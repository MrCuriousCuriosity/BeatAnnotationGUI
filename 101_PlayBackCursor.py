"""
Playback cursor overlay for spectrogram (and other) axes.

Defines the visual attributes of every playback cursor in the application
and provides a blit-based draw path so the cursor refreshes at ~60 FPS
without repainting the underlying spectrogram image.
"""


class PlaybackCursor:
    """Animated vertical-line cursor that tracks playback position on an axes.

    Create a new instance each time the host axes is redrawn (i.e. after
    ``ax.clear()`` is called), because ``ax.clear()`` destroys all artists.

    Example
    -------
    # After painting the spectrogram:
    cursor = PlaybackCursor(ax)

    # In the ~60 FPS update loop:
    cursor.update(player.playback_position_sec)
    cursor.draw(canvas, background)
    """

    # === Visual attributes — edit here to change every cursor in the app ===
    COLOR     = "#00FFFF"  # Cursor line colour
    LINEWIDTH = 1      # Line width in points
    ALPHA     = 1.0      # Opacity (0–1)
    ZORDER    = 10       # Drawn on top of the spectrogram image

    def __init__(self, ax):
        """
        Attach a playback cursor to *ax*.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to draw on (typically the spectrogram axes).
        """
        self.ax = ax
        self.line = ax.axvline(
            x=0.0,
            color=self.COLOR,
            linewidth=self.LINEWIDTH,
            alpha=self.ALPHA,
            zorder=self.ZORDER,
            animated=True,   # Excluded from the static draw; updated via blit
        )

    def update(self, position_sec: float) -> None:
        """Move the cursor to a new time position.

        Parameters
        ----------
        position_sec : float
            Playback position in seconds.
        """
        self.line.set_xdata([position_sec])

    def draw(self, canvas, background) -> None:
        """Blit-draw the cursor onto the canvas.

        Parameters
        ----------
        canvas : FigureCanvasTkAgg
            The matplotlib canvas.
        background : object
            Cached background from ``canvas.copy_from_bbox(ax.bbox)``.
            If ``None`` this call is a no-op.
        """
        if background is None:
            return
        canvas.restore_region(background)
        self.ax.draw_artist(self.line)
        canvas.blit(self.ax.bbox)
