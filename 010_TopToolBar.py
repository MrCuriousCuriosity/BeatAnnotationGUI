"""
Top toolbar UI component for the Beat Annotation GUI.

This module handles the top toolbar section with file operations and playback controls.
"""

import tkinter as tk
from tkinter import filedialog, messagebox



# === Script for Main ToolBar (TOP) ===

class TopToolBar:
    TOOLBAR_HEIGHT = 40  # Height of the toolbar frame

    def __init__(self, parent_frame, callbacks=None):
        """Initialize the top toolbar."""
        self.frame = tk.Frame(parent_frame, height=self.TOOLBAR_HEIGHT)
        self.frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 0))
        self.frame.pack_propagate(False)
        self.callbacks = callbacks or {}

        # Setup UI elements
        self._setup_open_button()
        self._setup_youtube_button()
        self._setup_settings_button()
        self._setup_playback_buttons()
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


    # === YOUTUBE BUTTON ===
    def _setup_youtube_button(self):
        """Setup the Insert Youtube Performance button."""
        self.youtube_btn = tk.Button(
            self.frame, text="Insert Youtube Performance", command=self._on_youtube_click
        )
        self.youtube_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _on_youtube_click(self):
        """Handle Youtube button click — show URL input dialog."""
        dialog = tk.Toplevel(self.frame)
        dialog.title("Insert YouTube Performance")
        dialog.resizable(False, False)
        dialog.grab_set()  # Make modal

        tk.Label(dialog, text="YouTube URL:").pack(padx=12, pady=(12, 4))
        url_var = tk.StringVar()
        entry = tk.Entry(dialog, textvariable=url_var, width=52)
        entry.pack(padx=12, pady=(0, 8))
        entry.focus_set()

        def _submit():
            url = url_var.get().strip()
            if not url:
                return
            dialog.destroy()
            if "on_youtube" in self.callbacks:
                self.callbacks["on_youtube"](url)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=(0, 12))
        tk.Button(btn_frame, text="Download", command=_submit).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=4)

        dialog.bind("<Return>", lambda e: _submit())

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

    # === PLAYBACK BUTTONS ===
    def _setup_playback_buttons(self):
        """Setup Play, Pause, and Stop buttons."""
        self.play_btn = tk.Button(
            self.frame, text="▶ Play", command=self._on_play_click
        )
        self.play_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.stop_btn = tk.Button(
            self.frame, text="⏹ Stop", command=self._on_stop_click
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(4, 0))

    def _on_play_click(self):
        if "on_play" in self.callbacks:
            self.callbacks["on_play"]()

    def _on_pause_click(self):
        if "on_pause" in self.callbacks:
            self.callbacks["on_pause"]()

    def _on_stop_click(self):
        if "on_stop" in self.callbacks:
            self.callbacks["on_stop"]()

    # === INFO LABEL ===
    def _setup_info_label(self):
        """Setup the info label."""
        self.info_var = tk.StringVar(value="Select an audio file to render spectrogram.")
        self.info_label = tk.Label(self.frame, textvariable=self.info_var, anchor="w")
        self.info_label.pack(side=tk.LEFT, padx=12)

    def set_info_text(self, text):
        """Update the info label text."""
        self.info_var.set(text)

    # === QUIT BUTTON ===
    def _setup_quit_button(self):
        """Setup the Quit button."""
        self.quit_btn = tk.Button(
            self.frame, text="Quit", command=self._on_quit_click
        )
        self.quit_btn.pack(side=tk.RIGHT, padx=(0, 8))

    def _on_quit_click(self):
        """Handle Quit button click."""
        self.frame.winfo_toplevel().destroy()
