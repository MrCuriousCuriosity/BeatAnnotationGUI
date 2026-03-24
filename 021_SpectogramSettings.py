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
        "magma", "viridis", "plasma", "inferno", "cividis", "twilight",
        "hot", "cool", "spring", "summer", "autumn", "winter", "Greys", "gray", "bone", "pink",
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
        "mel_view": False,
        "mel_rows": 768,
        "render_cols": 4096,
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

        # Storage for scale labels for dynamic updates
        self._scale_labels = {}

        # Create floating window
        self.window = tk.Toplevel(parent)
        self.window.title("Spectrogram Settings")
        self.window.geometry("400x600")
        self.window.resizable(False, False)

        # Create main frame with padding
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Build UI sections
        self._build_colormap_section(main_frame)
        self._build_frequency_section(main_frame)
        self._build_window_section(main_frame)
        self._build_hop_section(main_frame)
        self._build_db_range_section(main_frame)
        self._build_normalize_section(main_frame)
        self._build_mel_rows_section(main_frame)
        self._build_render_cols_section(main_frame)

        # Enter button pinned to the bottom of the window
        bottom_frame = ttk.Frame(self.window, padding=(15, 5, 15, 10))
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        # Use tk.Button here because ttk on macOS can render white text on white
        # background in its default state for some themes.
        tk.Button(
            bottom_frame,
            text="Enter",
            command=self._on_apply,
            fg="#000000",
            bg="#e6e6e6",
            activeforeground="#000000",
            activebackground="#cfd8ff",
            highlightthickness=0,
            padx=12,
            pady=4,
        ).pack(side=tk.RIGHT)

    # --- Section Builders ---

    def _build_colormap_section(self, parent):
        """Build the colormap selection section."""
        ttk.Label(parent, text="Colormap", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.colormap_var = tk.StringVar(value=self.settings["colormap"])
        colormap_menu = ttk.Combobox(
            parent, textvariable=self.colormap_var, values=self.COLORMAPS,
            state="readonly", width=20
        )
        colormap_menu.pack(anchor="w", pady=(0, 15), fill=tk.X)

    def _build_frequency_section(self, parent):
        """Build the frequency range (min/max) section."""
        ttk.Label(parent, text="Frequency Range (Hz)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        freq_frame = ttk.Frame(parent)
        freq_frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        ttk.Label(freq_frame, text="Min:").pack(side=tk.LEFT)
        self.min_freq_var = tk.IntVar(value=self.settings["min_freq"])
        ttk.Spinbox(freq_frame, from_=0, to=20000, textvariable=self.min_freq_var, width=10).pack(
            side=tk.LEFT, padx=(5, 20)
        )

        ttk.Label(freq_frame, text="Max:").pack(side=tk.LEFT)
        self.max_freq_var = tk.IntVar(value=self.settings["max_freq"])
        ttk.Spinbox(freq_frame, from_=0, to=20000, textvariable=self.max_freq_var, width=10).pack(
            side=tk.LEFT, padx=5
        )

    def _build_window_section(self, parent):
        """Build the window length (scale) section."""
        ttk.Label(parent, text="Window Length (samples)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.win_len_var = tk.IntVar(value=self.settings["win_len"])
        self._scale_labels["win_len"] = self._create_scale_input(
            parent, self.win_len_var, 256, 8192
        )

    def _build_hop_section(self, parent):
        """Build the hop length (scale) section."""
        ttk.Label(parent, text="Hop Length (samples)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.hop_len_var = tk.IntVar(value=self.settings["hop_len"])
        self._scale_labels["hop_len"] = self._create_scale_input(
            parent, self.hop_len_var, 64, 2048
        )

    def _build_db_range_section(self, parent):
        """Build the dynamic range (scale) section."""
        ttk.Label(parent, text="Dynamic Range (dB)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.db_range_var = tk.IntVar(value=self.settings["db_range"])
        self._scale_labels["db_range"] = self._create_scale_input(
            parent, self.db_range_var, 20, 150
        )

    def _build_normalize_section(self, parent):
        """Build the normalize and melodic-view checkbox section."""
        ttk.Label(parent, text="Display Options", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        options_frame = ttk.Frame(parent)
        options_frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        self.normalize_var = tk.BooleanVar(value=self.settings["normalize"])
        ttk.Checkbutton(
            options_frame, text="Normalize spectrogram", variable=self.normalize_var
        ).pack(side=tk.LEFT, anchor="w")

        self.log_freq_var = tk.BooleanVar(value=self.settings.get("mel_view", False))
        ttk.Checkbutton(
            options_frame, text="Melodic View", variable=self.log_freq_var
        ).pack(side=tk.LEFT, anchor="w", padx=(20, 0))

    def _build_render_cols_section(self, parent):
        """Build the render resolution (scale) section."""
        ttk.Label(parent, text="Render Resolution (columns)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.render_cols_var = tk.IntVar(value=self.settings.get("render_cols", 4096))
        self._scale_labels["render_cols"] = self._create_scale_input(
            parent, self.render_cols_var, 512, 8192
        )

    def _build_mel_rows_section(self, parent):
        """Build the Mel view render density section."""
        ttk.Label(parent, text="Mel Render Rows", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.mel_rows_var = tk.IntVar(value=self.settings.get("mel_rows", 768))
        self._scale_labels["mel_rows"] = self._create_scale_input(
            parent, self.mel_rows_var, 128, 2048
        )

    # --- Helper Methods ---

    def _create_scale_input(self, parent, var, from_, to):
        """
        Create a scale with a label showing the current value.

        Parameters
        ----------
        parent : tk.Widget
            Parent widget
        var : tk.IntVar
            Variable bound to the scale
        from_ : float
            Minimum scale value
        to : float
            Maximum scale value

        Returns
        -------
        ttk.Label
            Label widget displaying the current value (stored for updates)
        """
        frame = ttk.Frame(parent)
        frame.pack(anchor="w", pady=(0, 15), fill=tk.X)

        ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, variable=var,
                  command=lambda v: self._update_scale_label(label, v)).pack(
                      side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10)
                  )

        label = ttk.Label(frame, text=str(var.get()))
        label.pack(side=tk.LEFT, padx=(5, 0))
        return label

    def _update_scale_label(self, label, value):
        """Generic callback to update any scale label."""
        label.config(text=str(int(float(value))))

    def _on_apply(self):
        """Apply settings and close window."""
        self.settings = {
            "colormap":    self.colormap_var.get(),
            "min_freq":    self.min_freq_var.get(),
            "max_freq":    self.max_freq_var.get(),
            "win_len":     int(self.win_len_var.get()),
            "hop_len":     int(self.hop_len_var.get()),
            "db_range":    int(self.db_range_var.get()),
            "normalize":   self.normalize_var.get(),
            "mel_view":    self.log_freq_var.get(),
            "mel_rows":    int(self.mel_rows_var.get()),
            "render_cols": int(self.render_cols_var.get()),
        }

        if self.on_apply_callback:
            self.on_apply_callback(self.settings)

        self.window.destroy()


