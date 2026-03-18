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
