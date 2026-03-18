"""
Beat Annotation GUI - Main Entry Point

This is the main script to run the Beat Annotation GUI application.
It orchestrates all modules and manages the overall application lifecycle.
"""

import tkinter as tk
from tkinter import messagebox
import sys
from pathlib import Path
import importlib.util

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sounddevice as sd

import modusa as ms

# Import custom modules with numeric prefixes
current_dir = Path(__file__).parent
spec_config = importlib.util.spec_from_file_location(
    "spectogram_config", current_dir / "020_Spectogram.py"
)
spectogram_module = importlib.util.module_from_spec(spec_config)
spec_config.loader.exec_module(spectogram_module)
SpectrogramConfig = spectogram_module.SpectrogramConfig

spec_toolbar = importlib.util.spec_from_file_location(
    "toolbar", current_dir / "010_TopToolBar.py"
)
toolbar_module = importlib.util.module_from_spec(spec_toolbar)
spec_toolbar.loader.exec_module(toolbar_module)
TopToolBar = toolbar_module.TopToolBar

spec_settings = importlib.util.spec_from_file_location(
    "spectogram_settings", current_dir / "021_SpectogramSettings.py"
)
settings_module = importlib.util.module_from_spec(spec_settings)
spec_settings.loader.exec_module(settings_module)
SpectrogramSettings = settings_module.SpectrogramSettings


