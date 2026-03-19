"""
Spectrogram configuration and visualization utilities.

This module handles all spectrogram-related parameters, visualization settings,
and computation for the Beat Annotation GUI.
"""

import numpy as np
import modusa


class SpectrogramConfig:
    """Configuration class for spectrogram parameters and visualization."""

    # === Spectrogram computation parameters ===
    WINDOW_LENGTH_SEC = 0.064  # Window length in seconds
    HOP_LENGTH_RATIO = 4  # Hop length is 1/4 of window length
    WIN_LEN_SAMPLES = None  # Override window length in samples (set by settings UI)
    HOP_LEN_SAMPLES = None  # Override hop length in samples (set by settings UI)

    # === Visualization parameters ===
    COLOR_SCHEME = "magma"  # Colormap for spectrogram
    ORIGIN = "lower"  # Origin position ('lower' or 'upper')
    MIN_FREQ = 0            # Min frequency for display (Hz)
    MAX_FREQ = 8000         # Max frequency for display (Hz)
    DB_RANGE = 80           # Dynamic range in dB
    NORMALIZE = True        # Normalize display to signal peak
    
    # === Playback cursor parameters ===
    PLAYBACK_LINE_COLOR = "white"
    PLAYBACK_LINE_WIDTH = 1.0
    PLAYBACK_LINE_ALPHA = 1.0
    PLAYBACK_LINE_ZORDER = 10

    # === UI refresh parameters ===
    UI_UPDATE_INTERVAL_MS = 17  # Update interval for UI cursor in milliseconds (~60 FPS)

    @staticmethod
    def compute_spectrogram(audio_mono, sr):
        """
        Compute STFT spectrogram from mono audio.

        Parameters
        ----------
        audio_mono : np.ndarray
            Mono audio signal.
        sr : int
            Sample rate in Hz.

        Returns
        -------
        S : np.ndarray
            STFT magnitude spectrogram.
        freqs : np.ndarray
            Frequency bins.
        times : np.ndarray
            Time bins.
        """
        if SpectrogramConfig.WIN_LEN_SAMPLES is not None:
            winlen = SpectrogramConfig.WIN_LEN_SAMPLES
        else:
            winlen = int(SpectrogramConfig.WINDOW_LENGTH_SEC * sr)

        if SpectrogramConfig.HOP_LEN_SAMPLES is not None:
            hoplen = SpectrogramConfig.HOP_LEN_SAMPLES
        else:
            hoplen = max(1, winlen // SpectrogramConfig.HOP_LENGTH_RATIO)

        S, freqs, times = modusa.compute.stft(
            audio_mono, sr, winlen=winlen, hoplen=hoplen
        )
        return S, freqs, times

    @staticmethod
    def get_spectrogram_db(S):
        """
        Convert magnitude spectrogram to dB scale.

        Parameters
        ----------
        S : np.ndarray
            Magnitude spectrogram.

        Returns
        -------
        S_db : np.ndarray
            Spectrogram in dB scale.
        """
        return 20 * np.log10(np.abs(S) + 1e-8)

    @staticmethod
    def paint_spectrogram(ax, S_db, freqs, times, name):
        """
        Paint spectrogram on matplotlib axes.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Target axes object.
        S_db : np.ndarray
            Spectrogram in dB scale.
        freqs : np.ndarray
            Frequency bins.
        times : np.ndarray
            Time bins.
        name : str
            Audio file name (for title).

        Returns
        -------
        playback_line : matplotlib.lines.Line2D
            The playback cursor line object.
        """
        ax.clear()
        modusa.paint.image(
            ax=ax,
            M=S_db,
            y=freqs,
            x=times,
            c=SpectrogramConfig.COLOR_SCHEME,
            o=SpectrogramConfig.ORIGIN,
        )

        # Apply dynamic range and normalization
        if ax.images:
            vmax = float(S_db.max()) if SpectrogramConfig.NORMALIZE else 0.0
            vmin = vmax - SpectrogramConfig.DB_RANGE
            ax.images[-1].set_clim(vmin, vmax)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_title(f"Spectrogram: {name}")
        ax.set_ylim(SpectrogramConfig.MIN_FREQ, SpectrogramConfig.MAX_FREQ)

        # === Add playback cursor line ===
        playback_line = ax.axvline(
            x=0.0,
            color=SpectrogramConfig.PLAYBACK_LINE_COLOR,
            linewidth=SpectrogramConfig.PLAYBACK_LINE_WIDTH,
            alpha=SpectrogramConfig.PLAYBACK_LINE_ALPHA,
            zorder=SpectrogramConfig.PLAYBACK_LINE_ZORDER,
            animated=True,  # Exclude from static draw; updated via blit
        )

        return playback_line


class SpectrogramNavigator:
    """Handles scroll-to-zoom and click+drag pan on the spectrogram axes."""

    ZOOM_FACTOR = 0.7       # Window shrinks to 70% per scroll-down step
    MIN_WINDOW_SEC = 0.1    # Minimum displayable time window (seconds)
    SCROLL_DEBOUNCE_MS = 300  # Full redraw fires this long after the last scroll tick

    def __init__(self, ax, canvas, total_duration, on_view_change=None):
        self.ax = ax
        self.canvas = canvas
        self.total_duration = total_duration
        self.on_view_change = on_view_change  # called after every redraw

        self.view_start = 0.0
        self.view_end = total_duration
        self._drag_anchor = None
        self._redraw_after_id = None
        self._cids = []

        self._bind_events()

    # --- Public API ---------------------------------------------------

    def reset(self, total_duration):
        """Reset view to full duration. Call when a new file is loaded."""
        if self._redraw_after_id is not None:
            self.canvas.get_tk_widget().after_cancel(self._redraw_after_id)
            self._redraw_after_id = None
        if self.ax.images:
            self.ax.images[0].set_visible(True)
        self.total_duration = total_duration
        self.view_start = 0.0
        self.view_end = total_duration
        self.ax.set_xlim(self.view_start, self.view_end)

    def unbind_events(self):
        """Disconnect all matplotlib event handlers."""
        for cid in self._cids:
            self.canvas.mpl_disconnect(cid)
        self._cids.clear()

    # --- Setup --------------------------------------------------------

    def _bind_events(self):
        self._cids = [
            self.canvas.mpl_connect('scroll_event',          self._on_scroll),
            self.canvas.mpl_connect('button_press_event',    self._on_press),
            self.canvas.mpl_connect('motion_notify_event',   self._on_motion),
            self.canvas.mpl_connect('button_release_event',  self._on_release),
        ]

    # --- Scroll-to-zoom -----------------------------------------------

    def _on_scroll(self, event):
        if event.inaxes is not self.ax or event.xdata is None:
            return

        zoom_in = event.step < 0
        t_mouse = max(self.view_start, min(self.view_end, event.xdata))
        current_span = self.view_end - self.view_start

        if zoom_in:
            new_span = max(self.MIN_WINDOW_SEC, current_span * self.ZOOM_FACTOR)
        else:
            new_span = current_span / self.ZOOM_FACTOR
            if new_span >= self.total_duration:
                self.view_start = 0.0
                self.view_end = self.total_duration
                self._apply_view_scroll()
                return

        # Keep the time point under the cursor fixed
        ratio = (t_mouse - self.view_start) / current_span if current_span > 0 else 0.5
        new_start = t_mouse - ratio * new_span
        new_end = new_start + new_span

        # Clamp to audio bounds
        if new_start < 0.0:
            new_start = 0.0
            new_end = new_span
        if new_end > self.total_duration:
            new_end = self.total_duration
            new_start = max(0.0, new_end - new_span)

        self.view_start = new_start
        self.view_end = new_end
        self._apply_view_scroll()

    # --- Click + drag pan ---------------------------------------------

    def _on_press(self, event):
        if event.inaxes is not self.ax or event.button != 1 or event.xdata is None:
            return
        self._drag_anchor = event.xdata

    def _on_motion(self, event):
        if self._drag_anchor is None or event.xdata is None:
            return

        # Shift window so the anchor data-point stays under the cursor
        delta = self._drag_anchor - event.xdata
        span = self.view_end - self.view_start
        new_start = self.view_start + delta
        new_end = new_start + span

        if new_start < 0.0:
            new_start = 0.0
            new_end = span
        if new_end > self.total_duration:
            new_end = self.total_duration
            new_start = max(0.0, new_end - span)

        self.view_start = new_start
        self.view_end = new_end
        self._apply_view()

    def _on_release(self, event):
        if event.button == 1:
            self._drag_anchor = None

    # --- Redraw -------------------------------------------------------

    def _apply_view_scroll(self):
        """Scroll path: hide the image so canvas.draw() only redraws axes/ticks
        (fast), giving real-time time-axis updates. Debounce the full image render."""
        self.ax.set_xlim(self.view_start, self.view_end)
        # Hide image → draw() becomes cheap → ticks repaint immediately
        if self.ax.images:
            self.ax.images[0].set_visible(False)
        self.canvas.draw()
        self._schedule_full_redraw()

    def _schedule_full_redraw(self):
        """Cancel any pending redraw timer and start a new one."""
        widget = self.canvas.get_tk_widget()
        if self._redraw_after_id is not None:
            widget.after_cancel(self._redraw_after_id)
        self._redraw_after_id = widget.after(
            self.SCROLL_DEBOUNCE_MS, self._do_full_redraw
        )

    def _do_full_redraw(self):
        """Restore image and do the expensive full render after debounce."""
        self._redraw_after_id = None
        if self.ax.images:
            self.ax.images[0].set_visible(True)
        self.canvas.draw()
        if self.on_view_change:
            self.on_view_change()

    def _apply_view(self):
        """Full immediate redraw — used by pan drag."""
        # If a scroll session left the image hidden, restore it and cancel timer
        if self.ax.images and not self.ax.images[0].get_visible():
            self.ax.images[0].set_visible(True)
            if self._redraw_after_id is not None:
                self.canvas.get_tk_widget().after_cancel(self._redraw_after_id)
                self._redraw_after_id = None
        self.ax.set_xlim(self.view_start, self.view_end)
        self.canvas.draw()
        if self.on_view_change:
            self.on_view_change()
