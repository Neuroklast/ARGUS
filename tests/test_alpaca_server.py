"""Tests for the ASCOM Alpaca dome server.

Uses Flask's test client so no network port is opened.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from alpaca_server import AlpacaDomeServer


@pytest.fixture()
def controller():
    """Create a mock ArgusController with the attributes the server reads."""
    ctrl = MagicMock()
    ctrl.current_azimuth = 123.4
    ctrl.is_slewing = False
    ctrl.is_parked = False
    ctrl.is_slaved = False
    ctrl.config = {"hardware": {"homing": {"enabled": True}}}
    return ctrl


@pytest.fixture()
def client(controller):
    """Return a Flask test client wired to the mock controller."""
    server = AlpacaDomeServer(controller)
    server._app.config["TESTING"] = True
    with server._app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Management endpoints
# ---------------------------------------------------------------------------
class TestManagement:
    def test_connected(self, client):
        rv = client.get("/api/v1/dome/0/connected")
        assert rv.status_code == 200
        assert rv.get_json()["Value"] is True

    def test_name(self, client):
        rv = client.get("/api/v1/dome/0/name")
        assert rv.get_json()["Value"] == "ARGUS Smart Dome"

    def test_description(self, client):
        rv = client.get("/api/v1/dome/0/description")
        assert "Dome Controller" in rv.get_json()["Value"]

    def test_driverinfo(self, client):
        rv = client.get("/api/v1/dome/0/driverinfo")
        assert "ARGUS" in rv.get_json()["Value"]

    def test_has_transaction_ids(self, client):
        rv = client.get("/api/v1/dome/0/name")
        data = rv.get_json()
        assert "ClientTransactionID" in data
        assert "ServerTransactionID" in data
        assert "ErrorNumber" in data


# ---------------------------------------------------------------------------
# Status endpoints
# ---------------------------------------------------------------------------
class TestStatus:
    def test_azimuth(self, client, controller):
        controller.current_azimuth = 270.0
        rv = client.get("/api/v1/dome/0/azimuth")
        assert rv.get_json()["Value"] == 270.0

    def test_slewing(self, client, controller):
        controller.is_slewing = True
        rv = client.get("/api/v1/dome/0/slewing")
        assert rv.get_json()["Value"] is True

    def test_atpark(self, client, controller):
        controller.is_parked = True
        rv = client.get("/api/v1/dome/0/atpark")
        assert rv.get_json()["Value"] is True

    def test_shutterstatus(self, client):
        rv = client.get("/api/v1/dome/0/shutterstatus")
        assert rv.get_json()["Value"] == 0  # Open


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------
class TestCapabilities:
    def test_canslave(self, client):
        rv = client.get("/api/v1/dome/0/canslave")
        assert rv.get_json()["Value"] is True

    def test_canpark(self, client):
        rv = client.get("/api/v1/dome/0/canpark")
        assert rv.get_json()["Value"] is True

    def test_canfindhome(self, client):
        rv = client.get("/api/v1/dome/0/canfindhome")
        assert rv.get_json()["Value"] is True

    def test_cansetazimuth(self, client):
        rv = client.get("/api/v1/dome/0/cansetazimuth")
        assert rv.get_json()["Value"] is True


# ---------------------------------------------------------------------------
# Slaving
# ---------------------------------------------------------------------------
class TestSlaving:
    def test_get_slaved_default(self, client, controller):
        controller.is_slaved = False
        rv = client.get("/api/v1/dome/0/slaved")
        assert rv.get_json()["Value"] is False

    def test_put_slaved_true(self, client, controller):
        rv = client.put("/api/v1/dome/0/slaved", data={"Slaved": "true"})
        assert rv.status_code == 200
        assert controller.is_slaved is True

    def test_put_slaved_false(self, client, controller):
        controller.is_slaved = True
        rv = client.put("/api/v1/dome/0/slaved", data={"Slaved": "false"})
        assert rv.status_code == 200
        assert controller.is_slaved is False


# ---------------------------------------------------------------------------
# Movement commands
# ---------------------------------------------------------------------------
class TestMovement:
    def test_slewtoazimuth(self, client, controller):
        controller.is_slaved = False
        rv = client.put(
            "/api/v1/dome/0/slewtoazimuth", data={"Azimuth": "180.0"}
        )
        assert rv.status_code == 200
        controller.move_dome.assert_called_once_with(180.0)

    def test_slewtoazimuth_rejected_when_slaved(self, client, controller):
        controller.is_slaved = True
        rv = client.put(
            "/api/v1/dome/0/slewtoazimuth", data={"Azimuth": "90"}
        )
        data = rv.get_json()
        assert data["ErrorNumber"] != 0

    def test_park(self, client, controller):
        rv = client.put("/api/v1/dome/0/park")
        assert rv.status_code == 200
        controller.park_dome.assert_called_once()

    def test_abortslew(self, client, controller):
        rv = client.put("/api/v1/dome/0/abortslew")
        assert rv.status_code == 200
        controller.stop_dome.assert_called_once()


# ---------------------------------------------------------------------------
# Discovery / management
# ---------------------------------------------------------------------------
class TestDiscovery:
    def test_apiversions(self, client):
        rv = client.get("/management/apiversions")
        assert 1 in rv.get_json()["Value"]

    def test_configureddevices(self, client):
        rv = client.get("/management/v1/configureddevices")
        devices = rv.get_json()["Value"]
        assert len(devices) == 1
        assert devices[0]["DeviceType"] == "Dome"
