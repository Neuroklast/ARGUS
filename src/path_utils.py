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
