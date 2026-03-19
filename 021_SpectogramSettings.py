"""
Spectrogram Settings UI component for the Beat Annotation GUI.

This module handles the floating settings window for spectrogram visualization parameters.
"""

import tkinter as tk
from tkinter import ttk


class SpectrogramSettings:
    """Floating window for spectrogram visualization settings."""

    # Common matplotlib colormaps suitable for spectrograms
    COLORMAPS = [
        "magma",
        "viridis",
        "plasma",
        "inferno",
        "cividis",
        "twilight",
        "hot",
        "cool",
        "spring",
        "summer",
        "autumn",
        "winter",
        "Greys",
        "gray",
        "bone",
        "pink",
    ]

    # Default settings
    DEFAULTS = {
        "colormap": "magma",
        "min_freq": 20,
        "max_freq": 6000,
        "win_len": 2048,
        "hop_len": 512,
        "db_range": 60,
        "normalize": True,
    }

    def __init__(self, parent, settings=None, on_apply_callback=None):
        """
        Initialize the spectrogram settings window.

        Args:
            parent: Parent tkinter window
            settings: Dict of current settings (optional)
            on_apply_callback: Function to call when Apply is clicked
        """
        self.parent = parent
        self.on_apply_callback = on_apply_callback
        self.settings = self.DEFAULTS.copy()
        if settings:
            self.settings.update(settings)

        # Create floating window
        self.window = tk.Toplevel(parent)
        self.window.title("Spectrogram Settings")
        self.window.geometry("400x520")
        self.window.resizable(False, False)

        # Enter button pinned to the bottom of the window
        bottom_frame = ttk.Frame(self.window, padding=(15, 5, 15, 10))
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(bottom_frame, text="Enter", command=self._on_apply).pack(
            side=tk.RIGHT
        )

        # Create main frame with padding
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === COLORMAP SECTION ===
        ttk.Label(main_frame, text="Colormap", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 5)
        )
        self.colormap_var = tk.StringVar(value=self.settings["colormap"])
        colormap_menu = ttk.Combobox(
            main_frame,
            textvariable=self.colormap_var,
            values=self.COLORMAPS,
            state="readonly",
            width=20,
        )
        colormap_menu.pack(anchor="w", pady=(0, 15), fill=tk.X)

        # === FREQUENCY RANGE SECTION ===
        ttk.Label(main_frame, text="Frequency Range (Hz)", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 5)
        )

        freq_frame = ttk.Frame(main_frame)
        freq_frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        ttk.Label(freq_frame, text="Min:").pack(side=tk.LEFT)
        self.min_freq_var = tk.IntVar(value=self.settings["min_freq"])
        min_freq_spinbox = ttk.Spinbox(
            freq_frame,
            from_=0,
            to=20000,
            textvariable=self.min_freq_var,
            width=10,
        )
        min_freq_spinbox.pack(side=tk.LEFT, padx=(5, 20))

        ttk.Label(freq_frame, text="Max:").pack(side=tk.LEFT)
        self.max_freq_var = tk.IntVar(value=self.settings["max_freq"])
        max_freq_spinbox = ttk.Spinbox(
            freq_frame,
            from_=0,
            to=20000,
            textvariable=self.max_freq_var,
            width=10,
        )
        max_freq_spinbox.pack(side=tk.LEFT, padx=5)

        # === WINDOW LENGTH SECTION ===
        ttk.Label(main_frame, text="Window Length (samples)", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 5)
        )

        win_len_frame = ttk.Frame(main_frame)
        win_len_frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        self.win_len_var = tk.IntVar(value=self.settings["win_len"])
        win_len_scale = ttk.Scale(
            win_len_frame,
            from_=256,
            to=8192,
            orient=tk.HORIZONTAL,
            variable=self.win_len_var,
            command=self._on_win_len_change,
        )
        win_len_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.win_len_label = ttk.Label(win_len_frame, text=str(self.settings["win_len"]))
        self.win_len_label.pack(side=tk.LEFT, padx=(5, 0))

        # === HOP LENGTH SECTION ===
        ttk.Label(main_frame, text="Hop Length (samples)", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 5)
        )

        hop_len_frame = ttk.Frame(main_frame)
        hop_len_frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        self.hop_len_var = tk.IntVar(value=self.settings["hop_len"])
        hop_len_scale = ttk.Scale(
            hop_len_frame,
            from_=64,
            to=2048,
            orient=tk.HORIZONTAL,
            variable=self.hop_len_var,
            command=self._on_hop_len_change,
        )
        hop_len_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.hop_len_label = ttk.Label(hop_len_frame, text=str(self.settings["hop_len"]))
        self.hop_len_label.pack(side=tk.LEFT, padx=(5, 0))

        # === DYNAMIC RANGE SECTION ===
        ttk.Label(main_frame, text="Dynamic Range (dB)", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 5)
        )

        db_range_frame = ttk.Frame(main_frame)
        db_range_frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        self.db_range_var = tk.IntVar(value=self.settings["db_range"])
        db_range_scale = ttk.Scale(
            db_range_frame,
            from_=20,
            to=150,
            orient=tk.HORIZONTAL,
            variable=self.db_range_var,
            command=self._on_db_range_change,
        )
        db_range_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.db_range_label = ttk.Label(db_range_frame, text=str(self.settings["db_range"]))
        self.db_range_label.pack(side=tk.LEFT, padx=(5, 0))

        # === NORMALIZE SECTION ===
        ttk.Label(main_frame, text="Display Options", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(0, 5)
        )

        self.normalize_var = tk.BooleanVar(value=self.settings["normalize"])
        normalize_check = ttk.Checkbutton(
            main_frame, text="Normalize spectrogram", variable=self.normalize_var
        )
        normalize_check.pack(anchor="w", pady=(0, 20))



    def _on_win_len_change(self, value):
        """Update window length label."""
        self.win_len_label.config(text=str(int(float(value))))

    def _on_hop_len_change(self, value):
        """Update hop length label."""
        self.hop_len_label.config(text=str(int(float(value))))

    def _on_db_range_change(self, value):
        """Update dynamic range label."""
        self.db_range_label.config(text=str(int(float(value))))

    def _on_apply(self):
        """Apply settings and close window."""
        self.settings = {
            "colormap": self.colormap_var.get(),
            "min_freq": self.min_freq_var.get(),
            "max_freq": self.max_freq_var.get(),
            "win_len": int(self.win_len_var.get()),
            "hop_len": int(self.hop_len_var.get()),
            "db_range": int(self.db_range_var.get()),
            "normalize": self.normalize_var.get(),
        }

        if self.on_apply_callback:
            self.on_apply_callback(self.settings)

        self.window.destroy()

    def _on_reset(self):
        """Reset all settings to defaults."""
        self.colormap_var.set(self.DEFAULTS["colormap"])
        self.min_freq_var.set(self.DEFAULTS["min_freq"])
        self.max_freq_var.set(self.DEFAULTS["max_freq"])
        self.win_len_var.set(self.DEFAULTS["win_len"])
        self.hop_len_var.set(self.DEFAULTS["hop_len"])
        self.db_range_var.set(self.DEFAULTS["db_range"])
        self.normalize_var.set(self.DEFAULTS["normalize"])

        # Update labels
        self.win_len_label.config(text=str(self.DEFAULTS["win_len"]))
        self.hop_len_label.config(text=str(self.DEFAULTS["hop_len"]))
        self.db_range_label.config(text=str(self.DEFAULTS["db_range"]))

    def get_settings(self):
        """Return current settings dict."""
        return self.settings.copy()
