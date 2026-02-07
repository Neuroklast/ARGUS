"""Lightweight internationalisation module for ARGUS.

Thread-safe, dictionary-based i18n that ships English and German
translations for every UI string used by the application.

Usage::

    from localization import t, set_language, get_language

    set_language("de")
    print(t("splash.title"))        # "ARGUS"
    print(t("splash.subtitle"))     # "Erweiterte Rotationsführung mittels Sensorik"
"""

from __future__ import annotations

import threading
from typing import Dict

# ---------------------------------------------------------------------------
# Internal state (thread-safe)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_current_language: str = "en"

# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------
_translations: Dict[str, Dict[str, str]] = {
    "en": {
        # ── Splash screen ────────────────────────────────────────────
        "splash.title":                     "ARGUS",
        "splash.subtitle":                  "Advanced Rotation Guidance Using Sensors",
        "splash.starting":                  "Starting up \u2026",
        "splash.loading_config":            "Loading configuration \u2026",
        "splash.building_ui":               "Building user interface \u2026",
        "splash.connecting_hw":             "Connecting hardware \u2026",
        "splash.init_ascom":                "Initializing ASCOM telescope \u2026",
        "splash.init_serial":               "Initializing serial controller \u2026",
        "splash.init_vision":               "Initializing vision system \u2026",
        "splash.init_math":                 "Initializing math engine \u2026",
        "splash.init_voice":                "Initializing voice assistant \u2026",
        "splash.start_alpaca":              "Starting Alpaca server \u2026",
        "splash.start_loop":                "Starting control loop \u2026",
        "splash.ready":                     "Ready",
        "splash.init_failed":               "\u26a0 Initialisation failed \u2013 see log",

        # ── GUI labels ───────────────────────────────────────────────
        "gui.telemetry":                    "TELEMETRY",
        "gui.mount_az":                     "MOUNT AZ",
        "gui.dome_az":                      "DOME AZ",
        "gui.error":                        "ERROR",
        "gui.dome_position":                "DOME POSITION",
        "gui.connection_status":            "CONNECTION STATUS",
        "gui.telescope":                    "TELESCOPE",
        "gui.camera":                       "CAMERA",
        "gui.motor":                        "MOTOR",
        "gui.not_connected":                "Not connected",
        "gui.dome_control":                 "DOME CONTROL",
        "gui.operating_mode":               "OPERATING MODE",
        "gui.manual":                       "MANUAL",
        "gui.auto_slave":                   "AUTO-SLAVE",
        "gui.calibrate":                    "CALIBRATE",
        "gui.tools":                        "TOOLS",
        "gui.system_log":                   "SYSTEM LOG",
        "gui.no_hw_banner":                 "\u26a0 No hardware connected \u2013 running in simulation mode",
        "gui.rotate_ccw":                   "Rotate CCW (Counter-Clockwise)",
        "gui.rotate_cw":                    "Rotate CW (Clockwise)",
        "gui.emergency_stop":               "EMERGENCY STOP",
        "gui.open_settings":                "Open Settings",
        "gui.run_diagnostics":              "Run System Diagnostics",
        "gui.toggle_night":                 "Toggle Night Mode (red / preserve night vision)",
        "gui.no_camera_signal":             "NO CAMERA SIGNAL",
        "gui.camera_hint":                  "Connect USB camera or configure index in Settings",
        "gui.tracking":                     "TRACKING",
        "gui.no_markers":                   "NO MARKERS DETECTED",
        "gui.diagnostics_title":            "System Diagnostics",
        "gui.diagnostics_running":          "Running diagnostics \u2026",
        "gui.close":                        "Close",
        "gui.connected":                    "Connected",
        "gui.reconnecting":                 "Reconnecting\u2026",
        "gui.no_camera_found":              "No camera found",

        # ── Settings ─────────────────────────────────────────────────
        "settings.window_title":            "ARGUS \u2013 Settings",
        "settings.hardware":                "Hardware",
        "settings.vision":                  "Vision",
        "settings.ascom":                   "ASCOM",
        "settings.location":                "Location",
        "settings.geometry":                "Geometry",
        "settings.control":                 "Control",
        "settings.safety":                  "Safety",
        "settings.serial_port":             "Serial Port",
        "settings.baud_rate":               "Baud Rate",
        "settings.motor_type":              "Motor Type",
        "settings.comm_protocol":           "Communication Protocol",
        "settings.steps_per_degree":        "Steps per Degree (Stepper)",
        "settings.ticks_per_degree":        "Ticks per Degree (Encoder)",
        "settings.degrees_per_second":      "Degrees per Second (Timed)",
        "settings.encoder_tolerance":       "Encoder Tolerance (\u00b0)",
        "settings.homing_switch":           "Homing Switch Installed",
        "settings.home_switch_az":          "Home Switch Azimuth (\u00b0)",
        "settings.homing_direction":        "Homing Search Direction",
        "settings.camera_index":            "Camera Index",
        "settings.marker_size":             "Marker Size (m)",
        "settings.resolution_width":        "Resolution Width",
        "settings.resolution_height":       "Resolution Height",
        "settings.aruco_dict":              "ArUco Dictionary",
        "settings.telescope_progid":        "Telescope ProgID",
        "settings.latitude":                "Latitude (\u00b0)",
        "settings.longitude":               "Longitude (\u00b0)",
        "settings.elevation":               "Elevation (m)",
        "settings.dome_radius":             "Dome Radius (m)",
        "settings.slit_width":              "Slit Width (m)",
        "settings.pier_height":             "Pier Height (m)",
        "settings.gem_offset_east":         "GEM Offset East (m)",
        "settings.gem_offset_north":        "GEM Offset North (m)",
        "settings.drift_correction":        "Drift Correction Enabled",
        "settings.correction_threshold":    "Correction Threshold (\u00b0)",
        "settings.max_speed":               "Max Speed",
        "settings.update_rate":             "Update Rate (Hz)",
        "settings.telescope_protrudes":     "Telescope Protrudes",
        "settings.safe_altitude":           "Safe Altitude (\u00b0)",
        "settings.max_nudge":               "Max Nudge (\u00b0)",
        "settings.cancel":                  "CANCEL",
        "settings.save":                    "SAVE",

        # ── Settings – dropdown / enum values ────────────────────────
        "settings.motor_stepper":           "Stepper Motor",
        "settings.motor_dc_encoder":        "DC Motor with Encoder",
        "settings.motor_timed":             "Time-based (Relay)",
        "settings.proto_native":            "ARGUS Native",
        "settings.proto_lesvdome":          "LesveDome Standard",
        "settings.proto_relay":             "Relay Control",
        "settings.dir_cw":                  "Clockwise",
        "settings.dir_ccw":                 "Counter-Clockwise",

        # ── Settings – group headers ─────────────────────────────────
        "settings.group.connection":        "Connection",
        "settings.group.motor_config":      "Motor Configuration",
        "settings.group.drive_cal":         "Drive Calibration",
        "settings.group.homing":            "Homing",
        "settings.group.camera":            "Camera",
        "settings.group.aruco":             "ArUco Marker",
        "settings.group.telescope":         "Telescope",
        "settings.group.obs_position":      "Observatory Position",
        "settings.group.dome_dims":         "Dome Dimensions",
        "settings.group.mount_offsets":     "Mount Offsets",
        "settings.group.drift":             "Drift Correction",
        "settings.group.speed_timing":      "Speed & Timing",
        "settings.group.collision":         "Collision Avoidance",
        "settings.group.slew_limits":       "Slew Limits",

        # ── Camera overlay ───────────────────────────────────────────
        "overlay.mount_az":                 "MOUNT AZ",
        "overlay.dome_az":                  "DOME AZ",
        "overlay.error":                    "ERROR",
        "overlay.drift":                    "DRIFT",
        "overlay.status":                   "STATUS",
        "overlay.tracking":                 "TRACKING",
        "overlay.no_signal":                "NO SIGNAL",
        "overlay.markers":                  "MARKERS",

        # ── Connection banner ────────────────────────────────────────
        "banner.missing":                   "\u26a0 {missing} not connected \u2013 limited functionality",
        "banner.telescope":                 "Telescope",
        "banner.camera":                    "Camera",
        "banner.motor":                     "Motor",
    },

    "de": {
        # ── Splash-Bildschirm ────────────────────────────────────────
        "splash.title":                     "ARGUS",
        "splash.subtitle":                  "Erweiterte Rotationsf\u00fchrung mittels Sensorik",
        "splash.starting":                  "Starte \u2026",
        "splash.loading_config":            "Konfiguration wird geladen \u2026",
        "splash.building_ui":               "Benutzeroberfl\u00e4che wird aufgebaut \u2026",
        "splash.connecting_hw":             "Hardware wird verbunden \u2026",
        "splash.init_ascom":                "ASCOM-Teleskop wird initialisiert \u2026",
        "splash.init_serial":               "Serieller Controller wird initialisiert \u2026",
        "splash.init_vision":               "Bildverarbeitung wird initialisiert \u2026",
        "splash.init_math":                 "Mathematik-Engine wird initialisiert \u2026",
        "splash.init_voice":                "Sprachassistent wird initialisiert \u2026",
        "splash.start_alpaca":              "Alpaca-Server wird gestartet \u2026",
        "splash.start_loop":                "Regelschleife wird gestartet \u2026",
        "splash.ready":                     "Bereit",
        "splash.init_failed":               "\u26a0 Initialisierung fehlgeschlagen \u2013 siehe Protokoll",

        # ── GUI-Beschriftungen ───────────────────────────────────────
        "gui.telemetry":                    "TELEMETRIE",
        "gui.mount_az":                     "MONTIERUNG AZ",
        "gui.dome_az":                      "KUPPEL AZ",
        "gui.error":                        "FEHLER",
        "gui.dome_position":                "KUPPELPOSITION",
        "gui.connection_status":            "VERBINDUNGSSTATUS",
        "gui.telescope":                    "TELESKOP",
        "gui.camera":                       "KAMERA",
        "gui.motor":                        "MOTOR",
        "gui.not_connected":                "Nicht verbunden",
        "gui.dome_control":                 "KUPPELSTEUERUNG",
        "gui.operating_mode":               "BETRIEBSMODUS",
        "gui.manual":                       "MANUELL",
        "gui.auto_slave":                   "AUTOMATIK",
        "gui.calibrate":                    "KALIBRIEREN",
        "gui.tools":                        "WERKZEUGE",
        "gui.system_log":                   "SYSTEMPROTOKOLL",
        "gui.no_hw_banner":                 "\u26a0 Keine Hardware verbunden \u2013 Simulationsmodus aktiv",
        "gui.rotate_ccw":                   "Gegen den Uhrzeigersinn drehen",
        "gui.rotate_cw":                    "Im Uhrzeigersinn drehen",
        "gui.emergency_stop":               "NOT-HALT",
        "gui.open_settings":                "Einstellungen \u00f6ffnen",
        "gui.run_diagnostics":              "Systemdiagnose starten",
        "gui.toggle_night":                 "Nachtmodus umschalten (rot / Nachtsicht erhalten)",
        "gui.no_camera_signal":             "KEIN KAMERASIGNAL",
        "gui.camera_hint":                  "USB-Kamera anschlie\u00dfen oder Index in den Einstellungen konfigurieren",
        "gui.tracking":                     "NACHF\u00dcHRUNG",
        "gui.no_markers":                   "KEINE MARKER ERKANNT",
        "gui.diagnostics_title":            "Systemdiagnose",
        "gui.diagnostics_running":          "Diagnose l\u00e4uft \u2026",
        "gui.close":                        "Schlie\u00dfen",
        "gui.connected":                    "Verbunden",
        "gui.reconnecting":                 "Verbindung wird hergestellt\u2026",
        "gui.no_camera_found":              "Keine Kamera gefunden",

        # ── Einstellungen ────────────────────────────────────────────
        "settings.window_title":            "ARGUS \u2013 Einstellungen",
        "settings.hardware":                "Hardware",
        "settings.vision":                  "Bildverarbeitung",
        "settings.ascom":                   "ASCOM",
        "settings.location":                "Standort",
        "settings.geometry":                "Geometrie",
        "settings.control":                 "Steuerung",
        "settings.safety":                  "Sicherheit",
        "settings.serial_port":             "Serieller Anschluss",
        "settings.baud_rate":               "Baudrate",
        "settings.motor_type":              "Motortyp",
        "settings.comm_protocol":           "Kommunikationsprotokoll",
        "settings.steps_per_degree":        "Schritte pro Grad (Schrittmotor)",
        "settings.ticks_per_degree":        "Impulse pro Grad (Drehgeber)",
        "settings.degrees_per_second":      "Grad pro Sekunde (zeitgesteuert)",
        "settings.encoder_tolerance":       "Drehgeber-Toleranz (\u00b0)",
        "settings.homing_switch":           "Referenzschalter vorhanden",
        "settings.home_switch_az":          "Referenzschalter-Azimut (\u00b0)",
        "settings.homing_direction":        "Referenzfahrt-Suchrichtung",
        "settings.camera_index":            "Kamera-Index",
        "settings.marker_size":             "Markergr\u00f6\u00dfe (m)",
        "settings.resolution_width":        "Aufl\u00f6sung Breite",
        "settings.resolution_height":       "Aufl\u00f6sung H\u00f6he",
        "settings.aruco_dict":              "ArUco-W\u00f6rterbuch",
        "settings.telescope_progid":        "Teleskop-ProgID",
        "settings.latitude":                "Breitengrad (\u00b0)",
        "settings.longitude":               "L\u00e4ngengrad (\u00b0)",
        "settings.elevation":               "H\u00f6he (m)",
        "settings.dome_radius":             "Kuppelradius (m)",
        "settings.slit_width":              "Spaltbreite (m)",
        "settings.pier_height":             "S\u00e4ulenh\u00f6he (m)",
        "settings.gem_offset_east":         "GEM-Versatz Ost (m)",
        "settings.gem_offset_north":        "GEM-Versatz Nord (m)",
        "settings.drift_correction":        "Driftkorrektur aktiviert",
        "settings.correction_threshold":    "Korrekturschwelle (\u00b0)",
        "settings.max_speed":               "Maximalgeschwindigkeit",
        "settings.update_rate":             "Aktualisierungsrate (Hz)",
        "settings.telescope_protrudes":     "Teleskop ragt hervor",
        "settings.safe_altitude":           "Sichere H\u00f6he (\u00b0)",
        "settings.max_nudge":               "Maximaler Korrekturschritt (\u00b0)",
        "settings.cancel":                  "ABBRECHEN",
        "settings.save":                    "SPEICHERN",

        # ── Einstellungen – Dropdown-/Aufz\u00e4hlungswerte ──────────────
        "settings.motor_stepper":           "Schrittmotor",
        "settings.motor_dc_encoder":        "Gleichstrommotor mit Drehgeber",
        "settings.motor_timed":             "Zeitgesteuert (Relais)",
        "settings.proto_native":            "ARGUS Nativ",
        "settings.proto_lesvdome":          "LesveDome Standard",
        "settings.proto_relay":             "Relaissteuerung",
        "settings.dir_cw":                  "Im Uhrzeigersinn",
        "settings.dir_ccw":                 "Gegen den Uhrzeigersinn",

        # ── Einstellungen – Gruppenüberschriften ─────────────────────
        "settings.group.connection":        "Verbindung",
        "settings.group.motor_config":      "Motorkonfiguration",
        "settings.group.drive_cal":         "Antriebskalibrierung",
        "settings.group.homing":            "Referenzfahrt",
        "settings.group.camera":            "Kamera",
        "settings.group.aruco":             "ArUco-Marker",
        "settings.group.telescope":         "Teleskop",
        "settings.group.obs_position":      "Observatoriumsstandort",
        "settings.group.dome_dims":         "Kuppelabmessungen",
        "settings.group.mount_offsets":     "Montierungsversatz",
        "settings.group.drift":             "Driftkorrektur",
        "settings.group.speed_timing":      "Geschwindigkeit & Taktung",
        "settings.group.collision":         "Kollisionsvermeidung",
        "settings.group.slew_limits":       "Schwenkgrenzen",

        # ── Kamera-Overlay ───────────────────────────────────────────
        "overlay.mount_az":                 "MONTIERUNG AZ",
        "overlay.dome_az":                  "KUPPEL AZ",
        "overlay.error":                    "FEHLER",
        "overlay.drift":                    "DRIFT",
        "overlay.status":                   "STATUS",
        "overlay.tracking":                 "NACHF\u00dcHRUNG",
        "overlay.no_signal":                "KEIN SIGNAL",
        "overlay.markers":                  "MARKER",

        # ── Verbindungsbanner ────────────────────────────────────────
        "banner.missing":                   "\u26a0 {missing} nicht verbunden \u2013 eingeschr\u00e4nkte Funktionalit\u00e4t",
        "banner.telescope":                 "Teleskop",
        "banner.camera":                    "Kamera",
        "banner.motor":                     "Motor",
    },
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_language(lang: str) -> None:
    """Set the active language (e.g. ``"en"`` or ``"de"``)."""
    if lang not in _translations:
        raise ValueError(
            f"Unsupported language '{lang}'. "
            f"Available: {', '.join(sorted(_translations))}"
        )
    global _current_language
    with _lock:
        _current_language = lang


def get_language() -> str:
    """Return the currently active language code."""
    with _lock:
        return _current_language


def t(key: str) -> str:
    """Return the translated string for *key* in the current language.

    If the key is missing from the active language table the English
    fallback is tried.  If the key is not found at all the raw *key*
    string is returned so that missing translations are obvious in the UI
    without crashing the application.
    """
    with _lock:
        lang = _current_language

    table = _translations.get(lang, {})
    if key in table:
        return table[key]

    # Fallback to English
    en_table = _translations.get("en", {})
    if key in en_table:
        return en_table[key]

    return key
