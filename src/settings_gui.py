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

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class SettingsWindow(ctk.CTkToplevel):
    """Settings window for editing ARGUS configuration."""

    def __init__(self, parent, config_path: Optional[str] = None):
        super().__init__(parent)

        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()

        # -- Window setup ------------------------------------------------
        self.title("ARGUS – Settings")
        self.geometry("480x420")
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
        """Vision tab: camera_index and marker_size."""
        tab = self.tabview.add("Vision")
        tab.grid_columnconfigure(1, weight=1)

        vis = self.config.get("vision", {})
        aruco = vis.get("aruco", {})

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
