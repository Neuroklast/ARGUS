"""
ARGUS - Advanced Rotation Guidance Using Sensors
INDI Dome Server

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Exposes the ARGUS dome controller as an INDI device so that
Linux-based observatory software (KStars/Ekos, INDI clients on
StellarMate, Astroberry, …) can control the dome natively.

The server listens for XML-based INDI protocol messages on a TCP
socket (default port 7624) and translates them into
``ArgusController`` calls.

Supported INDI properties
--------------------------
* **ABS_DOME_POSITION** (Number) – read/write absolute dome azimuth.
* **DOME_SHUTTER** (Switch) – open / close the shutter.
* **DOME_PARK** (Switch) – park / unpark the dome.
* **CONNECTION** (Switch) – connect / disconnect the driver.
"""

import itertools
import logging
import socket
import threading
import xml.etree.ElementTree as ET
from typing import Optional

logger = logging.getLogger(__name__)

# Default INDI server port
INDI_DEFAULT_PORT = 7624
DEVICE_NAME = "ARGUS Dome"


class INDIDomeServer:
    """Minimal INDI server that exposes dome control properties.

    Args:
        controller: Reference to the running ``ArgusController``.
        host: Network interface to listen on (default ``0.0.0.0``).
        port: TCP port (default ``7624`` – INDI standard).
    """

    def __init__(self, controller, host: str = "0.0.0.0", port: int = INDI_DEFAULT_PORT):
        self._controller = controller
        self._host = host
        self._port = port
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # INDI XML helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _number_vector(name: str, state: str, values: dict[str, float]) -> str:
        """Build an INDI ``defNumberVector`` or ``setNumberVector`` XML."""
        elements = ""
        for ename, val in values.items():
            elements += (
                f'  <defNumber name="{ename}" label="{ename}" '
                f'format="%g" min="0" max="360" step="0.1">{val}</defNumber>\n'
            )
        return (
            f'<defNumberVector device="{DEVICE_NAME}" name="{name}" '
            f'label="{name}" group="Main Control" state="{state}" '
            f'perm="rw" timeout="60">\n{elements}</defNumberVector>\n'
        )

    @staticmethod
    def _switch_vector(name: str, state: str, switches: dict[str, str]) -> str:
        """Build an INDI ``defSwitchVector`` XML."""
        elements = ""
        for sname, sstate in switches.items():
            elements += (
                f'  <defSwitch name="{sname}" label="{sname}">{sstate}</defSwitch>\n'
            )
        return (
            f'<defSwitchVector device="{DEVICE_NAME}" name="{name}" '
            f'label="{name}" group="Main Control" state="{state}" '
            f'perm="rw" rule="OneOfMany" timeout="60">\n{elements}'
            f'</defSwitchVector>\n'
        )

    @staticmethod
    def _set_number(name: str, state: str, values: dict[str, float]) -> str:
        """Build an INDI ``setNumberVector`` XML for property updates."""
        elements = ""
        for ename, val in values.items():
            elements += f'  <oneNumber name="{ename}">{val}</oneNumber>\n'
        return (
            f'<setNumberVector device="{DEVICE_NAME}" name="{name}" '
            f'state="{state}">\n{elements}</setNumberVector>\n'
        )

    @staticmethod
    def _set_switch(name: str, state: str, switches: dict[str, str]) -> str:
        """Build an INDI ``setSwitchVector`` XML for property updates."""
        elements = ""
        for sname, sstate in switches.items():
            elements += f'  <oneSwitch name="{sname}">{sstate}</oneSwitch>\n'
        return (
            f'<setSwitchVector device="{DEVICE_NAME}" name="{name}" '
            f'state="{state}">\n{elements}</setSwitchVector>\n'
        )

    # ------------------------------------------------------------------
    # Property definitions sent on <getProperties>
    # ------------------------------------------------------------------
    def _build_definition_xml(self) -> str:
        """Return all property definition messages for the device."""
        az = getattr(self._controller, "current_azimuth", 0.0)
        is_parked = getattr(self._controller, "is_parked", False)

        xml = ""
        # CONNECTION
        xml += self._switch_vector(
            "CONNECTION", "Ok",
            {"CONNECT": "On", "DISCONNECT": "Off"},
        )
        # ABS_DOME_POSITION
        xml += self._number_vector(
            "ABS_DOME_POSITION", "Ok",
            {"DOME_ABSOLUTE_POSITION": az},
        )
        # DOME_SHUTTER
        xml += self._switch_vector(
            "DOME_SHUTTER", "Ok",
            {"SHUTTER_OPEN": "Off", "SHUTTER_CLOSE": "Off"},
        )
        # DOME_PARK
        xml += self._switch_vector(
            "DOME_PARK", "Ok",
            {"PARK": "On" if is_parked else "Off",
             "UNPARK": "Off" if is_parked else "On"},
        )
        return xml

    # ------------------------------------------------------------------
    # Incoming message handler
    # ------------------------------------------------------------------
    def _handle_message(self, xml_str: str, client: socket.socket) -> None:
        """Parse and handle a single INDI XML message."""
        try:
            root = ET.fromstring(f"<root>{xml_str}</root>")
        except ET.ParseError:
            logger.debug("INDI: Could not parse XML: %s", xml_str[:200])
            return

        for elem in root:
            tag = elem.tag
            device = elem.get("device", "")
            name = elem.get("name", "")

            if tag == "getProperties":
                response = self._build_definition_xml()
                self._send_to_client(client, response)

            elif device != DEVICE_NAME:
                continue

            elif tag == "newNumberVector" and name == "ABS_DOME_POSITION":
                for child in elem:
                    if child.get("name") == "DOME_ABSOLUTE_POSITION":
                        try:
                            target = float(child.text or "0")
                        except ValueError:
                            continue
                        if hasattr(self._controller, "move_dome"):
                            self._controller.move_dome(target)
                        reply = self._set_number(
                            "ABS_DOME_POSITION", "Ok",
                            {"DOME_ABSOLUTE_POSITION": target},
                        )
                        self._broadcast(reply)

            elif tag == "newSwitchVector" and name == "DOME_SHUTTER":
                for child in elem:
                    sname = child.get("name", "")
                    if sname == "SHUTTER_OPEN":
                        logger.info("INDI: Shutter open requested")
                    elif sname == "SHUTTER_CLOSE":
                        logger.info("INDI: Shutter close requested")
                reply = self._set_switch(
                    "DOME_SHUTTER", "Ok",
                    {"SHUTTER_OPEN": "Off", "SHUTTER_CLOSE": "Off"},
                )
                self._broadcast(reply)

            elif tag == "newSwitchVector" and name == "DOME_PARK":
                for child in elem:
                    sname = child.get("name", "")
                    if sname == "PARK" and hasattr(self._controller, "park_dome"):
                        self._controller.park_dome()
                        logger.info("INDI: Park requested")
                reply = self._set_switch(
                    "DOME_PARK", "Ok",
                    {"PARK": "On", "UNPARK": "Off"},
                )
                self._broadcast(reply)

    # ------------------------------------------------------------------
    # Networking
    # ------------------------------------------------------------------
    def _send_to_client(self, client: socket.socket, data: str) -> None:
        try:
            client.sendall(data.encode("utf-8"))
        except OSError:
            self._remove_client(client)

    def _broadcast(self, data: str) -> None:
        with self._lock:
            for c in list(self._clients):
                try:
                    c.sendall(data.encode("utf-8"))
                except OSError:
                    self._remove_client(c)

    def _remove_client(self, client: socket.socket) -> None:
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)
        try:
            client.close()
        except OSError:
            pass

    def _handle_client(self, client: socket.socket, addr) -> None:
        """Read INDI XML from a connected client until disconnect."""
        logger.info("INDI client connected from %s", addr)
        with self._lock:
            self._clients.append(client)
        buf = ""
        try:
            while self._running:
                data = client.recv(4096)
                if not data:
                    break
                buf += data.decode("utf-8", errors="replace")
                # Simple framing: process complete XML tags
                while buf:
                    # Find the end of the first top-level element
                    end = -1
                    for closing in ("</getProperties>", "</newNumberVector>",
                                    "</newSwitchVector>", "</newTextVector>"):
                        idx = buf.find(closing)
                        if idx >= 0:
                            end = idx + len(closing)
                            break
                    if end < 0:
                        break
                    msg = buf[:end]
                    buf = buf[end:]
                    self._handle_message(msg, client)
        except OSError:
            pass
        finally:
            self._remove_client(client)
            logger.info("INDI client disconnected: %s", addr)

    def _run_server(self) -> None:
        """Main accept loop for the INDI TCP server."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.settimeout(2.0)
        srv.bind((self._host, self._port))
        srv.listen(5)
        logger.info("INDI server listening on %s:%d", self._host, self._port)

        while self._running:
            try:
                client, addr = srv.accept()
                t = threading.Thread(
                    target=self._handle_client, args=(client, addr),
                    daemon=True,
                )
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

        srv.close()
        logger.info("INDI server stopped")

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the INDI server in a background daemon thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run_server, name="INDIServer", daemon=True,
        )
        self._thread.start()
        logger.info("INDI server started on %s:%d", self._host, self._port)

    def shutdown(self) -> None:
        """Request the INDI server to stop."""
        self._running = False
        # Close all client connections
        with self._lock:
            for c in list(self._clients):
                try:
                    c.close()
                except OSError:
                    pass
            self._clients.clear()
        logger.info("INDI server shutdown requested")
