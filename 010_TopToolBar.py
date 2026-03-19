"""
Top toolbar UI component for the Beat Annotation GUI.

This module handles the top toolbar section with file operations and playback controls.
"""

import tkinter as tk
from tkinter import filedialog, messagebox

import modusa as ms

# === Script for Main ToolBar (TOP) ===

class TopToolBar:
    def __init__(self, parent_frame, callbacks=None):
        """Initialize the top toolbar."""
        self.frame = tk.Frame(parent_frame)
        self.frame.pack(side=tk.TOP, fill=tk.X)
        self.callbacks = callbacks or {}

        # Setup UI elements
        self._setup_open_button()
        self._setup_settings_button()
        self._setup_quit_button()
        self._setup_info_label()

    # === OPEN BUTTON ===
    def _setup_open_button(self):
        """Setup the Open Audio File button."""
        self.open_btn = tk.Button(
            self.frame, text="Open Audio File", command=self._on_open_click
        )
        self.open_btn.pack(side=tk.LEFT)

    def _on_open_click(self):
        """Handle Open button click."""
        audio_path = filedialog.askopenfilename(
            title="Choose audio file",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.m4a *.aac *.opus *.aiff"),
                ("All files", "*.*"),
            ],
        )
        if not audio_path:
            return
        if "on_open" in self.callbacks:
            try:
                self.callbacks["on_open"](audio_path)
            except Exception as e:
                messagebox.showerror("Error", str(e))


    # === SPECTROGRAM SETTINGS BUTTON ===
    def _setup_settings_button(self):
        """Setup the Spectrogram Settings button."""
        self.settings_btn = tk.Button(
            self.frame, text="Spectrogram Settings", command=self._on_settings_click
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _on_settings_click(self):
        """Handle Settings button click."""
        if "on_settings" in self.callbacks:
            self.callbacks["on_settings"]()

    # === INFO LABEL ===
    def _setup_info_label(self):
        """Setup the info label."""
        self.info_var = tk.StringVar(value="Select an audio file to render spectrogram.")
        self.info_label = tk.Label(self.frame, textvariable=self.info_var, anchor="w")
        self.info_label.pack(side=tk.LEFT, padx=12)

    def set_info_text(self, text):
        """Update the info label text."""
        self.info_var.set(text)

    def get_info_text(self):
        """Get the current info label text."""
        return self.info_var.get()

    # === QUIT BUTTON ===
    def _setup_quit_button(self):
        """Setup the Quit button."""
        self.quit_btn = tk.Button(
            self.frame, text="Quit", command=self._on_quit_click
        )
        self.quit_btn.pack(side=tk.RIGHT, padx=(0, 8))

    def _on_quit_click(self):
        """Handle Quit button click."""
        if "on_quit" in self.callbacks:
            self.callbacks["on_quit"]()
        else:
            self.frame.winfo_toplevel().destroy()
