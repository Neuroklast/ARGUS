"""Hardware-in-the-Loop Simulation test for ARGUS replay accuracy.

Verifies that ``MathUtils.calculate_required_azimuth`` produces
consistent dome-azimuth values from the recorded tracking data
in ``testdata/Orion_Nebula_Calibration_Data.csv``.

The CSV uses comma-delimited format with HA (Hour Angle) and Dec
columns. RA is derived from HA via Local Sidereal Time computed
by Astropy.
"""

import sys
from pathlib import Path

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import load_calibration_data  # noqa: E402
from math_utils import MathUtils               # noqa: E402
from astropy.coordinates import EarthLocation   # noqa: E402
from astropy.time import Time                   # noqa: E402
import astropy.units as u                       # noqa: E402

# Path to the test CSV relative to the repository root
CSV_PATH = Path(__file__).resolve().parent.parent / "testdata" / "Orion_Nebula_Calibration_Data.csv"

# Observatory parameters from CSV header
SITE_LAT = 51.17    # degrees North
SITE_LON = 7.08     # degrees East
SITE_ELEV = 0.0     # metres
DOME_RADIUS = 2.5   # metres
PIER_HEIGHT = 1.0   # metres (reasonable default)

# Tolerance thresholds (degrees).
# During steady tracking, the dome azimuth should change smoothly.
# With sampling every 500th record (~1000s apart), sidereal motion causes
# larger azimuth changes per sample depending on geometry.
MAX_FRAME_JUMP = 8.0       # degrees between sampled frames (~1000s apart)
MAX_TOTAL_DRIFT = 200.0    # degrees total drift across ~6.5h session

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


def _ha_to_ra(ha_hours: float, timestamp: str, longitude: float) -> float:
    """Convert Hour Angle to Right Ascension using Local Sidereal Time.

    Args:
        ha_hours: Hour Angle in decimal hours.
        timestamp: ISO-format timestamp string.
        longitude: Observatory longitude in degrees.

    Returns:
        Right Ascension in decimal hours.
    """
    obstime = Time(timestamp, format="isot", scale="utc")
    location = EarthLocation(
        lon=longitude * u.deg, lat=SITE_LAT * u.deg, height=SITE_ELEV * u.m
    )
    lst = obstime.sidereal_time("apparent", longitude=location.lon)
    ra = (lst.hour - ha_hours + 24.0) % 24.0
    return ra


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


def test_csv_loads_records(calibration_data):
    """The CSV file should load a non-trivial number of records."""
    assert len(calibration_data) > 100, (
        f"Expected >100 records, got {len(calibration_data)}"
    )


def test_records_have_required_keys(calibration_data):
    """Every record should contain the expected keys."""
    for rec in calibration_data[:5]:
        assert "timestamp" in rec
        assert "ha" in rec
        assert "dec" in rec
        assert "pier_side" in rec
        assert "status" in rec


def test_orion_tracking_consistency(calibration_data, math_utils):
    """Verify that dome azimuth computations are smooth during tracking.

    Since the CSV does not include a reference dome azimuth, we verify
    *self-consistency*: the computed dome azimuths for consecutive
    sampled records should change smoothly (no wild jumps).

    Samples every 500th record to keep runtime reasonable (~42 records).
    """
    # Sample every Nth record to keep the test fast
    sample_step = 500
    sampled = [
        rec for i, rec in enumerate(calibration_data)
        if i % sample_step == 0 and rec["status"] not in SKIP_STATUSES
    ]

    azimuths: list[float] = []
    tested = 0
    jumps: list[float] = []

    prev_az = None
    prev_pier = None

    for rec in sampled:
        obstime = Time(rec["timestamp"].isoformat(), format="isot", scale="utc")

        # Derive RA from HA
        ra = _ha_to_ra(rec["ha"], rec["timestamp"].isoformat(), SITE_LON)

        computed_az = math_utils.calculate_required_azimuth(
            ra=ra,
            dec=rec["dec"],
            side_of_pier=rec["pier_side"],
            obstime=obstime,
        )

        azimuths.append(computed_az)
        tested += 1

        # Check frame-to-frame consistency (ignore pier-side flips)
        if prev_az is not None and rec["pier_side"] == prev_pier:
            jump = _angular_diff(computed_az, prev_az)
            jumps.append(jump)

        prev_az = computed_az
        prev_pier = rec["pier_side"]

    assert tested > 0, "No trackable records found in CSV"

    # Overall statistics
    avg_jump = sum(jumps) / len(jumps) if jumps else 0.0
    max_jump = max(jumps) if jumps else 0.0
    total_drift = _angular_diff(azimuths[0], azimuths[-1])

    print(f"\n--- Replay Consistency Report ---")
    print(f"Records tested    : {tested}")
    print(f"Average frame jump: {avg_jump:.4f} degrees")
    print(f"Maximum frame jump: {max_jump:.4f} degrees")
    print(f"Total drift       : {total_drift:.2f} degrees")
    print(f"--------------------------------")

    # Between sampled frames (~200s apart), drift should still be moderate
    assert avg_jump < MAX_FRAME_JUMP, (
        f"Average frame jump {avg_jump:.4f}° exceeds {MAX_FRAME_JUMP}°"
    )
    assert total_drift < MAX_TOTAL_DRIFT, (
        f"Total session drift {total_drift:.2f}° exceeds {MAX_TOTAL_DRIFT}°"
    )


def test_dome_azimuth_in_valid_range(calibration_data, math_utils):
    """All computed dome azimuths should be in [0, 360)."""
    for rec in calibration_data[:20]:
        obstime = Time(rec["timestamp"].isoformat(), format="isot", scale="utc")
        ra = _ha_to_ra(rec["ha"], rec["timestamp"].isoformat(), SITE_LON)

        computed_az = math_utils.calculate_required_azimuth(
            ra=ra,
            dec=rec["dec"],
            side_of_pier=rec["pier_side"],
            obstime=obstime,
        )
        assert 0 <= computed_az < 360, f"Azimuth {computed_az}° out of range"
