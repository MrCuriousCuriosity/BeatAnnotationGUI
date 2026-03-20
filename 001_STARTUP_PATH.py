"""
Launch Beat Annotation GUI with a hardcoded startup audio path.

This wrapper keeps the main GUI code clean while allowing quick local startup
with a fixed audio file.
"""

from pathlib import Path
import importlib.util
import tkinter as tk
from tkinter import messagebox

# Set your audio file path here (absolute path recommended).
HARDCODED_AUDIO_PATH = "Chopin Nocturne, op 27 no 2 - Maria João Pires live at Jardin Musical.mp3"


def _load_main_module():
    """Dynamically load the numeric-prefixed main module."""
    script_dir = Path(__file__).parent
    main_path = script_dir / "000_main_BA_GUI.py"
    spec = importlib.util.spec_from_file_location("main_ba_gui", main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_audio_path(raw_path):
    """Resolve absolute/relative paths from anywhere the script is launched."""
    script_dir = Path(__file__).parent
    candidate = Path(raw_path).expanduser()

    if candidate.is_file():
        return candidate

    local_candidate = (script_dir / raw_path).expanduser()
    if local_candidate.is_file():
        return local_candidate

    return None


def main():
    module = _load_main_module()
    audio_path = _resolve_audio_path(HARDCODED_AUDIO_PATH)

    root = tk.Tk()
    app = module.SpectrogramApp(root)

    if audio_path is not None:
        root.after(0, lambda: app.open_file(str(audio_path)))
    else:
        root.after(
            0,
            lambda: messagebox.showwarning(
                "Startup Audio",
                f"Hardcoded audio file not found:\n{HARDCODED_AUDIO_PATH}",
            ),
        )

    root.mainloop()


if __name__ == "__main__":
    main()
