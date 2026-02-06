"""
ARGUS - Advanced Rotation Guidance Using Sensors
Settings GUI Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Provides a Flet AlertDialog-based settings panel for editing
config.yaml without manual file editing.
"""

import logging
from pathlib import Path
from typing import Optional, Callable

import yaml
import flet as ft

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


# --- Conversion helpers (kept as static-compatible functions) ---------------
def _to_int(value: str, default: int) -> int:
    """Convert string to int, returning *default* on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _to_float(value: str, default: float) -> float:
    """Convert string to float, returning *default* on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# Backward-compatible class-level access used by tests
class SettingsWindow:
    """Shim that exposes the static helpers for backward compatibility."""
    _to_int = staticmethod(_to_int)
    _to_float = staticmethod(_to_float)


def show_settings_dialog(
    page: ft.Page,
    config: dict,
    on_save_callback: Callable[[dict], None],
    config_path: Optional[str] = None,
) -> None:
    """Open a settings dialog with tabs for all ARGUS configuration groups.

    Args:
        page: The Flet page to attach the dialog to.
        config: Current configuration dictionary.
        on_save_callback: Called with the updated config dict on save.
        config_path: Path to persist changes (defaults to repo config.yaml).
    """
    cfg_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    # -- Field references ------------------------------------------------
    hw = config.get("hardware", {})
    vis = config.get("vision", {})
    aruco = vis.get("aruco", {})
    res = vis.get("resolution", {})
    ascom = config.get("ascom", {})
    obs = config.get("math", {}).get("observatory", {})
    dome = config.get("math", {}).get("dome", {})
    mount = config.get("math", {}).get("mount", {})
    ctrl = config.get("control", {})
    safety = config.get("safety", {})

    # -- Hardware tab fields ---
    tf_serial_port = ft.TextField(label="Serial Port",
                                   value=str(hw.get("serial_port", "COM3")))
    tf_baud_rate = ft.TextField(label="Baud Rate",
                                 value=str(hw.get("baud_rate", 9600)))

    # -- Vision tab fields ---
    dd_camera_index = ft.Dropdown(
        label="Camera Index",
        options=[ft.dropdown.Option(str(i)) for i in range(3)],
        value=str(vis.get("camera_index", 0)),
    )
    tf_marker_size = ft.TextField(label="Marker Size (m)",
                                   value=str(aruco.get("marker_size", 0.05)))
    tf_res_width = ft.TextField(label="Resolution Width",
                                 value=str(res.get("width", 1280)))
    tf_res_height = ft.TextField(label="Resolution Height",
                                  value=str(res.get("height", 720)))
    dd_aruco_dict = ft.Dropdown(
        label="ArUco Dictionary",
        options=[ft.dropdown.Option(d) for d in ARUCO_DICTIONARIES],
        value=str(aruco.get("dictionary", "DICT_4X4_50")),
    )

    # -- ASCOM tab fields ---
    tf_prog_id = ft.TextField(label="Telescope ProgID",
                               value=str(ascom.get("telescope_prog_id",
                                                    "ASCOM.Simulator.Telescope")))

    # -- Location tab fields ---
    tf_latitude = ft.TextField(label="Latitude (°)",
                                value=str(obs.get("latitude", 0.0)))
    tf_longitude = ft.TextField(label="Longitude (°)",
                                 value=str(obs.get("longitude", 0.0)))
    tf_elevation = ft.TextField(label="Elevation (m)",
                                 value=str(obs.get("elevation", 0)))

    # -- Geometry tab fields ---
    tf_dome_radius = ft.TextField(label="Dome Radius (m)",
                                   value=str(dome.get("radius", 2.5)))
    tf_slit_width = ft.TextField(label="Slit Width (m)",
                                  value=str(dome.get("slit_width", 0.8)))
    tf_pier_height = ft.TextField(label="Pier Height (m)",
                                   value=str(mount.get("pier_height", 1.5)))
    tf_gem_offset_east = ft.TextField(
        label="GEM Offset East (m)",
        value=str(mount.get("gem_offset_east", 0.0)),
    )
    tf_gem_offset_north = ft.TextField(
        label="GEM Offset North (m)",
        value=str(mount.get("gem_offset_north", 0.0)),
    )

    # -- Control tab fields ---
    sw_drift = ft.Switch(label="Drift Correction Enabled",
                          value=ctrl.get("drift_correction_enabled", True))
    tf_correction_threshold = ft.TextField(
        label="Correction Threshold (°)",
        value=str(ctrl.get("correction_threshold", 0.5)),
    )
    tf_max_speed = ft.TextField(label="Max Speed",
                                 value=str(ctrl.get("max_speed", 100)))
    tf_update_rate = ft.TextField(label="Update Rate (Hz)",
                                   value=str(ctrl.get("update_rate", 10)))

    # -- Safety tab fields ---
    sw_protrudes = ft.Switch(label="Telescope Protrudes",
                              value=safety.get("telescope_protrudes", True))
    tf_safe_altitude = ft.TextField(
        label="Safe Altitude (°)",
        value=str(safety.get("safe_altitude", 90.0)),
    )
    tf_max_nudge = ft.TextField(
        label="Max Nudge (°)",
        value=str(safety.get("max_nudge_while_protruding", 2.0)),
    )

    # -- Tab layout -------------------------------------------------------
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Hardware", content=ft.Column([
                tf_serial_port, tf_baud_rate,
            ], spacing=8, scroll=ft.ScrollMode.AUTO)),
            ft.Tab(text="Vision", content=ft.Column([
                dd_camera_index, tf_marker_size,
                tf_res_width, tf_res_height, dd_aruco_dict,
            ], spacing=8, scroll=ft.ScrollMode.AUTO)),
            ft.Tab(text="ASCOM", content=ft.Column([
                tf_prog_id,
            ], spacing=8)),
            ft.Tab(text="Location", content=ft.Column([
                tf_latitude, tf_longitude, tf_elevation,
            ], spacing=8)),
            ft.Tab(text="Geometry", content=ft.Column([
                tf_dome_radius, tf_slit_width,
                tf_pier_height, tf_gem_offset_east, tf_gem_offset_north,
            ], spacing=8, scroll=ft.ScrollMode.AUTO)),
            ft.Tab(text="Control", content=ft.Column([
                sw_drift, tf_correction_threshold, tf_max_speed, tf_update_rate,
            ], spacing=8)),
            ft.Tab(text="Safety", content=ft.Column([
                sw_protrudes, tf_safe_altitude, tf_max_nudge,
            ], spacing=8)),
        ],
        expand=True,
    )

    # -- Save callback ----------------------------------------------------
    def _on_save(e):
        new_cfg = dict(config)

        # Hardware
        new_cfg.setdefault("hardware", {})
        new_cfg["hardware"]["serial_port"] = tf_serial_port.value
        new_cfg["hardware"]["baud_rate"] = _to_int(tf_baud_rate.value, 9600)

        # Vision
        new_cfg.setdefault("vision", {})
        new_cfg["vision"]["camera_index"] = _to_int(dd_camera_index.value, 0)
        new_cfg["vision"].setdefault("aruco", {})
        new_cfg["vision"]["aruco"]["marker_size"] = _to_float(
            tf_marker_size.value, 0.05
        )
        new_cfg["vision"]["aruco"]["dictionary"] = dd_aruco_dict.value
        new_cfg["vision"].setdefault("resolution", {})
        new_cfg["vision"]["resolution"]["width"] = _to_int(
            tf_res_width.value, 1280
        )
        new_cfg["vision"]["resolution"]["height"] = _to_int(
            tf_res_height.value, 720
        )

        # ASCOM
        new_cfg.setdefault("ascom", {})
        new_cfg["ascom"]["telescope_prog_id"] = tf_prog_id.value

        # Location
        new_cfg.setdefault("math", {})
        new_cfg["math"].setdefault("observatory", {})
        new_cfg["math"]["observatory"]["latitude"] = _to_float(
            tf_latitude.value, 0.0
        )
        new_cfg["math"]["observatory"]["longitude"] = _to_float(
            tf_longitude.value, 0.0
        )
        new_cfg["math"]["observatory"]["elevation"] = _to_float(
            tf_elevation.value, 0.0
        )

        # Geometry
        new_cfg["math"].setdefault("dome", {})
        new_cfg["math"]["dome"]["radius"] = _to_float(
            tf_dome_radius.value, 2.5
        )
        new_cfg["math"]["dome"]["slit_width"] = _to_float(
            tf_slit_width.value, 0.8
        )
        new_cfg["math"].setdefault("mount", {})
        new_cfg["math"]["mount"]["pier_height"] = _to_float(
            tf_pier_height.value, 1.5
        )
        new_cfg["math"]["mount"]["gem_offset_east"] = _to_float(
            tf_gem_offset_east.value, 0.0
        )
        new_cfg["math"]["mount"]["gem_offset_north"] = _to_float(
            tf_gem_offset_north.value, 0.0
        )

        # Control
        new_cfg.setdefault("control", {})
        new_cfg["control"]["drift_correction_enabled"] = sw_drift.value
        new_cfg["control"]["correction_threshold"] = _to_float(
            tf_correction_threshold.value, 0.5
        )
        new_cfg["control"]["max_speed"] = _to_int(tf_max_speed.value, 100)
        new_cfg["control"]["update_rate"] = _to_int(tf_update_rate.value, 10)

        # Safety
        new_cfg.setdefault("safety", {})
        new_cfg["safety"]["telescope_protrudes"] = sw_protrudes.value
        new_cfg["safety"]["safe_altitude"] = _to_float(
            tf_safe_altitude.value, 90.0
        )
        new_cfg["safety"]["max_nudge_while_protruding"] = _to_float(
            tf_max_nudge.value, 2.0
        )

        # Persist to YAML
        try:
            with open(cfg_path, "w") as fh:
                yaml.safe_dump(new_cfg, fh, default_flow_style=False)
            logger.info("Configuration saved to %s", cfg_path)
        except OSError as exc:
            logger.error("Failed to save configuration: %s", exc)

        on_save_callback(new_cfg)
        dialog.open = False
        page.update()

    def _on_cancel(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("ARGUS – Settings"),
        content=ft.Container(
            content=tabs,
            width=520,
            height=450,
        ),
        actions=[
            ft.TextButton("CANCEL", on_click=_on_cancel),
            ft.ElevatedButton("SAVE", on_click=_on_save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()
