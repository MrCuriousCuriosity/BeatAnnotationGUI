"""MEI panel widget shown below the spectrogram."""

import tkinter as tk


class MeiPanel:
	"""Simple bordered panel placed below the spectrogram."""

	def __init__(self, parent):
		self.parent = parent
		self.frame = tk.Frame(
			parent,
			bd=0,
			relief="flat",
			highlightthickness=1,
		)

	def place(self, x, y, width, height):
		"""Place panel by center coordinates and size."""
		self.frame.place(
			anchor="center",
			x=int(x),
			y=int(y),
			width=max(1, int(width)),
			height=max(1, int(height)),
		)

	def set_theme(self, border_color, bg_color):
		"""Apply border and background colours."""
		self.frame.configure(
			highlightbackground=border_color,
			highlightcolor=border_color,
			bg=bg_color,
		)