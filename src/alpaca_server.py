"""
ARGUS - Advanced Rotation Guidance Using Sensors
ASCOM Alpaca Dome Server

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Exposes the ARGUS dome controller as an ASCOM Alpaca device so that
observatory automation software (NINA, Voyager, …) can slave the dome
directly.

The server runs in a background daemon thread on port 11111 (Alpaca
standard) and delegates all dome operations to the ArgusController.
"""

import itertools
import logging
import threading
from typing import Any, Optional

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)

# ASCOM Alpaca error codes
ALPACA_OK = 0
ALPACA_NOT_IMPLEMENTED = 0x400
ALPACA_INVALID_VALUE = 0x401
ALPACA_INVALID_OPERATION = 0x40C


def _alpaca_response(
    value: Any = None,
    error_number: int = ALPACA_OK,
    error_message: str = "",
    server_tid: int = 0,
) -> dict:
    """Build a standard Alpaca JSON response envelope."""
    resp: dict = {}
    if value is not None:
        resp["Value"] = value
    resp["ClientTransactionID"] = request.values.get(
        "ClientTransactionID", 0, type=int
    )
    resp["ServerTransactionID"] = server_tid
    resp["ErrorNumber"] = error_number
    resp["ErrorMessage"] = error_message
    return resp


class AlpacaDomeServer:
    """ASCOM Alpaca REST server for the ARGUS dome controller.

    Args:
        controller: Reference to the running ``ArgusController``.
        host: Network interface to listen on (default ``0.0.0.0``).
        port: TCP port (default ``11111`` – Alpaca standard).
    """

    def __init__(self, controller, host: str = "0.0.0.0", port: int = 11111):
        self._controller = controller
        self._host = host
        self._port = port
        self._tid = itertools.count(1)
        self._thread: Optional[threading.Thread] = None

        # Flask app (suppress default request logging for cleanliness)
        self._app = Flask("AlpacaDomeServer")
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.WARNING)
        self._register_routes()

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------
    def _register_routes(self) -> None:  # noqa: C901 (route table)
        app = self._app
        prefix = "/api/v1/dome/0"

        # --- Management ---------------------------------------------------
        @app.route(f"{prefix}/connected", methods=["GET"])
        def get_connected():
            return jsonify(_alpaca_response(True, server_tid=next(self._tid)))

        @app.route(f"{prefix}/connected", methods=["PUT"])
        def put_connected():
            return jsonify(_alpaca_response(server_tid=next(self._tid)))

        @app.route(f"{prefix}/name", methods=["GET"])
        def get_name():
            return jsonify(
                _alpaca_response("ARGUS Smart Dome", server_tid=next(self._tid))
            )

        @app.route(f"{prefix}/description", methods=["GET"])
        def get_description():
            return jsonify(
                _alpaca_response(
                    "AI-powered Dome Controller", server_tid=next(self._tid)
                )
            )

        @app.route(f"{prefix}/driverinfo", methods=["GET"])
        def get_driverinfo():
            return jsonify(
                _alpaca_response("ARGUS v1.0", server_tid=next(self._tid))
            )

        @app.route(f"{prefix}/driverversion", methods=["GET"])
        def get_driverversion():
            return jsonify(
                _alpaca_response("1.0", server_tid=next(self._tid))
            )

        @app.route(f"{prefix}/interfaceversion", methods=["GET"])
        def get_interfaceversion():
            return jsonify(
                _alpaca_response(1, server_tid=next(self._tid))
            )

        @app.route(f"{prefix}/supportedactions", methods=["GET"])
        def get_supportedactions():
            return jsonify(
                _alpaca_response([], server_tid=next(self._tid))
            )

        # --- Status -------------------------------------------------------
        @app.route(f"{prefix}/azimuth", methods=["GET"])
        def get_azimuth():
            az = getattr(self._controller, "current_azimuth", 0.0)
            return jsonify(_alpaca_response(az, server_tid=next(self._tid)))

        @app.route(f"{prefix}/slewing", methods=["GET"])
        def get_slewing():
            val = getattr(self._controller, "is_slewing", False)
            return jsonify(_alpaca_response(val, server_tid=next(self._tid)))

        @app.route(f"{prefix}/atpark", methods=["GET"])
        def get_atpark():
            val = getattr(self._controller, "is_parked", False)
            return jsonify(_alpaca_response(val, server_tid=next(self._tid)))

        @app.route(f"{prefix}/athome", methods=["GET"])
        def get_athome():
            return jsonify(_alpaca_response(False, server_tid=next(self._tid)))

        @app.route(f"{prefix}/shutterstatus", methods=["GET"])
        def get_shutterstatus():
            # 0 = Open, 1 = Closed; no shutter control → always open
            return jsonify(_alpaca_response(0, server_tid=next(self._tid)))

        # --- Capabilities -------------------------------------------------
        @app.route(f"{prefix}/canfindhome", methods=["GET"])
        def get_canfindhome():
            homing = self._controller.config.get("hardware", {}).get("homing", {})
            return jsonify(
                _alpaca_response(
                    homing.get("enabled", False), server_tid=next(self._tid)
                )
            )

        @app.route(f"{prefix}/canpark", methods=["GET"])
        def get_canpark():
            return jsonify(_alpaca_response(True, server_tid=next(self._tid)))

        @app.route(f"{prefix}/cansetazimuth", methods=["GET"])
        def get_cansetazimuth():
            return jsonify(_alpaca_response(True, server_tid=next(self._tid)))

        @app.route(f"{prefix}/cansetpark", methods=["GET"])
        def get_cansetpark():
            return jsonify(_alpaca_response(False, server_tid=next(self._tid)))

        @app.route(f"{prefix}/cansetshutter", methods=["GET"])
        def get_cansetshutter():
            return jsonify(_alpaca_response(False, server_tid=next(self._tid)))

        @app.route(f"{prefix}/canslave", methods=["GET"])
        def get_canslave():
            return jsonify(_alpaca_response(True, server_tid=next(self._tid)))

        @app.route(f"{prefix}/cansyncazimuth", methods=["GET"])
        def get_cansyncazimuth():
            return jsonify(_alpaca_response(False, server_tid=next(self._tid)))

        # --- Slaving ------------------------------------------------------
        @app.route(f"{prefix}/slaved", methods=["GET"])
        def get_slaved():
            val = getattr(self._controller, "is_slaved", False)
            return jsonify(_alpaca_response(val, server_tid=next(self._tid)))

        @app.route(f"{prefix}/slaved", methods=["PUT"])
        def put_slaved():
            raw = request.values.get("Slaved", "false")
            slaved = str(raw).lower() in ("true", "1", "yes")
            self._controller.is_slaved = slaved
            logger.info("Alpaca: Slaved set to %s", slaved)
            return jsonify(_alpaca_response(server_tid=next(self._tid)))

        # --- Movement commands --------------------------------------------
        @app.route(f"{prefix}/slewtoazimuth", methods=["PUT"])
        def put_slewtoazimuth():
            tid = next(self._tid)
            if getattr(self._controller, "is_slaved", False):
                return jsonify(
                    _alpaca_response(
                        error_number=ALPACA_INVALID_OPERATION,
                        error_message="Dome is slaved – manual slew rejected",
                        server_tid=tid,
                    )
                )

            try:
                target = float(request.values.get("Azimuth", 0))
            except (TypeError, ValueError):
                return jsonify(
                    _alpaca_response(
                        error_number=ALPACA_INVALID_VALUE,
                        error_message="Invalid Azimuth value",
                        server_tid=tid,
                    )
                )

            if hasattr(self._controller, "move_dome"):
                self._controller.move_dome(target)
            return jsonify(_alpaca_response(server_tid=tid))

        @app.route(f"{prefix}/park", methods=["PUT"])
        def put_park():
            if hasattr(self._controller, "park_dome"):
                self._controller.park_dome()
            return jsonify(_alpaca_response(server_tid=next(self._tid)))

        @app.route(f"{prefix}/abortslew", methods=["PUT"])
        def put_abortslew():
            if hasattr(self._controller, "stop_dome"):
                self._controller.stop_dome()
            return jsonify(_alpaca_response(server_tid=next(self._tid)))

        @app.route(f"{prefix}/findhome", methods=["PUT"])
        def put_findhome():
            if hasattr(self._controller, "home_dome"):
                self._controller.home_dome()
            return jsonify(_alpaca_response(server_tid=next(self._tid)))

        # --- Alpaca management discovery ----------------------------------
        @app.route("/management/apiversions", methods=["GET"])
        def mgmt_apiversions():
            return jsonify({"Value": [1]})

        @app.route("/management/v1/configureddevices", methods=["GET"])
        def mgmt_configureddevices():
            return jsonify(
                {
                    "Value": [
                        {
                            "DeviceName": "ARGUS Smart Dome",
                            "DeviceType": "Dome",
                            "DeviceNumber": 0,
                            "UniqueID": "argus-dome-001",
                        }
                    ]
                }
            )

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the Alpaca server in a background daemon thread."""
        self._thread = threading.Thread(
            target=self._run_server, name="AlpacaServer", daemon=True
        )
        self._thread.start()
        logger.info(
            "Alpaca server started on %s:%d", self._host, self._port
        )

    def _run_server(self) -> None:
        self._app.run(
            host=self._host, port=self._port, threaded=True, use_reloader=False
        )

    def shutdown(self) -> None:
        """Request the server to stop (best-effort for daemon thread)."""
        logger.info("Alpaca server shutdown requested")
