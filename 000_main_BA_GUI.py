"""
Beat Annotation GUI - Main Entry Point

This is the main script to run the Beat Annotation GUI application.
It orchestrates all modules and manages the overall application lifecycle.
"""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import importlib.util

import threading
import tempfile

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import modusa
from modusa.utils.youtube_downloader import download as yt_download


# === Module Loading Helper ===
def _load_module_class(module_name, file_name, class_name):
    """
    Dynamically load a class from a module file.
    
    Parameters
    ----------
    module_name : str
        Internal module name (e.g., 'spectogram_config')
    file_name : str
        File name relative to script directory (e.g., '020_Spectogram.py')
    class_name : str
        Class name to extract from the module (e.g., 'SpectrogramConfig')
    
    Returns
    -------
    class
        The requested class from the loaded module
    """
    current_dir = Path(__file__).parent
    spec = importlib.util.spec_from_file_location(module_name, current_dir / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


# === Import custom modules with numeric prefixes ===
SpectrogramConfig = _load_module_class("spectogram_config", "020_Spectogram.py", "SpectrogramConfig")
SpectrogramNavigator = _load_module_class("spectogram_navigator", "020_Spectogram.py", "SpectrogramNavigator")
TopToolBar = _load_module_class("toolbar", "010_TopToolBar.py", "TopToolBar")
SpectrogramSettings = _load_module_class("spectogram_settings", "021_SpectogramSettings.py", "SpectrogramSettings")
AudioPlayer = _load_module_class("sound_playback", "100_SoundPlayback.py", "AudioPlayer")
PlaybackCursor = _load_module_class("playback_cursor", "101_PlayBackCursor.py", "PlaybackCursor")


class SpectrogramApp:
    """Main application class for the Beat Annotation GUI."""

    # === DARK/LIGHT MODE ===
    DARK_MODE = True

    SET_FULLSCREEN = True  # Set Fullscreen by default. I just added this for testing, and persnal preference.

    # === Main Window Layout ===
    MAIN_WINDOW_WIDTH_PCT  = 0.6  # Starting screen width
    MAIN_WINDOW_HEIGHT_PCT = 0.4  # Starting screen height

    # === Spectrogram Plot Layout ===
    FIGURE_WIDTH_PCT  = 1.2
    FIGURE_HEIGHT_PCT = 0.70
    FIGURE_CENTER_X   = 0.5
    FIGURE_CENTER_Y   = 0.35
    FIGURE_DPI = 100

    def __init__(self, root):
        """
        Initialize the Beat Annotation GUI application.

        Parameters
        ----------
        root : tk.Tk
            Root tkinter window.
        """
        self.root = root
        self.root.title("Audio Spectrogram Viewer")

        # Compute window size from screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.window_width  = int(screen_w * self.MAIN_WINDOW_WIDTH_PCT)
        self.window_height = int(screen_h * self.MAIN_WINDOW_HEIGHT_PCT)
        self.root.geometry(f"{self.window_width}x{self.window_height}")

        # === SET_FULLSCREEN on startup funtion ===
        if self.SET_FULLSCREEN:
            self.root.attributes("-fullscreen", True)

        # Audio state
        self.audio_mono = None
        self.sr = None
        self.audio_name = None

        # Spectrogram background cache for blitting
        self._background = None

        # Settings window state
        self._settings_window = None

        # Navigator state
        self.navigator = None

        # Playback engine and cursor
        self.player = AudioPlayer()
        self.playback_cursor = None

        # UI update loop handle
        self._loop_id = None

        # Create UI components (canvas first, toolbar on top)
        self._setup_canvas()
        self._setup_toolbar()

        # Apply colour theme
        self._apply_theme()

        # Start the ~60 FPS cursor update loop
        self._start_update_loop()

        # Clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # === DARK/LIGHT THEMES ===
    _DARK_THEME = {
        "bg": "#000000",
        "fg": "#ffffff",
    }
    _LIGHT_THEME = {
        "bg": "#f0f0f0",
        "fg": "#000000",
    }

    def _apply_theme(self):
        """Apply the light or dark colour theme to all tkinter and figure elements."""
        theme = self._DARK_THEME if self.DARK_MODE else self._LIGHT_THEME
        bg = theme["bg"]
        fg = theme["fg"]

        # Root window
        self.root.configure(bg=bg)

        # Matplotlib figure outer background
        self.fig.patch.set_facecolor(bg)
        self.ax.set_facecolor(bg)

        # Axes spines, ticks, and labels
        for spine in self.ax.spines.values():
            spine.set_edgecolor(fg)
        self.ax.tick_params(colors=fg)
        self.ax.xaxis.label.set_color(fg)
        self.ax.yaxis.label.set_color(fg)
        self.ax.title.set_color(fg)
    # === ===

    def _setup_toolbar(self):
        """Set up the top toolbar with callbacks."""
        callbacks = {
            "on_open":     self.open_file,
            "on_settings": self.open_settings,
            "on_youtube":  self._on_youtube,
            "on_play":     self._on_play,
            "on_pause":    self._on_pause,
            "on_stop":     self._on_stop,
        }
        self.toolbar = TopToolBar(self.root, callbacks=callbacks)

    def _setup_canvas(self):
        """Set up the matplotlib canvas for spectrogram visualization."""
        init_w = int(self.window_width  * self.FIGURE_WIDTH_PCT)
        init_h = int(self.window_height * self.FIGURE_HEIGHT_PCT)
        self.fig, self.ax = plt.subplots(
            figsize=(init_w / self.FIGURE_DPI, init_h / self.FIGURE_DPI),
            dpi=self.FIGURE_DPI,
        )
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        widget = self.canvas.get_tk_widget()
        cx = int(self.window_width  * self.FIGURE_CENTER_X)
        cy = int(self.window_height * self.FIGURE_CENTER_Y)
        widget.place(anchor='center', x=cx, y=cy, width=init_w, height=init_h)

        # Reposition/resize figure whenever the window changes (including fullscreen)
        self.root.bind("<Configure>", self._on_window_resize)

    def _on_window_resize(self, event):
        """Resize and reposition the matplotlib figure to track the window dimensions."""
        if event.widget is not self.root:
            return
        canvas_w = int(event.width  * self.FIGURE_WIDTH_PCT)
        canvas_h = int(event.height * self.FIGURE_HEIGHT_PCT)
        if canvas_w < 1 or canvas_h < 1:
            return
        cx = int(event.width  * self.FIGURE_CENTER_X)
        cy = int(event.height * self.FIGURE_CENTER_Y)
        widget = self.canvas.get_tk_widget()
        widget.place(anchor='center', x=cx, y=cy, width=canvas_w, height=canvas_h)
        self.fig.set_size_inches(canvas_w / self.FIGURE_DPI, canvas_h / self.FIGURE_DPI)
        self.canvas.draw_idle()

    def open_settings(self):
        """Open (or close) the spectrogram settings floating window."""
        # Toggle: close if already open
        if self._settings_window is not None:
            try:
                if self._settings_window.window.winfo_exists():
                    self._settings_window.window.destroy()
                    self._settings_window = None
                    return
            except Exception:
                self._settings_window = None

        # Build current settings from SpectrogramConfig
        if self.sr is not None and SpectrogramConfig.WIN_LEN_SAMPLES is None:
            win_len = int(SpectrogramConfig.WINDOW_LENGTH_SEC * self.sr)
            hop_len = max(1, win_len // SpectrogramConfig.HOP_LENGTH_RATIO)
        else:
            win_len = SpectrogramConfig.WIN_LEN_SAMPLES or SpectrogramSettings.DEFAULTS["win_len"]
            hop_len = SpectrogramConfig.HOP_LEN_SAMPLES or SpectrogramSettings.DEFAULTS["hop_len"]

        current_settings = {
            "colormap": SpectrogramConfig.COLOR_SCHEME,
            "min_freq": SpectrogramConfig.MIN_FREQ,
            "max_freq": SpectrogramConfig.MAX_FREQ,
            "win_len": win_len,
            "hop_len": hop_len,
            "db_range": SpectrogramConfig.DB_RANGE,
            "normalize": SpectrogramConfig.NORMALIZE,
            "render_cols": SpectrogramConfig.RENDER_COLS,
        }

        self._settings_window = SpectrogramSettings(
            self.root,
            settings=current_settings,
            on_apply_callback=self._on_settings_apply,
        )

    def _on_settings_apply(self, settings):
        """Apply new spectrogram settings and redraw if audio is loaded."""
        # Validate and clamp frequency bounds.
        min_freq = max(0, int(settings["min_freq"]))
        max_freq = int(settings["max_freq"])
        if max_freq <= min_freq:
            max_freq = min_freq + 1
        if self.sr is not None:
            nyquist = max(1, self.sr // 2)
            max_freq = min(max_freq, nyquist)

        SpectrogramConfig.COLOR_SCHEME = settings["colormap"]
        SpectrogramConfig.MIN_FREQ = min_freq
        SpectrogramConfig.MAX_FREQ = max_freq
        SpectrogramConfig.WIN_LEN_SAMPLES = settings["win_len"]
        SpectrogramConfig.HOP_LEN_SAMPLES = settings["hop_len"]
        SpectrogramConfig.DB_RANGE = settings["db_range"]
        SpectrogramConfig.NORMALIZE = settings["normalize"]
        SpectrogramConfig.RENDER_COLS = settings["render_cols"]
        self._settings_window = None

        # Recompute and repaint if audio is loaded
        if self.audio_mono is not None and self.sr is not None:
            try:
                S, freqs, times = SpectrogramConfig.compute_spectrogram(
                    self.audio_mono, self.sr
                )
                S_db = SpectrogramConfig.get_spectrogram_db(S)
                SpectrogramConfig.paint_spectrogram(
                    self.ax, S_db, freqs, times, self.audio_name
                )
                self._apply_theme()
                self.canvas.draw()
                self._background = self.canvas.copy_from_bbox(self.ax.bbox)

                # Recreate cursor on the redrawn axes
                self.playback_cursor = PlaybackCursor(self.ax)

                if self.navigator is not None:
                    self.navigator.reset(self.navigator.total_duration)
            except Exception as e:
                messagebox.showerror("Settings Error", str(e))

    def _on_view_change(self):
        """Recache blit background after navigator redraws."""
        self._background = self.canvas.copy_from_bbox(self.ax.bbox)
        # Redraw cursor immediately so it remains visible after the recache
        if self.playback_cursor is not None:
            self.playback_cursor.draw(self.canvas, self._background)

    def _on_nav_start(self):
        """Pause cursor blitting while the user is actively panning/zooming."""
        self._background = None

    # === YOUTUBE DOWNLOAD ===
    def _on_youtube(self, url):
        """Download audio from a YouTube URL in a background thread, then load it."""
        self.toolbar.set_info_text("Downloading from YouTube...")
        self.toolbar.youtube_btn.config(state=tk.DISABLED)

        def _worker():
            try:
                out_dir = tempfile.gettempdir()
                audio_path = yt_download(url, content_type="audio", output_dir=out_dir)
                self.root.after(0, lambda: self._on_youtube_done(str(audio_path)))
            except Exception as e:
                self.root.after(0, lambda err=e: self._on_youtube_error(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_youtube_done(self, audio_path):
        self.toolbar.youtube_btn.config(state=tk.NORMAL)
        self.open_file(audio_path)

    def _on_youtube_error(self, error):
        self.toolbar.youtube_btn.config(state=tk.NORMAL)
        self.toolbar.set_info_text("Select an audio file to render spectrogram.")
        messagebox.showerror("YouTube Download Error", str(error))

    def open_file(self, audio_path):
        """
        Load an audio file and display its spectrogram.

        Parameters
        ----------
        audio_path : str
            Path to the audio file.
        """
        try:
            y, sr, name = modusa.load.audio(audio_path)

            # Keep original for playback shape handling
            y_raw = np.asarray(y, dtype=np.float32)

            # Prepare mono for spectrogram
            if y_raw.ndim == 2:
                y_mono = np.mean(y_raw, axis=0)
            else:
                y_mono = y_raw

            self.audio_mono = np.asarray(y_mono, dtype=np.float32)
            self.sr = int(sr)
            self.audio_name = name

            # Reset window/hop overrides so spectrogram uses current settings
            SpectrogramConfig.WIN_LEN_SAMPLES = None
            SpectrogramConfig.HOP_LEN_SAMPLES = None

            # Compute spectrogram
            S, freqs, times = SpectrogramConfig.compute_spectrogram(
                self.audio_mono, self.sr
            )
            S_db = SpectrogramConfig.get_spectrogram_db(S)

            # Paint spectrogram
            SpectrogramConfig.paint_spectrogram(
                self.ax, S_db, freqs, times, name
            )

            self._apply_theme()
            self.canvas.draw()
            self._background = self.canvas.copy_from_bbox(self.ax.bbox)

            # (Re)create the playback cursor on the freshly drawn axes
            self.playback_cursor = PlaybackCursor(self.ax)

            # Load audio into the player (resets position to 0)
            self.player.load(self.audio_mono, self.sr)

            self.toolbar.set_info_text(f"Loaded: {name} | sr={self.sr} Hz")

            # Set up or reset the navigator
            total_duration = len(self.audio_mono) / self.sr
            if self.navigator is None:
                self.navigator = SpectrogramNavigator(
                    self.ax, self.canvas, total_duration,
                    on_view_change=self._on_view_change,
                    on_nav_start=self._on_nav_start,
                )
            else:
                self.navigator.reset(total_duration)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # === Playback controls ============================================

    def _on_play(self):
        """Play or resume audio."""
        if self.player.is_playing:
            self.player.pause()
        else:
            self.player.resume() if self.player.playback_position_sec > 0.0 else self.player.play()

    def _on_pause(self):
        """Pause audio without resetting position."""
        self.player.pause()

    def _on_stop(self):
        """Stop audio and reset cursor to 0."""
        self.player.stop()
        # Draw cursor at 0 immediately
        if self.playback_cursor is not None:
            self.playback_cursor.update(0.0)
            self.playback_cursor.draw(self.canvas, self._background)

    # === ~60 FPS cursor update loop ===================================

    def _start_update_loop(self):
        """Start the recurring UI update loop."""
        self._loop_tick()

    def _loop_tick(self):
        """Single tick: advance player position and redraw cursor."""
        self.player.update_position()
        if self.playback_cursor is not None and self._background is not None:
            self.playback_cursor.update(self.player.playback_position_sec)
            self.playback_cursor.draw(self.canvas, self._background)
        self._loop_id = self.root.after(
            SpectrogramConfig.UI_UPDATE_INTERVAL_MS, self._loop_tick
        )

    # ==================================================================

    def on_close(self):
        """Handle window close event."""
        self.player.stop()
        if self._loop_id is not None:
            self.root.after_cancel(self._loop_id)
        self.root.destroy()


def main():
    """Main entry point for the Beat Annotation GUI application."""
    root = tk.Tk()
    app = SpectrogramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
