"""
Audio playback engine for the Beat Annotation GUI.

Wraps sounddevice to provide play / stop / pause controls and a public
`playback_position_sec` float that is updated every UI tick.
"""

import time
import numpy as np

try:
    import sounddevice as sd
except ImportError as exc:
    raise ImportError(
        "sounddevice is required for audio playback.  "
        "Install it with:  pip install sounddevice"
    ) from exc


class AudioPlayer:
    """Manages audio playback state and exposes current position in time.

    Usage
    -----
    1. Call ``load(audio, sr)`` once after a file is opened.
    2. Call ``play()`` / ``pause()`` / ``stop()`` from UI buttons.
    3. In the UI update loop (every ~17 ms) call ``update_position()`` and
       then read ``playback_position_sec`` to move cursors / indicators.
    """

    def __init__(self):
        # === Public: read this every UI tick to drive cursors ===
        self.playback_position_sec: float = 0.0

        self._audio: np.ndarray | None = None
        self._sr: int | None = None
        self._duration: float = 0.0

        self._is_playing: bool = False
        self._start_wall_time: float | None = None
        self._start_audio_sec: float = 0.0

    # --- Public API ---------------------------------------------------

    def load(self, audio: np.ndarray, sr: int) -> None:
        """Store audio data without starting playback.

        Parameters
        ----------
        audio : np.ndarray
            Mono float32 audio array.
        sr : int
            Sample rate in Hz.
        """
        self.stop()
        self._audio = np.asarray(audio, dtype=np.float32)
        self._sr = int(sr)
        self._duration = len(self._audio) / self._sr
        self.playback_position_sec = 0.0

    def play(self, start_sec: float | None = None) -> None:
        """Start playback from *start_sec* (defaults to current position).

        Parameters
        ----------
        start_sec : float | None
            Position in seconds to begin from.  Uses current
            ``playback_position_sec`` when *None*.
        """
        if self._audio is None:
            return

        if start_sec is None:
            start_sec = self.playback_position_sec

        # Clamp to valid range; restart from 0 if already at end
        start_sec = max(0.0, min(start_sec, self._duration))
        if start_sec >= self._duration:
            start_sec = 0.0

        self._start_audio_sec = start_sec
        start_sample = int(start_sec * self._sr)
        audio_slice = self._audio[start_sample:]

        sd.stop()
        sd.play(audio_slice, self._sr)
        self._start_wall_time = time.perf_counter()
        self._is_playing = True
        self.playback_position_sec = start_sec

    def pause(self) -> None:
        """Pause playback, preserving the current position."""
        if not self._is_playing:
            return
        self.update_position()   # lock in exact position before stopping
        sd.stop()
        self._is_playing = False
        self._start_wall_time = None

    def resume(self) -> None:
        """Resume from the current paused position."""
        if self._is_playing:
            return
        self.play(start_sec=self.playback_position_sec)

    def stop(self) -> None:
        """Stop playback and reset cursor to 0."""
        sd.stop()
        self._is_playing = False
        self._start_wall_time = None
        self.playback_position_sec = 0.0

    @property
    def is_playing(self) -> bool:
        """``True`` while audio is actively streaming."""
        return self._is_playing

    @property
    def duration(self) -> float:
        """Total audio duration in seconds (0.0 if no audio loaded)."""
        return self._duration

    # --- Called every UI tick -----------------------------------------

    def update_position(self) -> None:
        """Advance ``playback_position_sec`` based on elapsed wall-clock time.

        Call this once per UI refresh tick (e.g. every 17 ms) so that
        ``playback_position_sec`` stays in sync with the actual stream.
        Automatically sets ``is_playing`` to ``False`` when the end is reached.
        """
        if not self._is_playing or self._start_wall_time is None:
            return
        elapsed = time.perf_counter() - self._start_wall_time
        pos = self._start_audio_sec + elapsed
        if pos >= self._duration:
            pos = self._duration
            self._is_playing = False
            sd.stop()
        self.playback_position_sec = pos
