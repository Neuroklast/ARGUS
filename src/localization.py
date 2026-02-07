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
        "gui.slit":                         "SLIT",
        "gui.slit_open":                    "Open",
        "gui.slit_closed":                  "Closed",
        "gui.mount_alt":                    "MOUNT ALT",
        "gui.sidereal_time":                "LST",
        "gui.tracking_rate":                "TRACK RATE",
        "gui.pier_side":                    "PIER SIDE",
        "gui.simulation":                   "SIMULATION",
        "gui.sim_telescope_az":             "Tel AZ",
        "gui.sim_telescope_alt":            "Tel ALT",
        "gui.open_slit":                    "Open Slit",
        "gui.close_slit":                   "Close Slit",

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

        # ── Help dialog ─────────────────────────────────────────────
        "gui.help_tooltip":                 "Help",
        "gui.setup_wizard":                 "Setup Wizard",
        "help.title":                       "ARGUS \u2013 Help",
        "help.quick_start_title":           "Quick Start",
        "help.quick_start_body":            "1. Connect your telescope mount, dome motor controller, and camera via USB.\n2. Use Settings (\u2699) to configure serial port, telescope driver, and dome geometry.\n3. Switch to AUTO-SLAVE mode for automatic dome tracking.\n4. Run Diagnostics to verify all connections.",
        "help.modes_title":                 "Operating Modes",
        "help.modes_body":                  "\u2022 MANUAL \u2013 Control the dome with the CCW/CW buttons.\n\u2022 AUTO-SLAVE \u2013 Dome follows the telescope automatically.\n\u2022 CALIBRATE \u2013 Collects data points for offset calibration.",
        "help.troubleshooting_title":       "Troubleshooting",
        "help.troubleshooting_body":        "\u2022 No serial port? Check USB cable and drivers.\n\u2022 Telescope not found? Verify ASCOM driver and ProgID.\n\u2022 Camera black? Try a different camera index in Settings.\n\u2022 Run Diagnostics for detailed system checks.",

        # ── Setup wizard ─────────────────────────────────────────────
        "wizard.title":                     "ARGUS \u2013 Setup Wizard",
        "wizard.next":                      "Next \u25b6",
        "wizard.back":                      "\u25c0 Back",
        "wizard.finish":                    "Finish \u2713",
        "wizard.step_location_title":       "Step 1: Observatory Location",
        "wizard.step_location_help":        "Enter your observatory\u2019s geographic coordinates. These are used to compute accurate dome positions based on the telescope\u2019s celestial pointing direction. You can find your coordinates using Google Maps or a GPS device.",
        "wizard.step_hardware_title":       "Step 2: Hardware Connection",
        "wizard.step_hardware_help":        "Configure the serial port and baud rate for communication with your dome motor controller (Arduino). Common values are COM3 (Windows) or /dev/ttyUSB0 (Linux) at 9600 baud.",
        "wizard.step_dome_title":           "Step 3: Dome Geometry & Limits",
        "wizard.step_dome_help":            "Set the physical dimensions of your dome and optional rotation limits. If cables are attached to the dome that could tear, set azimuth limits to restrict the rotation range.",
        "wizard.step_finish_title":         "Setup Complete",
        "wizard.step_finish_help":          "Your basic configuration is ready. You can fine-tune additional settings (ASCOM, vision, safety) via the Settings panel (\u2699) at any time. Run Diagnostics to verify everything works.",

        # ── Dome rotation limits ─────────────────────────────────────
        "settings.az_min":                  "Min Azimuth Limit (\u00b0)",
        "settings.az_max":                  "Max Azimuth Limit (\u00b0)",
        "settings.group.rotation_limits":   "Rotation Limits",

        # ── Diagnostics tips ─────────────────────────────────────────
        "diag.tips_title":                  "\U0001f527 Troubleshooting Tips",
        "diag.tips_body":                   "\u2022 Check that all USB cables are securely connected.\n\u2022 Restart ARGUS after changing hardware connections.\n\u2022 Verify that no other program is using the same serial port.\n\u2022 On Windows, check Device Manager for COM port assignments.\n\u2022 Use the Setup Wizard to reconfigure basic settings.",
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
        "gui.slit":                         "SPALT",
        "gui.slit_open":                    "Offen",
        "gui.slit_closed":                  "Geschlossen",
        "gui.mount_alt":                    "MONTIERUNG ALT",
        "gui.sidereal_time":                "LST",
        "gui.tracking_rate":                "NACHF\u00dcHRRATE",
        "gui.pier_side":                    "S\u00c4ULENSEITE",
        "gui.simulation":                   "SIMULATION",
        "gui.sim_telescope_az":             "Tel AZ",
        "gui.sim_telescope_alt":            "Tel ALT",
        "gui.open_slit":                    "Spalt \u00f6ffnen",
        "gui.close_slit":                   "Spalt schlie\u00dfen",

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

        # ── Hilfedialog ─────────────────────────────────────────────
        "gui.help_tooltip":                 "Hilfe",
        "gui.setup_wizard":                 "Einrichtungsassistent",
        "help.title":                       "ARGUS \u2013 Hilfe",
        "help.quick_start_title":           "Schnellstart",
        "help.quick_start_body":            "1. Verbinden Sie Teleskopmontierung, Kuppelmotor und Kamera per USB.\n2. Konfigurieren Sie in den Einstellungen (\u2699) den seriellen Anschluss, den Teleskoptreiber und die Kuppelgeometrie.\n3. Wechseln Sie in den AUTOMATIK-Modus f\u00fcr automatische Kuppelnachf\u00fchrung.\n4. F\u00fchren Sie die Diagnose aus, um alle Verbindungen zu pr\u00fcfen.",
        "help.modes_title":                 "Betriebsmodi",
        "help.modes_body":                  "\u2022 MANUELL \u2013 Steuern Sie die Kuppel mit den CCW/CW-Tasten.\n\u2022 AUTOMATIK \u2013 Die Kuppel folgt dem Teleskop automatisch.\n\u2022 KALIBRIEREN \u2013 Sammelt Datenpunkte f\u00fcr die Offset-Kalibrierung.",
        "help.troubleshooting_title":       "Fehlerbehebung",
        "help.troubleshooting_body":        "\u2022 Kein serieller Anschluss? USB-Kabel und Treiber pr\u00fcfen.\n\u2022 Teleskop nicht gefunden? ASCOM-Treiber und ProgID \u00fcberpr\u00fcfen.\n\u2022 Kamera schwarz? Anderen Kamera-Index in den Einstellungen versuchen.\n\u2022 Diagnose f\u00fcr detaillierte Systempr\u00fcfungen ausf\u00fchren.",

        # ── Einrichtungsassistent ─────────────────────────────────────
        "wizard.title":                     "ARGUS \u2013 Einrichtungsassistent",
        "wizard.next":                      "Weiter \u25b6",
        "wizard.back":                      "\u25c0 Zur\u00fcck",
        "wizard.finish":                    "Fertig \u2713",
        "wizard.step_location_title":       "Schritt 1: Observatoriumsstandort",
        "wizard.step_location_help":        "Geben Sie die geografischen Koordinaten Ihres Observatoriums ein. Diese werden verwendet, um genaue Kuppelpositionen basierend auf der Himmelsausrichtung des Teleskops zu berechnen. Sie finden Ihre Koordinaten z.\u00a0B. \u00fcber Google Maps oder ein GPS-Ger\u00e4t.",
        "wizard.step_hardware_title":       "Schritt 2: Hardware-Verbindung",
        "wizard.step_hardware_help":        "Konfigurieren Sie den seriellen Anschluss und die Baudrate f\u00fcr die Kommunikation mit dem Kuppelmotor-Controller (Arduino). \u00dcbliche Werte sind COM3 (Windows) oder /dev/ttyUSB0 (Linux) bei 9600 Baud.",
        "wizard.step_dome_title":           "Schritt 3: Kuppelgeometrie & Grenzen",
        "wizard.step_dome_help":            "Geben Sie die physischen Ma\u00dfe Ihrer Kuppel und optionale Drehgrenzen ein. Falls Kabel an der Kuppel befestigt sind, die abreißen k\u00f6nnten, legen Sie Azimutgrenzen fest, um den Drehbereich einzuschr\u00e4nken.",
        "wizard.step_finish_title":         "Einrichtung abgeschlossen",
        "wizard.step_finish_help":          "Ihre Grundkonfiguration ist fertig. Weitere Einstellungen (ASCOM, Bildverarbeitung, Sicherheit) k\u00f6nnen Sie jederzeit \u00fcber das Einstellungsmen\u00fc (\u2699) anpassen. F\u00fchren Sie die Diagnose aus, um alles zu \u00fcberpr\u00fcfen.",

        # ── Kuppeldrehgrenzen ─────────────────────────────────────────
        "settings.az_min":                  "Min. Azimutgrenze (\u00b0)",
        "settings.az_max":                  "Max. Azimutgrenze (\u00b0)",
        "settings.group.rotation_limits":   "Drehgrenzen",

        # ── Diagnosetipps ─────────────────────────────────────────────
        "diag.tips_title":                  "\U0001f527 Tipps zur Fehlerbehebung",
        "diag.tips_body":                   "\u2022 Pr\u00fcfen Sie, dass alle USB-Kabel fest angeschlossen sind.\n\u2022 Starten Sie ARGUS nach \u00c4nderungen an der Hardware neu.\n\u2022 Stellen Sie sicher, dass kein anderes Programm denselben seriellen Anschluss verwendet.\n\u2022 Unter Windows pr\u00fcfen Sie den Ger\u00e4te-Manager f\u00fcr COM-Port-Zuweisungen.\n\u2022 Verwenden Sie den Einrichtungsassistenten, um Grundeinstellungen neu zu konfigurieren.",
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
