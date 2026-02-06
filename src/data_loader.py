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
    """Load a calibration CSV file.

    Supports two formats:

    1. **Semicolon-delimited** (legacy) with columns
       ``ISO_TIMESTAMP;LST;RA_MOUNT;DEC_MOUNT;HA_MOUNT;AZ_DEG;ALT_DEG;PIER_SIDE;STATUS``
       Lines starting with ``#`` are treated as comments.

    2. **Comma-delimited** with a header row containing
       ``Timestamp_UTC_Local,Timestamp_Unix,Status,PierSide,
       HA_Current_Hour,Dec_Current_Deg,Relative_Time_Sec,ErrorCode,Msg``

    The format is auto-detected by inspecting the first non-empty line.

    Each returned dictionary contains:

    * ``timestamp`` – :class:`datetime`
    * ``ha`` – float hours  (Hour Angle)
    * ``dec`` – float degrees
    * ``pier_side`` – int (0/1) or ``None``
    * ``status`` – original status string

    Legacy format additionally provides ``ra``, ``az``, and ``alt``.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Calibration file not found: {filepath}")

    # Peek at first line to decide format
    with open(filepath, "r", encoding="utf-8") as fh:
        first_line = ""
        for line in fh:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                first_line = stripped
                break

    if ";" in first_line and "Timestamp_UTC_Local" not in first_line:
        return _load_semicolon_format(filepath)
    return _load_comma_format(filepath)


def _load_semicolon_format(filepath: Path) -> List[Dict]:
    """Load the legacy semicolon-delimited calibration CSV."""
    records: List[Dict] = []

    with open(filepath, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter=";")
        for row in reader:
            if not row or row[0].strip().startswith("#"):
                continue
            if len(row) < 9:
                logger.warning("Skipping malformed row: %s", row)
                continue

            try:
                ha = _parse_hms(row[4])
                record = {
                    "timestamp": datetime.fromisoformat(row[0].strip()),
                    "ra": _parse_hms(row[2]),
                    "dec": _parse_hms(row[3]),
                    "ha": ha,
                    "az": float(row[5].strip()),
                    "alt": float(row[6].strip()),
                    "pier_side": _parse_pier_side(row[7]),
                    "status": row[8].strip(),
                }
                records.append(record)
            except (ValueError, IndexError) as exc:
                logger.warning("Skipping row due to parse error: %s – %s", row, exc)
                continue

    logger.info("Loaded %d records from %s (semicolon format)", len(records), filepath)
    return records


def _load_comma_format(filepath: Path) -> List[Dict]:
    """Load the comma-delimited calibration CSV with header row.

    Columns:
    ``Timestamp_UTC_Local,Timestamp_Unix,Status,PierSide,
    HA_Current_Hour,Dec_Current_Deg,Relative_Time_Sec,ErrorCode,Msg``
    """
    records: List[Dict] = []

    with open(filepath, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter=",")
        header = None
        for row in reader:
            if not row:
                continue
            # Skip the header row
            if header is None:
                header = [c.strip() for c in row]
                continue

            if len(row) < 6:
                logger.warning("Skipping malformed row: %s", row)
                continue

            try:
                record = {
                    "timestamp": datetime.fromisoformat(row[0].strip()),
                    "ha": float(row[4].strip()),
                    "dec": float(row[5].strip()),
                    "pier_side": _parse_pier_side(row[3]),
                    "status": row[2].strip(),
                }
                records.append(record)
            except (ValueError, IndexError) as exc:
                logger.warning("Skipping row due to parse error: %s – %s", row, exc)
                continue

    logger.info("Loaded %d records from %s (comma format)", len(records), filepath)
    return records
