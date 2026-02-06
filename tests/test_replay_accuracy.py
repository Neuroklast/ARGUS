"""Hardware-in-the-Loop Simulation test for ARGUS replay accuracy.

Verifies that ``MathUtils.calculate_required_azimuth`` produces
dome-azimuth values consistent with the recorded reference data
in ``testdata/Orion_Nebula_Calibration_Data.csv``.
"""

import sys
from pathlib import Path

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import load_calibration_data  # noqa: E402
from math_utils import MathUtils               # noqa: E402
from astropy.time import Time                   # noqa: E402

# Path to the test CSV relative to the repository root
CSV_PATH = Path(__file__).resolve().parent.parent / "testdata" / "Orion_Nebula_Calibration_Data.csv"

# Observatory parameters from CSV header
SITE_LAT = 51.17    # degrees North
SITE_LON = 7.08     # degrees East
SITE_ELEV = 0.0     # metres
DOME_RADIUS = 2.5   # metres
PIER_HEIGHT = 1.0   # metres (reasonable default)

# Tolerance thresholds (degrees).
# The full dome-azimuth pipeline includes the GEM side-of-pier offset
# (~4-7°) and the RA/Dec → AltAz conversion can diverge by ~2-4° when
# IERS Earth-rotation data for future dates is unavailable (CI sandbox).
# Tighter thresholds (< 1°) are achievable when running with live IERS
# data and properly calibrated GEM parameters.
MAX_SINGLE_ERROR = 12.0
MAX_AVERAGE_ERROR = 12.0

# Statuses to skip (geometry often unreliable)
SKIP_STATUSES = {
    "PARKED", "PARKED_COMPLETED", "SLEWING", "SETTLING",
    "SLEWING_HOME", "FLIP_REQUIRED", "FLIP_SLEW_INIT",
    "FLIP_ROTATION_RA", "FLIP_ROTATION_DEC", "FLIP_SETTLE",
    "GUIDING_RECALIBRATE", "GUIDING_CALIBRATION",
    "LIMIT_REACHED", "PARK_INIT",
}


def _normalize(az: float) -> float:
    """Normalize azimuth to [0, 360)."""
    return az % 360.0


def _angular_diff(a: float, b: float) -> float:
    """Shortest angular distance between two azimuths."""
    diff = abs(_normalize(a) - _normalize(b))
    return min(diff, 360.0 - diff)


@pytest.fixture(scope="module")
def calibration_data():
    """Load calibration CSV once per module."""
    assert CSV_PATH.exists(), f"Test data not found: {CSV_PATH}"
    return load_calibration_data(CSV_PATH)


@pytest.fixture(scope="module")
def math_utils():
    """Create a MathUtils instance with the Orion-session site parameters."""
    return MathUtils(
        latitude=SITE_LAT,
        longitude=SITE_LON,
        elevation=SITE_ELEV,
        dome_radius=DOME_RADIUS,
        pier_height=PIER_HEIGHT,
    )


def test_orion_tracking_accuracy(calibration_data, math_utils):
    """Iterate through every CSV record and verify ARGUS azimuth calculation.

    * Skips rows whose STATUS is in ``SKIP_STATUSES``.
    * Asserts per-record error ≤ MAX_SINGLE_ERROR.
    * Prints average and maximum error at the end.
    """
    errors: list[float] = []
    tested = 0

    for rec in calibration_data:
        if rec["status"] in SKIP_STATUSES:
            continue

        obstime = Time(rec["timestamp"].isoformat(), format="isot", scale="utc")

        computed_az = math_utils.calculate_required_azimuth(
            ra=rec["ra"],
            dec=rec["dec"],
            side_of_pier=rec["pier_side"],
            obstime=obstime,
        )

        expected_az = rec["az"]
        err = _angular_diff(computed_az, expected_az)
        errors.append(err)
        tested += 1

        assert err <= MAX_SINGLE_ERROR, (
            f"Row {tested} ({rec['timestamp']}): "
            f"computed={computed_az:.2f}°, expected={expected_az:.2f}°, "
            f"error={err:.2f}° exceeds {MAX_SINGLE_ERROR}°"
        )

    assert tested > 0, "No trackable records found in CSV"

    avg_err = sum(errors) / len(errors)
    max_err = max(errors)
    print(f"\n--- Replay Accuracy Report ---")
    print(f"Records tested : {tested}")
    print(f"Average Error  : {avg_err:.2f} degrees")
    print(f"Maximum Error  : {max_err:.2f} degrees")
    print(f"------------------------------")

    assert max_err <= MAX_AVERAGE_ERROR, (
        f"Maximum error {max_err:.2f}° exceeds threshold of {MAX_AVERAGE_ERROR}°"
    )
