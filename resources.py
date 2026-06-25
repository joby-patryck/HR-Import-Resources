"""
Resource path resolution that works both in development and inside a
packaged (PyInstaller) build.

Two distinct kinds of file:

- **Bundled read-only resources** (e.g. ``tenants.json``) are shipped *inside*
  the frozen app. PyInstaller unpacks them to a temporary directory exposed as
  ``sys._MEIPASS``; in development they sit next to this module.

- **External user-editable files** (e.g. ``dont_suspend.csv``) live *next to the
  executable* so they can be edited without rebuilding. On macOS the executable
  lives deep inside ``HR Import.app/Contents/MacOS``; we climb out so the file
  is expected alongside the ``.app`` itself, where a user can actually see it.
"""
import sys
from pathlib import Path


def _bundle_dir() -> Path:
    """Directory holding read-only bundled resources."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def _app_dir() -> Path:
    """Directory for external, user-editable files (next to the app)."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # Climb out of "HR Import.app/Contents/MacOS/HR Import" to the folder
        # that actually contains the .app bundle.
        if (
            sys.platform == "darwin"
            and exe.parent.name == "MacOS"
            and exe.parent.parent.name == "Contents"
        ):
            return exe.parents[3]
        return exe.parent
    return Path(__file__).resolve().parent


def resource_path(name: str) -> Path:
    """Path to a read-only resource bundled inside the app."""
    return _bundle_dir() / name


def external_path(name: str) -> Path:
    """Path to a user-editable file expected alongside the executable/app."""
    return _app_dir() / name
