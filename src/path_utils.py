"""
ARGUS - Advanced Rotation Guidance Using Sensors
Path Utilities

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides a portable base-path resolver used by all modules that need
to locate resources (``config.yaml``, ``assets/``, …) relative to
the application root.
"""

import sys
from pathlib import Path


def get_base_path() -> Path:
    """Return the application root directory.

    * **Frozen / EXE** (``sys.frozen`` is set): the directory that contains
      the executable, so the user can place ``config.yaml`` and ``assets/``
      next to the ``.exe``.
    * **Development / Script**: two levels up from this source file, which
      equals the repository root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_path(relative: str) -> Path:
    """Locate a resource file/directory, checking all known locations.

    Resolution order (first match wins):

    1. ``get_base_path() / relative`` – the directory beside the ``.exe``
       (frozen) or the repository root (development).
    2. ``sys._MEIPASS / relative`` – PyInstaller's internal data directory
       (``_internal/``).  Only checked in frozen builds.

    If no location contains the resource the function returns the primary
    base-path location so callers can generate a meaningful "not-found"
    message with the expected path.
    """
    primary = get_base_path() / relative
    if primary.exists():
        return primary

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = Path(meipass) / relative
            if candidate.exists():
                return candidate

    return primary  # fallback – allows callers to report the expected path
