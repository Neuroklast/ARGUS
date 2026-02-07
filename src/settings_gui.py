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

from path_utils import resolve_path
from localization import t

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = resolve_path("config.yaml")

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


def _section_header(text: str) -> ft.Container:
    """Return a styled section header for settings groups."""
    return ft.Container(
        content=ft.Text(text, size=12, weight=ft.FontWeight.BOLD,
                        color="#00B4D8"),
        padding=ft.Padding(0, 8, 0, 4),
        border=ft.Border(bottom=ft.BorderSide(1, "#333333")),
    )


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
    dome_limits = config.get("dome", {})

    # -- Hardware tab fields ---
    tf_serial_port = ft.TextField(label=t("settings.serial_port"),
                                   value=str(hw.get("serial_port", "COM3")))
    tf_baud_rate = ft.TextField(label=t("settings.baud_rate"),
                                 value=str(hw.get("baud_rate", 9600)))

    # Motor type
    dd_motor_type = ft.Dropdown(
        label=t("settings.motor_type"),
        options=[
            ft.dropdown.Option("stepper", t("settings.motor_stepper")),
            ft.dropdown.Option("encoder", t("settings.motor_dc_encoder")),
            ft.dropdown.Option("timed", t("settings.motor_timed")),
        ],
        value=str(hw.get("motor_type", "stepper")),
    )

    # Protocol
    dd_protocol = ft.Dropdown(
        label=t("settings.comm_protocol"),
        options=[
            ft.dropdown.Option("argus", t("settings.proto_native")),
            ft.dropdown.Option("lesvedome", t("settings.proto_lesvdome")),
            ft.dropdown.Option("relay", t("settings.proto_relay")),
        ],
        value=str(hw.get("protocol", "argus")),
    )

    # Drive-specific calibration
    tf_steps_per_degree = ft.TextField(
        label=t("settings.steps_per_degree"),
        value=str(hw.get("steps_per_degree", 100.0)),
    )
    tf_ticks_per_degree = ft.TextField(
        label=t("settings.ticks_per_degree"),
        value=str(hw.get("ticks_per_degree", 50.0)),
    )
    tf_degrees_per_second = ft.TextField(
        label=t("settings.degrees_per_second"),
        value=str(hw.get("degrees_per_second", 5.0)),
    )
    tf_encoder_tolerance = ft.TextField(
        label=t("settings.encoder_tolerance"),
        value=str(hw.get("encoder_tolerance", 0.5)),
    )

    # Homing configuration
    homing = hw.get("homing", {})
    sw_homing_enabled = ft.Switch(
        label=t("settings.homing_switch"),
        value=homing.get("enabled", False),
    )
    tf_homing_azimuth = ft.TextField(
        label=t("settings.home_switch_az"),
        value=str(homing.get("azimuth", 0.0)),
    )
    dd_homing_direction = ft.Dropdown(
        label=t("settings.homing_direction"),
        options=[
            ft.dropdown.Option("CW", t("settings.dir_cw")),
            ft.dropdown.Option("CCW", t("settings.dir_ccw")),
        ],
        value=str(homing.get("direction", "CW")),
    )

    # -- Vision tab fields ---
    dd_camera_index = ft.Dropdown(
        label=t("settings.camera_index"),
        options=[ft.dropdown.Option(str(i)) for i in range(3)],
        value=str(vis.get("camera_index", 0)),
    )
    tf_marker_size = ft.TextField(label=t("settings.marker_size"),
                                   value=str(aruco.get("marker_size", 0.05)))
    tf_res_width = ft.TextField(label=t("settings.resolution_width"),
                                 value=str(res.get("width", 1280)))
    tf_res_height = ft.TextField(label=t("settings.resolution_height"),
                                  value=str(res.get("height", 720)))
    dd_aruco_dict = ft.Dropdown(
        label=t("settings.aruco_dict"),
        options=[ft.dropdown.Option(d) for d in ARUCO_DICTIONARIES],
        value=str(aruco.get("dictionary", "DICT_4X4_50")),
    )

    # -- ASCOM tab fields ---
    tf_prog_id = ft.TextField(label=t("settings.telescope_progid"),
                               value=str(ascom.get("telescope_prog_id",
                                                    "ASCOM.Simulator.Telescope")))

    # -- Location tab fields ---
    tf_latitude = ft.TextField(label=t("settings.latitude"),
                                value=str(obs.get("latitude", 0.0)))
    tf_longitude = ft.TextField(label=t("settings.longitude"),
                                 value=str(obs.get("longitude", 0.0)))
    tf_elevation = ft.TextField(label=t("settings.elevation"),
                                 value=str(obs.get("elevation", 0)))

    # -- Geometry tab fields ---
    tf_dome_radius = ft.TextField(label=t("settings.dome_radius"),
                                   value=str(dome.get("radius", 2.5)))
    tf_slit_width = ft.TextField(label=t("settings.slit_width"),
                                  value=str(dome.get("slit_width", 0.8)))
    tf_pier_height = ft.TextField(label=t("settings.pier_height"),
                                   value=str(mount.get("pier_height", 1.5)))
    tf_gem_offset_east = ft.TextField(
        label=t("settings.gem_offset_east"),
        value=str(mount.get("gem_offset_east", 0.0)),
    )
    tf_gem_offset_north = ft.TextField(
        label=t("settings.gem_offset_north"),
        value=str(mount.get("gem_offset_north", 0.0)),
    )

    # -- Control tab fields ---
    sw_drift = ft.Switch(label=t("settings.drift_correction"),
                          value=ctrl.get("drift_correction_enabled", True))
    tf_correction_threshold = ft.TextField(
        label=t("settings.correction_threshold"),
        value=str(ctrl.get("correction_threshold", 0.5)),
    )
    tf_max_speed = ft.TextField(label=t("settings.max_speed"),
                                 value=str(ctrl.get("max_speed", 100)))
    tf_update_rate = ft.TextField(label=t("settings.update_rate"),
                                   value=str(ctrl.get("update_rate", 10)))

    # -- Safety tab fields ---
    sw_protrudes = ft.Switch(label=t("settings.telescope_protrudes"),
                              value=safety.get("telescope_protrudes", True))
    tf_safe_altitude = ft.TextField(
        label=t("settings.safe_altitude"),
        value=str(safety.get("safe_altitude", 90.0)),
    )
    tf_max_nudge = ft.TextField(
        label=t("settings.max_nudge"),
        value=str(safety.get("max_nudge_while_protruding", 2.0)),
    )

    # -- Rotation limits fields ---
    tf_az_min = ft.TextField(
        label=t("settings.az_min"),
        value=str(dome_limits.get("az_min", 0.0)),
    )
    tf_az_max = ft.TextField(
        label=t("settings.az_max"),
        value=str(dome_limits.get("az_max", 360.0)),
    )

    # -- Tab layout -------------------------------------------------------
    # Flet 0.80 Tabs API: Tabs wraps a TabBar + TabBarView.
    _tab_defs = [
        (t("settings.hardware"), ft.Column([
            _section_header(t("settings.group.connection")),
            tf_serial_port, tf_baud_rate,
            _section_header(t("settings.group.motor_config")),
            dd_motor_type, dd_protocol,
            _section_header(t("settings.group.drive_cal")),
            tf_steps_per_degree, tf_ticks_per_degree,
            tf_degrees_per_second, tf_encoder_tolerance,
            _section_header(t("settings.group.homing")),
            sw_homing_enabled, tf_homing_azimuth, dd_homing_direction,
        ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)),
        (t("settings.vision"), ft.Column([
            _section_header(t("settings.group.camera")),
            dd_camera_index, tf_res_width, tf_res_height,
            _section_header(t("settings.group.aruco")),
            tf_marker_size, dd_aruco_dict,
        ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)),
        (t("settings.ascom"), ft.Column([
            _section_header(t("settings.group.telescope")),
            tf_prog_id,
        ], spacing=6, expand=True)),
        (t("settings.location"), ft.Column([
            _section_header(t("settings.group.obs_position")),
            tf_latitude, tf_longitude, tf_elevation,
        ], spacing=6, expand=True)),
        (t("settings.geometry"), ft.Column([
            _section_header(t("settings.group.dome_dims")),
            tf_dome_radius, tf_slit_width,
            _section_header(t("settings.group.mount_offsets")),
            tf_pier_height, tf_gem_offset_east, tf_gem_offset_north,
        ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)),
        (t("settings.control"), ft.Column([
            _section_header(t("settings.group.drift")),
            sw_drift, tf_correction_threshold,
            _section_header(t("settings.group.speed_timing")),
            tf_max_speed, tf_update_rate,
        ], spacing=6, expand=True)),
        (t("settings.safety"), ft.Column([
            _section_header(t("settings.group.collision")),
            sw_protrudes, tf_safe_altitude,
            _section_header(t("settings.group.slew_limits")),
            tf_max_nudge,
            _section_header(t("settings.group.rotation_limits")),
            tf_az_min, tf_az_max,
        ], spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)),
    ]

    tabs = ft.Tabs(
        content=ft.Column([
            ft.TabBar(
                tabs=[ft.Tab(label=name) for name, _ in _tab_defs],
                scrollable=True,
            ),
            ft.TabBarView(
                controls=[body for _, body in _tab_defs],
                expand=True,
            ),
        ]),
        length=len(_tab_defs),
        selected_index=0,
        expand=True,
    )

    # -- Save callback ----------------------------------------------------
    def _on_save(e):
        new_cfg = dict(config)

        # Hardware
        new_cfg.setdefault("hardware", {})
        new_cfg["hardware"]["serial_port"] = tf_serial_port.value
        new_cfg["hardware"]["baud_rate"] = _to_int(tf_baud_rate.value, 9600)
        new_cfg["hardware"]["motor_type"] = dd_motor_type.value
        new_cfg["hardware"]["protocol"] = dd_protocol.value
        new_cfg["hardware"]["steps_per_degree"] = _to_float(
            tf_steps_per_degree.value, 100.0
        )
        new_cfg["hardware"]["ticks_per_degree"] = _to_float(
            tf_ticks_per_degree.value, 50.0
        )
        new_cfg["hardware"]["degrees_per_second"] = _to_float(
            tf_degrees_per_second.value, 5.0
        )
        new_cfg["hardware"]["encoder_tolerance"] = _to_float(
            tf_encoder_tolerance.value, 0.5
        )
        new_cfg["hardware"].setdefault("homing", {})
        new_cfg["hardware"]["homing"]["enabled"] = sw_homing_enabled.value
        new_cfg["hardware"]["homing"]["azimuth"] = _to_float(
            tf_homing_azimuth.value, 0.0
        )
        new_cfg["hardware"]["homing"]["direction"] = dd_homing_direction.value

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

        # Dome rotation limits
        new_cfg.setdefault("dome", {})
        new_cfg["dome"]["az_min"] = _to_float(tf_az_min.value, 0.0)
        new_cfg["dome"]["az_max"] = _to_float(tf_az_max.value, 360.0)

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
        title=ft.Text(t("settings.window_title")),
        content=ft.Container(
            content=tabs,
            width=520,
            height=450,
        ),
        actions=[
            ft.TextButton(t("settings.cancel"), on_click=_on_cancel),
            ft.Button(t("settings.save"), on_click=_on_save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(dialog)
    dialog.open = True
    page.update()
