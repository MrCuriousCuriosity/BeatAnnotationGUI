"""
Spectrogram configuration and visualization utilities.

This module handles all spectrogram-related parameters, visualization settings,
and computation for the Beat Annotation GUI.
"""

import numpy as np
from matplotlib.ticker import MaxNLocator
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
    MIN_FREQ = 20            # Min frequency for display (Hz)
    MAX_FREQ = 7000         # Max frequency for display (Hz)
    DB_RANGE = 60           # Dynamic range in dB
    NORMALIZE = True        # Normalize display to signal peak

    # === Render resolution ===
    RENDER_COLS = 4096      # Time columns in the pre-downsampled display image

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
    def downsample_spectrogram(S_db, target_cols):
        """
        Reduce S_db to target_cols time columns via block-max pooling.

        Parameters
        ----------
        S_db : np.ndarray
            Full-resolution spectrogram in dB, shape (n_freq, n_time).
        target_cols : int
            Desired number of output time columns.

        Returns
        -------
        np.ndarray
            Downsampled spectrogram, shape (n_freq, target_cols).
        """
        n_freq, n_time = S_db.shape
        if n_time <= target_cols:
            return S_db
        indices = np.linspace(0, n_time, target_cols + 1, dtype=int)
        return np.maximum.reduceat(S_db, indices[:-1], axis=1)

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

        """
        ax.clear()
        S_db_render = SpectrogramConfig.downsample_spectrogram(
            S_db, SpectrogramConfig.RENDER_COLS
        )
        times_render = (
            np.linspace(times[0], times[-1], S_db_render.shape[1])
            if S_db_render.shape[1] != len(times)
            else times
        )
        modusa.paint.image(
            ax=ax,
            M=S_db_render,
            y=freqs,
            x=times_render,
            c=SpectrogramConfig.COLOR_SCHEME,
            o=SpectrogramConfig.ORIGIN,
        )

        # Apply dynamic range and normalization (use original S_db for global max)
        if ax.images:
            vmax = float(S_db.max()) if SpectrogramConfig.NORMALIZE else 0.0
            vmin = vmax - SpectrogramConfig.DB_RANGE
            ax.images[-1].set_clim(vmin, vmax)

        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_title(f"Spectrogram: {name}")
        ax.set_ylim(SpectrogramConfig.MIN_FREQ, SpectrogramConfig.MAX_FREQ)


class SpectrogramNavigator:
    """Handles scroll-to-zoom and click+drag pan on the spectrogram axes.

    Interaction model:
    - While dragging/scrolling: only the x-axis is blitted (fast preview).
    - After interaction settles: one full canvas redraw is performed.
    """

    ZOOM_FACTOR = 0.7       # Window shrinks to 70% per scroll-down step
    MIN_WINDOW_SEC = 0.1    # Minimum displayable time window (seconds)
    PREVIEW_INTERVAL_MS = 16  # 60 Hz axis preview while interacting
    SCROLL_SETTLE_MS = 200  # Redraw spectrogram 0.2 s after last wheel event

    def __init__(self, ax, canvas, total_duration, on_view_change=None, on_nav_start=None):
        self.ax = ax
        self.canvas = canvas
        self.total_duration = total_duration
        self.on_view_change = on_view_change  # called after every full redraw
        self.on_nav_start = on_nav_start      # called when interaction begins

        self.view_start = 0.0
        self.view_end = total_duration
        self._drag_anchor = None
        self._drag_anchor_px = None
        self._drag_view_start = None
        self._drag_span = None
        self._tick_locator = MaxNLocator(nbins=7)
        self._scroll_after_id = None
        self._preview_after_id = None
        self._preview_dirty = False
        self._axis_preview_background = None
        self._axis_preview_bbox = None
        self._nav_active = False
        self._cids = []

        self._bind_events()
        self._update_time_ticks()
        self._cache_axis_preview_background_from_current()

    # --- Public API ---------------------------------------------------

    def reset(self, total_duration):
        """Reset view to full duration. Call when a new file is loaded."""
        self.total_duration = total_duration
        self.view_start = 0.0
        self.view_end = total_duration
        self._drag_anchor = None
        self._drag_anchor_px = None
        self._drag_view_start = None
        self._drag_span = None
        self._nav_active = False
        self._stop_preview_loop()
        self._cancel_scroll_settle()
        self.ax.set_xlim(self.view_start, self.view_end)
        self._update_time_ticks()
        self._cache_axis_preview_background_from_current()

    def unbind_events(self):
        """Disconnect all matplotlib event handlers."""
        for cid in self._cids:
            self.canvas.mpl_disconnect(cid)
        self._cids.clear()
        self._drag_anchor = None
        self._drag_anchor_px = None
        self._drag_view_start = None
        self._drag_span = None
        self._nav_active = False
        self._stop_preview_loop()
        self._cancel_scroll_settle()

    # --- Setup --------------------------------------------------------

    def _bind_events(self):
        self._cids = [
            self.canvas.mpl_connect('scroll_event',          self._on_scroll),
            self.canvas.mpl_connect('button_press_event',    self._on_press),
            self.canvas.mpl_connect('motion_notify_event',   self._on_motion),
            self.canvas.mpl_connect('button_release_event',  self._on_release),
        ]

    # --- Internal helpers ---------------------------------------------

    def _cancel_scroll_settle(self):
        if self._scroll_after_id is not None:
            self.canvas.get_tk_widget().after_cancel(self._scroll_after_id)
            self._scroll_after_id = None

    def _begin_navigation(self):
        """Enter interaction mode and pause external cursor blitting."""
        if self._nav_active:
            return
        self._nav_active = True
        self._start_preview_loop()
        if self.on_nav_start:
            self.on_nav_start()
        if self._axis_preview_background is None:
            self._cache_axis_preview_background_from_current()

    def _finish_navigation(self):
        """Render one final frame and refresh preview cache for next interaction."""
        self._nav_active = False
        self._stop_preview_loop()
        self.ax.set_xlim(self.view_start, self.view_end)
        self._update_time_ticks()
        self.canvas.draw()
        if self.on_view_change:
            self.on_view_change()
        self._cache_axis_preview_background_from_current()

    def _update_time_ticks(self):
        """Force x-axis to include exact view start/end tick values."""
        start = float(self.view_start)
        end = float(self.view_end)
        if not np.isfinite(start) or not np.isfinite(end):
            return
        if end < start:
            start, end = end, start

        span = end - start
        if span <= 0.0:
            self.ax.set_xticks([start])
            return

        auto_ticks = np.asarray(self._tick_locator.tick_values(start, end), dtype=float)
        interior = auto_ticks[(auto_ticks > start) & (auto_ticks < end)]
        ticks = np.concatenate(([start], interior, [end]))

        # Remove near-duplicate values around the bounds.
        eps = max(span * 1e-9, 1e-9)
        dedup = [float(ticks[0])]
        for value in ticks[1:]:
            val = float(value)
            if abs(val - dedup[-1]) > eps:
                dedup.append(val)

        self.ax.set_xticks(dedup)

    def _start_preview_loop(self):
        if self._preview_after_id is not None:
            return
        self._preview_after_id = self.canvas.get_tk_widget().after(
            self.PREVIEW_INTERVAL_MS, self._preview_tick
        )

    def _stop_preview_loop(self):
        if self._preview_after_id is not None:
            self.canvas.get_tk_widget().after_cancel(self._preview_after_id)
            self._preview_after_id = None
        self._preview_dirty = False

    def _request_preview_draw(self):
        self._preview_dirty = True

    def _preview_tick(self):
        self._preview_after_id = None
        if not self._nav_active:
            return

        if self._preview_dirty:
            self._preview_dirty = False
            self.ax.set_xlim(self.view_start, self.view_end)
            self._update_time_ticks()
            self._draw_axis_preview()

        self._preview_after_id = self.canvas.get_tk_widget().after(
            self.PREVIEW_INTERVAL_MS, self._preview_tick
        )

    def _draw_axis_preview(self):
        """Fast path: draw only x-axis on top of frozen spectrogram pixels."""
        if self._axis_preview_background is None or self._axis_preview_bbox is None:
            return
        self.canvas.restore_region(self._axis_preview_background)
        self.ax.draw_artist(self.ax.xaxis)
        self.canvas.blit(self._axis_preview_bbox)

    def _cache_axis_preview_background_from_current(self):
        """Cache axes pixels with x-axis hidden for fast x-axis-only previews."""
        try:
            fig_bbox = self.canvas.figure.bbox
            full_bg = self.canvas.copy_from_bbox(fig_bbox)

            renderer = self.canvas.get_renderer()
            self._axis_preview_bbox = self.ax.get_tightbbox(renderer)
            if self._axis_preview_bbox is None:
                self._axis_preview_bbox = self.ax.bbox

            xaxis_visible = self.ax.xaxis.get_visible()
            self.ax.xaxis.set_visible(False)
            self.canvas.draw()
            self._axis_preview_background = self.canvas.copy_from_bbox(self._axis_preview_bbox)
            self.ax.xaxis.set_visible(xaxis_visible)

            # Restore the full frame without another full draw.
            self.canvas.restore_region(full_bg)
            self.canvas.blit(fig_bbox)
        except Exception:
            # If renderer state is not ready yet, keep preview disabled.
            self._axis_preview_background = None
            self._axis_preview_bbox = None

    # --- Scroll-to-zoom -----------------------------------------------

    def _on_scroll(self, event):
        if event.inaxes is not self.ax or event.xdata is None:
            return

        self._begin_navigation()

        zoom_in = event.step < 0
        t_mouse = max(self.view_start, min(self.view_end, event.xdata))
        current_span = self.view_end - self.view_start

        if zoom_in:
            new_span = max(self.MIN_WINDOW_SEC, current_span * self.ZOOM_FACTOR)
        else:
            new_span = current_span / self.ZOOM_FACTOR
            if new_span >= self.total_duration:
                new_span = self.total_duration

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

        # Defer axis drawing to the 60 Hz preview loop.
        self._request_preview_draw()

        self._cancel_scroll_settle()
        self._scroll_after_id = self.canvas.get_tk_widget().after(
            self.SCROLL_SETTLE_MS, self._on_scroll_settle
        )

    def _on_scroll_settle(self):
        """Fired after wheel inactivity; commits one full redraw."""
        self._scroll_after_id = None
        self._finish_navigation()

    # --- Click + drag pan ---------------------------------------------

    def _on_press(self, event):
        if event.inaxes is not self.ax or event.button != 1 or event.xdata is None:
            return
        self._cancel_scroll_settle()
        self._begin_navigation()
        self._drag_anchor = event.xdata
        self._drag_anchor_px = float(event.x)
        self._drag_view_start = self.view_start
        self._drag_span = self.view_end - self.view_start

    def _on_motion(self, event):
        if self._drag_anchor is None or self._drag_anchor_px is None:
            return

        # Compute pan in pixel-space relative to press point so updates do not
        # feed back through changing xlim transforms.
        delta_px = float(event.x) - self._drag_anchor_px
        span = self._drag_span if self._drag_span is not None else (self.view_end - self.view_start)
        base_start = self._drag_view_start if self._drag_view_start is not None else self.view_start
        px_width = max(1.0, float(self.ax.bbox.width))
        new_start = base_start - (delta_px * span / px_width)
        new_end = new_start + span

        if new_start < 0.0:
            new_start = 0.0
            new_end = span
        if new_end > self.total_duration:
            new_end = self.total_duration
            new_start = max(0.0, new_end - span)

        if abs(new_start - self.view_start) < 1e-12:
            return

        self.view_start = new_start
        self.view_end = new_end

        # Defer axis drawing to the 60 Hz preview loop.
        self._request_preview_draw()

    def _on_release(self, event):
        if event.button != 1 or self._drag_anchor is None:
            return
        self._drag_anchor = None
        self._drag_anchor_px = None
        self._drag_view_start = None
        self._drag_span = None
        self._finish_navigation()




