"""
ARGUS - Advanced Rotation Guidance Using Sensors
CSV Data Loader Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Loads recorded calibration data from semicolon-delimited CSV files
for use in the replay/demo system.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _parse_hms(value: str) -> float:
    """Parse a HH:MM:SS or ±DD:MM:SS string to a float number.

    For RA values the result is in decimal hours, for Dec values in
    decimal degrees – the caller decides the interpretation.
    """
    value = value.strip()
    sign = 1.0
    if value.startswith("-"):
        sign = -1.0
        value = value[1:]
    elif value.startswith("+"):
        value = value[1:]

    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError(f"Cannot parse HMS/DMS value: {value!r}")

    h_or_d = float(parts[0])
    m = float(parts[1])
    s = float(parts[2])
    return sign * (h_or_d + m / 60.0 + s / 3600.0)


def _parse_pier_side(value: str) -> int | None:
    """Convert PIER_SIDE string to ASCOM integer.

    ``EAST`` → 0, ``WEST`` → 1, anything else → ``None``.
    """
    value = value.strip().upper()
    if value == "EAST":
        return 0
    if value == "WEST":
        return 1
    return None


def load_calibration_data(filepath: str | Path) -> List[Dict]:
    """Load a semicolon-delimited calibration CSV file.

    Lines starting with ``#`` are treated as comments/header and skipped.
    Empty lines are also skipped.

    Each returned dictionary contains:

    * ``timestamp`` – :class:`datetime` parsed from ``ISO_TIMESTAMP``
    * ``ra`` – float hours  (parsed from ``RA_MOUNT``)
    * ``dec`` – float degrees (parsed from ``DEC_MOUNT``)
    * ``az`` – float degrees  (from ``AZ_DEG``)
    * ``alt`` – float degrees (from ``ALT_DEG``)
    * ``pier_side`` – int (0/1) or ``None``
    * ``status`` – original status string
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Calibration file not found: {filepath}")

    records: List[Dict] = []

    with open(filepath, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter=";")
        for row in reader:
            # Skip empty lines and comment/header lines
            if not row or row[0].strip().startswith("#"):
                continue

            # Expected columns (see COLUMNS header):
            # ISO_TIMESTAMP;LST;RA_MOUNT;DEC_MOUNT;HA_MOUNT;AZ_DEG;ALT_DEG;PIER_SIDE;STATUS
            if len(row) < 9:
                logger.warning("Skipping malformed row: %s", row)
                continue

            try:
                record = {
                    "timestamp": datetime.fromisoformat(row[0].strip()),
                    "ra": _parse_hms(row[2]),       # RA in decimal hours
                    "dec": _parse_hms(row[3]),       # Dec in decimal degrees
                    "az": float(row[5].strip()),     # Azimuth in degrees
                    "alt": float(row[6].strip()),    # Altitude in degrees
                    "pier_side": _parse_pier_side(row[7]),
                    "status": row[8].strip(),
                }
                records.append(record)
            except (ValueError, IndexError) as exc:
                logger.warning("Skipping row due to parse error: %s – %s", row, exc)
                continue

    logger.info("Loaded %d records from %s", len(records), filepath)
    return records
