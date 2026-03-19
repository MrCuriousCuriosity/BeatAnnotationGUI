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

    # === DARK/LIGHT MODE ===
    DARK_MODE = True
    


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

        # Audio state
        self.audio_mono = None
        self.sr = None
        self.audio_name = None

        # Spectrogram line state
        self.playback_line = None
        self._background = None  # Cached spectrogram background for blitting

        # Settings window state
        self._settings_window = None

        # Create UI components
        self._setup_toolbar()
        self._setup_canvas()

        # Apply colour theme
        self._apply_theme()

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
            "on_open": self.open_file,
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
                self._apply_theme()
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

            # Reset window/hop overrides so spectrogram uses current settings
            SpectrogramConfig.WIN_LEN_SAMPLES = None
            SpectrogramConfig.HOP_LEN_SAMPLES = None

            # Compute spectrogram
            S, freqs, times = SpectrogramConfig.compute_spectrogram(
                self.audio_mono, self.sr
            )
            S_db = SpectrogramConfig.get_spectrogram_db(S)

            # Paint spectrogram
            self.playback_line = SpectrogramConfig.paint_spectrogram(
                self.ax, S_db, freqs, times, name
            )

            self._apply_theme()
            self.canvas.draw()
            self._background = self.canvas.copy_from_bbox(self.ax.bbox)

            self.toolbar.set_info_text(f"Loaded: {name} | sr={self.sr} Hz")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_close(self):
        """Handle window close event."""
        self.root.destroy()


def main():
    """Main entry point for the Beat Annotation GUI application."""
    root = tk.Tk()
    app = SpectrogramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