class SpectrogramApp:
    """Main application class for the Beat Annotation GUI."""

    # UI Layout positioning variables
    MAIN_WINDOW_WIDTH = 950
    MAIN_WINDOW_HEIGHT = 600
    FIGURE_WIDTH_INCHES = 10
    FIGURE_HEIGHT_INCHES = 5
    FIGURE_DPI = 100
    TOP_BAR_PADX = 10
    TOP_BAR_PADY = 10

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
        self.root.geometry(f"{self.MAIN_WINDOW_WIDTH}x{self.MAIN_WINDOW_HEIGHT}")

        # Audio/playback state
        self.audio_mono = None
        self.audio_for_playback = None
        self.sr = None
        self.audio_name = None
        self.total_frames = 0

        self.playhead_frame = 0
        self.playing = False
        self.stream = None

        # Cursor line state
        self.playback_line = None
        self._background = None  # Cached spectrogram background for blitting

        # Settings window state
        self._settings_window = None

        # Create UI components
        self._setup_toolbar()
        self._setup_canvas()

        # Start UI update timer
        self.root.after(SpectrogramConfig.UI_UPDATE_INTERVAL_MS, self._update_ui)

        # Clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_toolbar(self):
        """Set up the top toolbar with callbacks."""
        callbacks = {
            "on_open": self.open_file,
            "on_play": self.play_audio,
            "on_pause": self.pause_audio,
            "on_settings": self.open_settings,
        }
        self.toolbar = TopToolBar(self.root, callbacks=callbacks)

    def _setup_canvas(self):
        """Set up the matplotlib canvas for spectrogram visualization."""
        self.fig, self.ax = plt.subplots(
            figsize=(self.FIGURE_WIDTH_INCHES, self.FIGURE_HEIGHT_INCHES),
            dpi=self.FIGURE_DPI,
        )
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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
        }

        self._settings_window = SpectrogramSettings(
            self.root,
            settings=current_settings,
            on_apply_callback=self._on_settings_apply,
        )

    def _on_settings_apply(self, settings):
        """Apply new spectrogram settings and redraw if audio is loaded."""
        SpectrogramConfig.COLOR_SCHEME = settings["colormap"]
        SpectrogramConfig.MIN_FREQ = settings["min_freq"]
        SpectrogramConfig.MAX_FREQ = settings["max_freq"]
        SpectrogramConfig.WIN_LEN_SAMPLES = settings["win_len"]
        SpectrogramConfig.HOP_LEN_SAMPLES = settings["hop_len"]
        SpectrogramConfig.DB_RANGE = settings["db_range"]
        SpectrogramConfig.NORMALIZE = settings["normalize"]
        self._settings_window = None

        # Recompute and repaint if audio is loaded
        if self.audio_mono is not None and self.sr is not None:
            try:
                S, freqs, times = SpectrogramConfig.compute_spectrogram(
                    self.audio_mono, self.sr
                )
                S_db = SpectrogramConfig.get_spectrogram_db(S)
                self.playback_line = SpectrogramConfig.paint_spectrogram(
                    self.ax, S_db, freqs, times, self.audio_name
                )
                self.canvas.draw()
                self._background = self.canvas.copy_from_bbox(self.ax.bbox)
            except Exception as e:
                messagebox.showerror("Settings Error", str(e))

    def open_file(self, audio_path):
        """
        Load an audio file and display its spectrogram.

        Parameters
        ----------
        audio_path : str
            Path to the audio file.
        """
        try:
            y, sr, name = ms.load.audio(audio_path)

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
            self.total_frames = self.audio_mono.shape[0]
            self.playhead_frame = 0

            # Prepare playback buffer as (frames, channels)
            if y_raw.ndim == 2:
                self.audio_for_playback = y_raw.T.astype(np.float32)  # (N, 2)
            else:
                self.audio_for_playback = y_raw.reshape(-1, 1).astype(
                    np.float32
                )  # (N, 1)

            # Stop previous stream if any
            self._stop_stream()

            # Compute spectrogram
            S, freqs, times = SpectrogramConfig.compute_spectrogram(
                self.audio_mono, self.sr
            )
            S_db = SpectrogramConfig.get_spectrogram_db(S)

            # Paint spectrogram
            self.playback_line = SpectrogramConfig.paint_spectrogram(
                self.ax, S_db, freqs, times, name
            )

            self.canvas.draw()
            self._background = self.canvas.copy_from_bbox(self.ax.bbox)

            self.toolbar.set_info_text(f"Loaded: {name} | sr={self.sr} Hz")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def play_audio(self):
        """Start audio playback."""
        if self.audio_for_playback is None or self.sr is None:
            messagebox.showinfo("No audio", "Load an audio file first.")
            return

        if self.playing:
            return

        # If finished, restart from beginning
        if self.playhead_frame >= self.total_frames:
            self.playhead_frame = 0

        if self.stream is None:
            channels = int(self.audio_for_playback.shape[1])

            def callback(outdata, frames, time_info, status):
                if status:
                    pass

                start = self.playhead_frame
                end = min(start + frames, self.total_frames)
                chunk = self.audio_for_playback[start:end]

                n = end - start
                outdata[:] = 0.0
                if n > 0:
                    outdata[:n, :channels] = chunk
                    self.playhead_frame = end

                # Reached end of file
                if end >= self.total_frames:
                    raise sd.CallbackStop()

            self.stream = sd.OutputStream(
                samplerate=self.sr,
                channels=channels,
                dtype="float32",
                callback=callback,
                finished_callback=self._on_stream_finished,
            )

        self.stream.start()
        self.playing = True
        self.toolbar.set_info_text(f"Playing: {self.audio_name}")

    def pause_audio(self):
        """Pause audio playback."""
        if self.stream is not None and self.playing:
            self.stream.stop()
            self.playing = False
            self.toolbar.set_info_text(
                f"Paused: {self.audio_name} @ {self.playhead_frame / self.sr:.2f}s"
            )

    def _on_stream_finished(self):
        """Handle stream finished callback."""
        self.playing = False
        self.stream = None
        self.toolbar.set_info_text(f"Finished: {self.audio_name}")

    def _stop_stream(self):
        """Stop and clean up audio stream."""
        self.playing = False
        if self.stream is not None:
            try:
                self.stream.stop()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _update_ui(self):
        """Update UI elements (playback cursor position)."""
        if self.playback_line is not None and self.sr and self.total_frames > 0 and self._background is not None:
            t = self.playhead_frame / self.sr
            self.playback_line.set_xdata([t, t])
            # Blit: restore cached background, draw only the cursor, then blit
            self.canvas.restore_region(self._background)
            self.ax.draw_artist(self.playback_line)
            self.canvas.blit(self.ax.bbox)

        self.root.after(SpectrogramConfig.UI_UPDATE_INTERVAL_MS, self._update_ui)

    def on_close(self):
        """Handle window close event."""
        self._stop_stream()
        self.root.destroy()


def main():
    """Main entry point for the Beat Annotation GUI application."""
    root = tk.Tk()
    app = SpectrogramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
