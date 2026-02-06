"""
ARGUS - Advanced Rotation Guidance Using Sensors
Settings GUI Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides a CTkToplevel settings window for editing config.yaml
without manual file editing.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
import customtkinter as ctk

from path_utils import get_base_path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = get_base_path() / "config.yaml"

# ArUco dictionary options for the dropdown
ARUCO_DICTIONARIES = [
    "DICT_4X4_50", "DICT_4X4_100", "DICT_4X4_250", "DICT_4X4_1000",
    "DICT_5X5_50", "DICT_5X5_100", "DICT_5X5_250", "DICT_5X5_1000",
    "DICT_6X6_50", "DICT_6X6_100", "DICT_6X6_250", "DICT_6X6_1000",
    "DICT_7X7_50", "DICT_7X7_100", "DICT_7X7_250", "DICT_7X7_1000",
]


class SettingsWindow(ctk.CTkToplevel):
    """Settings window for editing ARGUS configuration."""

    def __init__(self, parent, config_path: Optional[str] = None):
        super().__init__(parent)

        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()

        # -- Window setup ------------------------------------------------
        self.title("ARGUS – Settings")
        self.geometry("520x560")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # -- Build UI ----------------------------------------------------
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))

        self._build_hardware_tab()
        self._build_vision_tab()
        self._build_ascom_tab()
        self._build_location_tab()
        self._build_geometry_tab()
        self._build_control_tab()
        self._build_safety_tab()

        # -- Save button -------------------------------------------------
        self.btn_save = ctk.CTkButton(
            self, text="SAVE", command=self._on_save
        )
        self.btn_save.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))

    # ---- Config I/O ----------------------------------------------------
    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, "r") as fh:
                config = yaml.safe_load(fh)
            return config or {}
        except (FileNotFoundError, yaml.YAMLError) as exc:
            logger.warning("Could not load config: %s – using empty dict", exc)
            return {}

    # ---- Tab builders --------------------------------------------------
    def _build_hardware_tab(self):
        """Hardware tab: serial_port and baud_rate."""
        tab = self.tabview.add("Hardware")
        tab.grid_columnconfigure(1, weight=1)

        hw = self.config.get("hardware", {})

        ctk.CTkLabel(tab, text="Serial Port:").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_serial_port = ctk.CTkEntry(tab)
        self.entry_serial_port.insert(0, str(hw.get("serial_port", "COM3")))
        self.entry_serial_port.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Baud Rate:").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_baud_rate = ctk.CTkEntry(tab)
        self.entry_baud_rate.insert(0, str(hw.get("baud_rate", 9600)))
        self.entry_baud_rate.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

    def _build_vision_tab(self):
        """Vision tab: camera_index, marker_size, resolution, aruco dictionary."""
        tab = self.tabview.add("Vision")
        tab.grid_columnconfigure(1, weight=1)

        vis = self.config.get("vision", {})
        aruco = vis.get("aruco", {})
        res = vis.get("resolution", {})

        ctk.CTkLabel(tab, text="Camera Index:").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        self.opt_camera_index = ctk.CTkOptionMenu(
            tab, values=["0", "1", "2"]
        )
        self.opt_camera_index.set(str(vis.get("camera_index", 0)))
        self.opt_camera_index.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Marker Size (m):").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_marker_size = ctk.CTkEntry(tab)
        self.entry_marker_size.insert(0, str(aruco.get("marker_size", 0.05)))
        self.entry_marker_size.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Resolution Width:").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_res_width = ctk.CTkEntry(tab)
        self.entry_res_width.insert(0, str(res.get("width", 1280)))
        self.entry_res_width.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Resolution Height:").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_res_height = ctk.CTkEntry(tab)
        self.entry_res_height.insert(0, str(res.get("height", 720)))
        self.entry_res_height.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="ArUco Dictionary:").grid(
            row=4, column=0, sticky="w", padx=8, pady=6
        )
        self.opt_aruco_dict = ctk.CTkOptionMenu(tab, values=ARUCO_DICTIONARIES)
        self.opt_aruco_dict.set(str(aruco.get("dictionary", "DICT_4X4_50")))
        self.opt_aruco_dict.grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    def _build_ascom_tab(self):
        """ASCOM tab: telescope_prog_id."""
        tab = self.tabview.add("ASCOM")
        tab.grid_columnconfigure(1, weight=1)

        ascom = self.config.get("ascom", {})

        ctk.CTkLabel(tab, text="Telescope ProgID:").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_prog_id = ctk.CTkEntry(tab, width=280)
        self.entry_prog_id.insert(
            0, str(ascom.get("telescope_prog_id", "ASCOM.Simulator.Telescope"))
        )
        self.entry_prog_id.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

    def _build_location_tab(self):
        """Location tab: latitude, longitude, elevation."""
        tab = self.tabview.add("Location")
        tab.grid_columnconfigure(1, weight=1)

        obs = self.config.get("math", {}).get("observatory", {})

        ctk.CTkLabel(tab, text="Latitude (°):").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_latitude = ctk.CTkEntry(tab)
        self.entry_latitude.insert(0, str(obs.get("latitude", 0.0)))
        self.entry_latitude.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Longitude (°):").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_longitude = ctk.CTkEntry(tab)
        self.entry_longitude.insert(0, str(obs.get("longitude", 0.0)))
        self.entry_longitude.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Elevation (m):").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_elevation = ctk.CTkEntry(tab)
        self.entry_elevation.insert(0, str(obs.get("elevation", 0)))
        self.entry_elevation.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    def _build_geometry_tab(self):
        """Geometry tab: dome specs and mount specs."""
        tab = self.tabview.add("Geometry")
        tab.grid_columnconfigure(1, weight=1)

        dome = self.config.get("math", {}).get("dome", {})
        mount = self.config.get("math", {}).get("mount", {})

        ctk.CTkLabel(tab, text="Dome Radius (m):").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_dome_radius = ctk.CTkEntry(tab)
        self.entry_dome_radius.insert(0, str(dome.get("radius", 2.5)))
        self.entry_dome_radius.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Slit Width (m):").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_slit_width = ctk.CTkEntry(tab)
        self.entry_slit_width.insert(0, str(dome.get("slit_width", 0.8)))
        self.entry_slit_width.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Pier Height (m):").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_pier_height = ctk.CTkEntry(tab)
        self.entry_pier_height.insert(0, str(mount.get("pier_height", 1.5)))
        self.entry_pier_height.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="GEM Offset East (m):").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_gem_offset_east = ctk.CTkEntry(tab)
        self.entry_gem_offset_east.insert(0, str(mount.get("gem_offset_east", 0.0)))
        self.entry_gem_offset_east.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="GEM Offset North (m):").grid(
            row=4, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_gem_offset_north = ctk.CTkEntry(tab)
        self.entry_gem_offset_north.insert(0, str(mount.get("gem_offset_north", 0.0)))
        self.entry_gem_offset_north.grid(row=4, column=1, sticky="ew", padx=8, pady=6)

    def _build_control_tab(self):
        """Control tab: drift correction, thresholds, speeds."""
        tab = self.tabview.add("Control")
        tab.grid_columnconfigure(1, weight=1)

        ctrl = self.config.get("control", {})

        self.var_drift_enabled = ctk.StringVar(
            value="on" if ctrl.get("drift_correction_enabled", True) else "off"
        )
        self.switch_drift = ctk.CTkSwitch(
            tab, text="Drift Correction Enabled",
            variable=self.var_drift_enabled,
            onvalue="on", offvalue="off",
        )
        self.switch_drift.grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(tab, text="Correction Threshold (°):").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_correction_threshold = ctk.CTkEntry(tab)
        self.entry_correction_threshold.insert(
            0, str(ctrl.get("correction_threshold", 0.5))
        )
        self.entry_correction_threshold.grid(
            row=1, column=1, sticky="ew", padx=8, pady=6
        )

        ctk.CTkLabel(tab, text="Max Speed:").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_max_speed = ctk.CTkEntry(tab)
        self.entry_max_speed.insert(0, str(ctrl.get("max_speed", 100)))
        self.entry_max_speed.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Update Rate (Hz):").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_update_rate = ctk.CTkEntry(tab)
        self.entry_update_rate.insert(0, str(ctrl.get("update_rate", 10)))
        self.entry_update_rate.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

    def _build_safety_tab(self):
        """Safety tab: collision avoidance settings."""
        tab = self.tabview.add("Safety")
        tab.grid_columnconfigure(1, weight=1)

        safety = self.config.get("safety", {})

        self.var_telescope_protrudes = ctk.StringVar(
            value="on" if safety.get("telescope_protrudes", True) else "off"
        )
        self.switch_protrudes = ctk.CTkSwitch(
            tab, text="Telescope Protrudes",
            variable=self.var_telescope_protrudes,
            onvalue="on", offvalue="off",
        )
        self.switch_protrudes.grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(tab, text="Safe Altitude (°):").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_safe_altitude = ctk.CTkEntry(tab)
        self.entry_safe_altitude.insert(
            0, str(safety.get("safe_altitude", 90.0))
        )
        self.entry_safe_altitude.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(tab, text="Max Nudge (°):").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        self.entry_max_nudge = ctk.CTkEntry(tab)
        self.entry_max_nudge.insert(
            0, str(safety.get("max_nudge_while_protruding", 2.0))
        )
        self.entry_max_nudge.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

    # ---- Save ----------------------------------------------------------
    def _on_save(self):
        """Read all widget values, convert types, and write config.yaml."""
        # Hardware
        self.config.setdefault("hardware", {})
        self.config["hardware"]["serial_port"] = self.entry_serial_port.get()
        self.config["hardware"]["baud_rate"] = self._to_int(
            self.entry_baud_rate.get(), 9600
        )

        # Vision
        self.config.setdefault("vision", {})
        self.config["vision"]["camera_index"] = self._to_int(
            self.opt_camera_index.get(), 0
        )
        self.config["vision"].setdefault("aruco", {})
        self.config["vision"]["aruco"]["marker_size"] = self._to_float(
            self.entry_marker_size.get(), 0.05
        )
        self.config["vision"]["aruco"]["dictionary"] = self.opt_aruco_dict.get()
        self.config["vision"].setdefault("resolution", {})
        self.config["vision"]["resolution"]["width"] = self._to_int(
            self.entry_res_width.get(), 1280
        )
        self.config["vision"]["resolution"]["height"] = self._to_int(
            self.entry_res_height.get(), 720
        )

        # ASCOM
        self.config.setdefault("ascom", {})
        self.config["ascom"]["telescope_prog_id"] = self.entry_prog_id.get()

        # Location
        self.config.setdefault("math", {})
        self.config["math"].setdefault("observatory", {})
        self.config["math"]["observatory"]["latitude"] = self._to_float(
            self.entry_latitude.get(), 0.0
        )
        self.config["math"]["observatory"]["longitude"] = self._to_float(
            self.entry_longitude.get(), 0.0
        )
        self.config["math"]["observatory"]["elevation"] = self._to_float(
            self.entry_elevation.get(), 0.0
        )

        # Geometry
        self.config["math"].setdefault("dome", {})
        self.config["math"]["dome"]["radius"] = self._to_float(
            self.entry_dome_radius.get(), 2.5
        )
        self.config["math"]["dome"]["slit_width"] = self._to_float(
            self.entry_slit_width.get(), 0.8
        )
        self.config["math"].setdefault("mount", {})
        self.config["math"]["mount"]["pier_height"] = self._to_float(
            self.entry_pier_height.get(), 1.5
        )
        self.config["math"]["mount"]["gem_offset_east"] = self._to_float(
            self.entry_gem_offset_east.get(), 0.0
        )
        self.config["math"]["mount"]["gem_offset_north"] = self._to_float(
            self.entry_gem_offset_north.get(), 0.0
        )

        # Control
        self.config.setdefault("control", {})
        self.config["control"]["drift_correction_enabled"] = (
            self.var_drift_enabled.get() == "on"
        )
        self.config["control"]["correction_threshold"] = self._to_float(
            self.entry_correction_threshold.get(), 0.5
        )
        self.config["control"]["max_speed"] = self._to_int(
            self.entry_max_speed.get(), 100
        )
        self.config["control"]["update_rate"] = self._to_int(
            self.entry_update_rate.get(), 10
        )

        # Safety
        self.config.setdefault("safety", {})
        self.config["safety"]["telescope_protrudes"] = (
            self.var_telescope_protrudes.get() == "on"
        )
        self.config["safety"]["safe_altitude"] = self._to_float(
            self.entry_safe_altitude.get(), 90.0
        )
        self.config["safety"]["max_nudge_while_protruding"] = self._to_float(
            self.entry_max_nudge.get(), 2.0
        )

        # Write back
        try:
            with open(self.config_path, "w") as fh:
                yaml.safe_dump(self.config, fh, default_flow_style=False)
            logger.info("Configuration saved to %s", self.config_path)
        except OSError as exc:
            logger.error("Failed to save configuration: %s", exc)

        self.destroy()

    # ---- Helpers -------------------------------------------------------
    @staticmethod
    def _to_int(value: str, default: int) -> int:
        """Convert string to int, returning *default* on failure."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_float(value: str, default: float) -> float:
        """Convert string to float, returning *default* on failure."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
