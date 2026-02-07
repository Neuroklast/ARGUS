"""
ARGUS - Advanced Rotation Guidance Using Sensors
GUI Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Professional dark-mode Sci-Fi / SpaceX interface built with Flet for
observatory dome control and monitoring.
"""

import base64
import datetime
import logging
import math

import numpy as np
import cv2
import flet as ft
import flet.canvas as cv

from localization import t

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Font Constants
# Sans-serif (Roboto) for static labels/headings,
# Monospace (Roboto Mono) for changing numeric readouts.
# ---------------------------------------------------------------------------
FONT_DATA = ("Roboto Mono", 24, "bold")
FONT_LABEL = ("Roboto", 12)
FONT_BUTTON = ("Roboto", 14, "bold")
FONT_SECTION = ("Roboto", 13, "bold")
FONT_INDICATOR = ("Roboto", 11)
FONT_LOG = ("Roboto Mono", 10)

# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------
# NASA Mission Control dark theme (professional blue-grey, cyan accents)
THEME_DARK = {
    "bg": "#0B0E11",
    "card_bg": "#141A22",
    "accent": "#00B4D8",
    "error_readout": "#FF8C00",
    "stop_btn": "#C0392B",
    "off": "#3A4450",
    "on": "#2ECC71",
    "moving": "#F1C40F",
    "no_signal": "#667788",
    "text": "#B0BEC5",
    "heading": "#E0E6EC",
    "border": "#2A3442",
    "radar_circle": "#3A4450",
    "radar_mount": "#FF3333",
    "radar_dome": "#00B4D8",
    "banner_warn_bg": "#F1C40F",
    "banner_warn_fg": "#000000",
    "banner_crit_bg": "#C0392B",
    "banner_crit_fg": "#FFFFFF",
}

# NASA Night-Vision red/black theme (pure black with red lines/text)
THEME_NIGHT = {
    "bg": "#000000",
    "card_bg": "#000000",
    "accent": "#FF0000",
    "error_readout": "#FF0000",
    "stop_btn": "#FF0000",
    "off": "#330000",
    "on": "#FF0000",
    "moving": "#FF0000",
    "no_signal": "#550000",
    "text": "#FF0000",
    "heading": "#FF0000",
    "border": "#FF0000",
    "radar_circle": "#FF0000",
    "radar_mount": "#FF0000",
    "radar_dome": "#FF0000",
    "banner_warn_bg": "#000000",
    "banner_warn_fg": "#FF0000",
    "banner_crit_bg": "#000000",
    "banner_crit_fg": "#FF0000",
}

# Active colour constants (start with dark theme, toggled at runtime)
COLOR_BG = THEME_DARK["bg"]
COLOR_ERROR = THEME_DARK["error_readout"]
COLOR_STOP_BTN = THEME_DARK["stop_btn"]
COLOR_STOP_HOVER = "#E74C3C"
COLOR_OFF = THEME_DARK["off"]
COLOR_ON = THEME_DARK["on"]
COLOR_MOVING = THEME_DARK["moving"]
COLOR_NO_SIGNAL = THEME_DARK["no_signal"]
COLOR_CARD_BG = THEME_DARK["card_bg"]
COLOR_ACCENT = THEME_DARK["accent"]
CARD_CORNER_RADIUS = 12

# Radar constants
_RADAR_SIZE = 140
_RADAR_CX = _RADAR_SIZE / 2
_RADAR_CY = _RADAR_SIZE / 2
_RADAR_R = 55


def _card(content: ft.Control, **kwargs) -> ft.Container:
    """Wrap *content* in a Material Design 3 card container."""
    return ft.Container(
        content=content,
        bgcolor=COLOR_CARD_BG,
        border_radius=CARD_CORNER_RADIUS,
        padding=10,
        **kwargs,
    )


def _generate_placeholder_frame(width: int = 640, height: int = 480) -> str:
    """Generate a dark placeholder image with crosshair and text, return as base64 PNG."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (10, 10, 10)
    cx, cy = width // 2, height // 2
    cv2.line(img, (cx - 40, cy), (cx + 40, cy), (60, 60, 60), 1)
    cv2.line(img, (cx, cy - 40), (cx, cy + 40), (60, 60, 60), 1)
    cv2.circle(img, (cx, cy), 30, (60, 60, 60), 1)
    cv2.putText(img, "NO CAMERA SIGNAL", (cx - 130, cy - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 80), 1)
    cv2.putText(img, "Connect USB camera or configure index in Settings",
                (cx - 250, cy + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)
    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode("ascii")


class ArgusGUI:
    """Main ARGUS GUI built with Flet.

    Args:
        page: The Flet ``Page`` object provided by ``ft.app(target=...)``.
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self._theme = dict(THEME_DARK)
        self._night_mode = False

        # -- Text elements for thread-safe updates -----------------------
        self.lbl_mount_az = ft.Text(
            "---.-°", size=32, font_family="RobotoMono",
            color=self._theme["accent"], weight=ft.FontWeight.BOLD,
        )
        self.lbl_dome_az = ft.Text(
            "---.-°", size=32, font_family="RobotoMono",
            color=self._theme["accent"], weight=ft.FontWeight.BOLD,
        )
        self.lbl_error = ft.Text(
            "---.-°", size=32, font_family="RobotoMono",
            color=self._theme["error_readout"], weight=ft.FontWeight.BOLD,
        )

        # Status indicator badges
        self.ind_ascom = ft.Container(width=36, height=16, bgcolor=COLOR_OFF,
                                       border_radius=6)
        self.ind_vision = ft.Container(width=36, height=16, bgcolor=COLOR_OFF,
                                        border_radius=6)
        self.ind_motor = ft.Container(width=36, height=16, bgcolor=COLOR_OFF,
                                       border_radius=6)

        # Status hint labels (user-facing text next to each indicator)
        self.hint_ascom = ft.Text(
            t("gui.not_connected"), size=10, color=COLOR_NO_SIGNAL, italic=True,
        )
        self.hint_vision = ft.Text(
            t("gui.not_connected"), size=10, color=COLOR_NO_SIGNAL, italic=True,
        )
        self.hint_motor = ft.Text(
            t("gui.not_connected"), size=10, color=COLOR_NO_SIGNAL, italic=True,
        )

        # Connection banner (top-level status bar)
        self.connection_banner = ft.Container(
            content=ft.Text(
                t("gui.no_hw_banner"),
                size=12, color="#000000", weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
            bgcolor="#F1C40F",
            padding=6,
            border_radius=8,
            alignment=ft.Alignment(0, 0),
            visible=True,
        )

        # Camera preview image
        self._placeholder_b64 = _generate_placeholder_frame()
        self.camera_image = ft.Image(
            src=f"data:image/png;base64,{self._placeholder_b64}",
            fit=ft.BoxFit.CONTAIN,
            expand=True,
        )

        # Radar canvas
        self.radar_canvas = cv.Canvas(
            width=_RADAR_SIZE, height=_RADAR_SIZE,
            shapes=self._radar_shapes(0.0, 0.0),
        )

        # Log list
        self.log_list = ft.ListView(
            height=60, spacing=2, auto_scroll=True,
        )

        # Control buttons (callbacks set later by the controller)
        self.btn_ccw = ft.IconButton(
            icon=ft.Icons.ARROW_BACK, tooltip=t("gui.rotate_ccw"),
            icon_size=28,
        )
        self.btn_stop = ft.IconButton(
            icon=ft.Icons.STOP_CIRCLE, tooltip=t("gui.emergency_stop"),
            icon_color="red", icon_size=36,
        )
        self.btn_cw = ft.IconButton(
            icon=ft.Icons.ARROW_FORWARD, tooltip=t("gui.rotate_cw"),
            icon_size=28,
        )

        # Mode selector
        self.mode_selector = ft.SegmentedButton(
            segments=[
                ft.Segment(value="MANUAL", label=ft.Text(t("gui.manual"))),
                ft.Segment(value="AUTO-SLAVE", label=ft.Text(t("gui.auto_slave"))),
                ft.Segment(value="CALIBRATE", label=ft.Text(t("gui.calibrate"))),
            ],
            selected=["MANUAL"],
            allow_multiple_selection=False,
        )

        # Settings button
        self.btn_settings = ft.IconButton(
            icon=ft.Icons.SETTINGS, tooltip=t("gui.open_settings"),
            icon_size=24,
        )

        # Diagnostics button
        self.btn_diagnostics = ft.IconButton(
            icon=ft.Icons.HEALTH_AND_SAFETY, tooltip=t("gui.run_diagnostics"),
            icon_size=24,
        )

        # Night mode toggle button
        self.btn_night_mode = ft.IconButton(
            icon=ft.Icons.NIGHTLIGHT_ROUND,
            tooltip=t("gui.toggle_night"),
            icon_size=24,
            on_click=lambda e: self.toggle_night_mode(),
        )

        # -- Build layout ------------------------------------------------
        self._build_layout()

    # ===================================================================
    # Layout
    # ===================================================================
    def _build_layout(self):
        """Assemble the full dashboard layout on the page."""

        # --- Video feed with live camera preview ---
        self.video_card = _card(
            ft.Container(
                content=self.camera_image,
                alignment=ft.Alignment(0, 0),
                expand=True,
                border=ft.Border.all(1, "#333333"),
            ),
            expand=True,
        )

        # --- Telemetry card (compact) ---
        telemetry_card = _card(ft.Column([
            ft.Text(t("gui.telemetry"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            ft.Row([ft.Text(t("gui.mount_az"), size=11), self.lbl_mount_az],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text(t("gui.dome_az"), size=11), self.lbl_dome_az],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text(t("gui.error"), size=11), self.lbl_error],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=2))

        # --- Radar card (compact) ---
        radar_card = _card(ft.Column([
            ft.Text(t("gui.dome_position"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            ft.Container(
                content=self.radar_canvas,
                alignment=ft.Alignment(0, 0),
            ),
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        # --- Status card ---
        def _indicator_col(label: str, badge: ft.Container,
                           hint: ft.Text) -> ft.Column:
            return ft.Column([
                ft.Text(label, size=10, text_align=ft.TextAlign.CENTER),
                badge,
                hint,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

        status_card = _card(ft.Column([
            ft.Text(t("gui.connection_status"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            ft.Row([
                _indicator_col(t("gui.telescope"), self.ind_ascom, self.hint_ascom),
                _indicator_col(t("gui.camera"), self.ind_vision, self.hint_vision),
                _indicator_col(t("gui.motor"), self.ind_motor, self.hint_motor),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        ], spacing=2))

        # --- Controls card ---
        controls_card = _card(ft.Column([
            ft.Text(t("gui.dome_control"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            ft.Row([
                self.btn_ccw, self.btn_stop, self.btn_cw,
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        ], spacing=2))

        # --- Mode card ---
        mode_card = _card(ft.Column([
            ft.Text(t("gui.operating_mode"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            self.mode_selector,
        ], spacing=2))

        # --- Toolbar card (settings, diagnostics, night mode) ---
        toolbar_card = _card(ft.Row([
            ft.Text(t("gui.tools"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            ft.Row([
                self.btn_night_mode,
                self.btn_diagnostics,
                self.btn_settings,
            ], spacing=0),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        # --- Log card (fixed height) ---
        self._log_card = _card(ft.Column([
            ft.Text(t("gui.system_log"), weight=ft.FontWeight.BOLD, size=11,
                     color=self._theme["heading"]),
            self.log_list,
        ], spacing=2))

        # --- Dashboard (right column) – NO scroll, all elements visible ---
        self._dashboard_cards = [
            telemetry_card, radar_card, status_card,
            controls_card, mode_card, toolbar_card,
        ]
        dashboard = ft.Column(
            self._dashboard_cards,
            expand=True, spacing=6,
        )

        # --- Main layout ---
        main_row = ft.Row([
            ft.Container(content=self.video_card, expand=2),
            ft.Container(content=dashboard, expand=1),
        ], expand=True, spacing=8)

        self.page.add(
            ft.Column([
                self.connection_banner,
                ft.Container(content=main_row, expand=True),
                ft.Container(
                    content=self._log_card,
                    height=100,
                ),
            ], expand=True, spacing=6),
        )

    # ===================================================================
    # Radar drawing helpers
    # ===================================================================
    @staticmethod
    def _radar_shapes(mount_az: float, dome_az: float) -> list:
        """Return a list of canvas shapes for the radar view."""
        cx, cy, r = _RADAR_CX, _RADAR_CY, _RADAR_R
        shapes: list = []

        # 1. Observatory circle
        shapes.append(cv.Circle(
            cx, cy, r,
            paint=ft.Paint(color="#555555", stroke_width=2,
                           style=ft.PaintingStyle.STROKE),
        ))

        # 2. Red line for mount azimuth (telescope)
        angle_rad = math.radians(mount_az - 90)
        arrow_len = r - 6
        ax = cx + arrow_len * math.cos(angle_rad)
        ay = cy + arrow_len * math.sin(angle_rad)
        shapes.append(cv.Line(
            cx, cy, ax, ay,
            paint=ft.Paint(color="#FF0000", stroke_width=3,
                           style=ft.PaintingStyle.STROKE),
        ))

        # 3. Yellow arc for dome slit (~20° wide)
        arc_half_deg = 10
        start_deg = dome_az - 90 - arc_half_deg
        sweep_deg = 2 * arc_half_deg
        shapes.append(cv.Arc(
            cx - r, cy - r, 2 * r, 2 * r,
            start_angle=math.radians(start_deg),
            sweep_angle=math.radians(sweep_deg),
            paint=ft.Paint(color="#F1C40F", stroke_width=4,
                           style=ft.PaintingStyle.STROKE),
        ))

        return shapes

    def draw_radar(self, mount_az: float, dome_az: float) -> None:
        """Redraw the radar view showing mount and dome positions.

        Args:
            mount_az: Current mount azimuth in degrees.
            dome_az:  Current dome slit azimuth in degrees.
        """
        self.radar_canvas.shapes = self._radar_shapes(mount_az, dome_az)

    # ===================================================================
    # Camera preview
    # ===================================================================
    def update_camera_preview(self, frame, marker_data=None,
                              drift=None, telemetry=None) -> None:
        """Update the camera preview image with optional detection overlay.

        Args:
            frame: numpy array (BGR) from camera, or ``None`` for placeholder.
            marker_data: Marker detection dict from VisionSystem, or ``None``.
            drift: Tuple (dx, dy) drift in pixels, or ``None``.
            telemetry: Optional dict with mount_az, dome_az, error, mode, health.
        """
        if frame is None:
            self.camera_image.src = f"data:image/png;base64,{self._placeholder_b64}"
            try:
                self.page.update()
            except Exception:
                pass
            return

        overlay = frame.copy()
        h, w = overlay.shape[:2]
        cx, cy = w // 2, h // 2

        # Draw crosshair at centre
        cv2.line(overlay, (cx - 30, cy), (cx + 30, cy), (0, 180, 180), 1)
        cv2.line(overlay, (cx, cy - 30), (cx, cy + 30), (0, 180, 180), 1)

        # HUD overlay - measurement data
        hud_color = (0, 200, 200)  # Cyan for readability
        hud_y = 20
        if telemetry:
            mount_az = telemetry.get("mount_az")
            dome_az = telemetry.get("dome_az")
            error = telemetry.get("error")
            mode = telemetry.get("mode", "")
            health = telemetry.get("health", "")
            if mount_az is not None:
                cv2.putText(overlay, f"{t('overlay.mount_az')}: {mount_az:06.1f}°",
                            (w - 250, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, hud_color, 1)
                hud_y += 22
            if dome_az is not None:
                cv2.putText(overlay, f"{t('overlay.dome_az')}: {dome_az:06.1f}°",
                            (w - 250, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, hud_color, 1)
                hud_y += 22
            if error is not None:
                err_color = (0, 255, 0) if abs(error) < 2.0 else (0, 165, 255) if abs(error) < 5.0 else (0, 0, 255)
                cv2.putText(overlay, f"{t('overlay.error')}: {error:+.1f}°",
                            (w - 250, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, err_color, 1)
                hud_y += 22
            if mode:
                cv2.putText(overlay, f"MODE: {mode}",
                            (w - 250, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, hud_color, 1)
                hud_y += 22
            if health:
                h_color = (0, 255, 0) if health == "HEALTHY" else (0, 165, 255) if health == "DEGRADED" else (0, 0, 255)
                cv2.putText(overlay, f"{t('overlay.status')}: {health}",
                            (w - 250, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, h_color, 1)

        if marker_data and marker_data.get("markers"):
            for m in marker_data["markers"]:
                corners = m["corners"].astype(int)
                cv2.polylines(overlay, [corners], True, (0, 255, 0), 2)
                mc = tuple(map(int, m["center"]))
                cv2.putText(overlay, f"ID:{m['id']}", (mc[0] + 10, mc[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                cv2.circle(overlay, mc, 4, (0, 255, 0), -1)

            if drift is not None:
                dx, dy = drift
                cv2.putText(overlay, f"DRIFT dx={dx:+.1f} dy={dy:+.1f}",
                            (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 200, 200), 1)
                # Arrow from centre to drift direction
                end_x = int(cx + dx * 0.5)
                end_y = int(cy + dy * 0.5)
                cv2.arrowedLine(overlay, (cx, cy), (end_x, end_y),
                                (0, 200, 200), 2)

            cv2.putText(overlay, t("gui.tracking"), (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        else:
            cv2.putText(overlay, t("gui.no_markers"), (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 200), 1)

        # Encode to base64 PNG
        _, buf = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        self.camera_image.src = f"data:image/jpeg;base64,{b64}"
        try:
            self.page.update()
        except Exception:
            pass

    # ===================================================================
    # Night mode / theme toggle
    # ===================================================================
    def toggle_night_mode(self) -> None:
        """Switch between NASA Mission Control theme and Night-Vision red/black mode."""
        self._night_mode = not self._night_mode
        self._theme = dict(THEME_NIGHT) if self._night_mode else dict(THEME_DARK)

        # Update page background
        self.page.bgcolor = self._theme["bg"]

        # Update accent colours on telemetry labels
        self.lbl_mount_az.color = self._theme["accent"]
        self.lbl_dome_az.color = self._theme["accent"]
        self.lbl_error.color = self._theme["error_readout"]

        # Update all card backgrounds and borders
        for card in self._dashboard_cards:
            card.bgcolor = self._theme["card_bg"]
            if self._night_mode:
                card.border = ft.Border.all(1, self._theme["border"])
            else:
                card.border = None
        # Also update video card and log card
        if hasattr(self, 'video_card'):
            self.video_card.bgcolor = self._theme["card_bg"]
            if self._night_mode:
                self.video_card.border = ft.Border.all(1, self._theme["border"])
            else:
                self.video_card.border = None
        if hasattr(self, '_log_card'):
            self._log_card.bgcolor = self._theme["card_bg"]
            if self._night_mode:
                self._log_card.border = ft.Border.all(1, self._theme["border"])
            else:
                self._log_card.border = None

        # Toggle icon
        self.btn_night_mode.icon = (
            ft.Icons.LIGHT_MODE if self._night_mode else ft.Icons.NIGHTLIGHT_ROUND
        )
        self.btn_night_mode.icon_color = self._theme["accent"]

        try:
            self.page.update()
        except Exception:
            pass

    # ===================================================================
    # Public API
    # ===================================================================
    def batch_update(self) -> None:
        """Call page.update() once. Use after multiple property changes."""
        try:
            self.page.update()
        except Exception:
            pass

    def update_telemetry(self, mount_az: float, dome_az: float) -> None:
        """Update the telemetry readouts on the dashboard.

        Thread-safe: modifies text values; caller should use batch_update().

        Args:
            mount_az: Current mount azimuth in degrees.
            dome_az:  Current dome azimuth in degrees.
        """
        error = mount_az - dome_az
        # Normalise to ±180° so the error is meaningful near the 0°/360° boundary
        if error > 180:
            error -= 360
        elif error < -180:
            error += 360
        self.lbl_mount_az.value = f"{mount_az:06.1f}°"
        self.lbl_dome_az.value = f"{dome_az:06.1f}°"
        self.lbl_error.value = f"{error:+06.1f}°"
        self.draw_radar(mount_az, dome_az)

    def write_log(self, message: str) -> None:
        """Append a timestamped message to the log console.

        Thread-safe: calls ``page.update()`` after adding the line.

        Args:
            message: The log text to display.
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        entry = ft.Text(line, size=10, font_family="RobotoMono",
                        color="#CCCCCC")
        self.log_list.controls.append(entry)
        # Keep at most 200 lines
        if len(self.log_list.controls) > 200:
            self.log_list.controls.pop(0)
        try:
            self.page.update()
        except Exception:
            pass

    # Backward-compatible alias
    append_log = write_log

    def set_status(self, component: str, is_ok: bool) -> None:
        """Set the colour of a status indicator.

        Args:
            component: One of ``"ascom"``, ``"vision"``, ``"motor"``.
            is_ok:     ``True`` to turn the indicator on.
        """
        mapping = {
            "ascom": (self.ind_ascom, COLOR_ON),
            "vision": (self.ind_vision, COLOR_ON),
            "motor": (self.ind_motor, COLOR_MOVING),
        }
        if component not in mapping:
            return
        badge, on_colour = mapping[component]
        badge.bgcolor = on_colour if is_ok else COLOR_OFF

    # Backward-compatible alias used by ArgusController
    set_indicator = set_status

    def set_status_hint(self, component: str, text: str) -> None:
        """Update the hint label below a status indicator.

        Args:
            component: One of ``"ascom"``, ``"vision"``, ``"motor"``.
            text:      Short human-readable status hint.
        """
        hint_mapping = {
            "ascom": self.hint_ascom,
            "vision": self.hint_vision,
            "motor": self.hint_motor,
        }
        hint = hint_mapping.get(component)
        if hint is None:
            return
        hint.value = text

    def update_connection_banner(self, ascom_ok: bool, vision_ok: bool,
                                 motor_ok: bool) -> None:
        """Update the top-level connection status banner.

        The banner is hidden when all components are connected, shows
        a yellow warning when partially connected, and a red alert
        when nothing is connected.

        Args:
            ascom_ok:  Whether the telescope is connected.
            vision_ok: Whether the camera is connected.
            motor_ok:  Whether the motor controller is connected.
        """
        all_ok = ascom_ok and vision_ok and motor_ok
        none_ok = not ascom_ok and not vision_ok and not motor_ok

        if all_ok:
            self.connection_banner.visible = False
        else:
            self.connection_banner.visible = True
            parts = []
            if not ascom_ok:
                parts.append(t("banner.telescope"))
            if not vision_ok:
                parts.append(t("banner.camera"))
            if not motor_ok:
                parts.append(t("banner.motor"))
            missing = ", ".join(parts)

            if none_ok:
                msg = t("gui.no_hw_banner")
                bg = "#C0392B"
                fg = "#FFFFFF"
            else:
                msg = t("banner.missing").format(missing=missing)
                bg = "#F1C40F"
                fg = "#000000"

            self.connection_banner.bgcolor = bg
            banner_text = self.connection_banner.content
            banner_text.value = msg
            banner_text.color = fg

        try:
            self.page.update()
        except Exception:
            pass

    # ===================================================================
    # Diagnostics dialog (with loading state)
    # ===================================================================
    def show_diagnostics_loading(self) -> ft.AlertDialog:
        """Show a diagnostics dialog with a loading indicator immediately.

        Returns the dialog so the caller can replace its content later.
        """
        dlg = ft.AlertDialog(
            title=ft.Text(t("gui.diagnostics_title")),
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=40, height=40, stroke_width=3),
                    ft.Text(t("gui.diagnostics_running"), size=13,
                            text_align=ft.TextAlign.CENTER),
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   spacing=12),
                width=560,
                height=420,
                alignment=ft.Alignment(0, 0),
            ),
            actions=[
                ft.TextButton(t("gui.close"), on_click=lambda e: self._close_dialog(dlg)),
            ],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        try:
            self.page.update()
        except Exception:
            pass
        return dlg

    def show_diagnostics(self, report, dlg=None) -> None:
        """Open (or update) a dialog showing the diagnostics report.

        Args:
            report: A :class:`diagnostics.DiagReport` instance.
            dlg:    Optional pre-existing loading dialog to update.
        """
        from diagnostics import Status

        _STATUS_ICONS = {
            Status.OK: ("✓", "#2ECC71"),
            Status.WARNING: ("⚠", "#F1C40F"),
            Status.ERROR: ("✗", "#E74C3C"),
            Status.INFO: ("ℹ", "#3498DB"),
        }

        rows: list = []
        for r in report.results:
            icon_char, icon_color = _STATUS_ICONS.get(
                r.status, ("?", "#888888")
            )
            parts = [
                ft.Text(icon_char, color=icon_color, size=14,
                        weight=ft.FontWeight.BOLD),
                ft.Text(f"[{r.category}] {r.name}", size=12,
                        weight=ft.FontWeight.BOLD),
                ft.Text(r.message, size=11, color="#CCCCCC"),
            ]
            if r.suggestion:
                parts.append(ft.Text(
                    f"→ {r.suggestion}", size=10, italic=True,
                    color="#F1C40F",
                ))
            rows.append(ft.Container(
                content=ft.Column(parts, spacing=2),
                padding=6,
                border=ft.Border(
                    bottom=ft.BorderSide(1, "#333333"),
                ),
            ))

        # Summary header
        header = ft.Text(
            f"Diagnostics: {report.summary}  ({report.duration_s}s)",
            size=13, weight=ft.FontWeight.BOLD,
        )

        result_content = ft.Container(
            content=ft.Column(
                [header] + rows,
                scroll=ft.ScrollMode.AUTO,
                spacing=4,
            ),
            width=560,
            height=420,
        )

        if dlg is not None:
            # Update the existing loading dialog with results
            dlg.content = result_content
        else:
            dlg = ft.AlertDialog(
                title=ft.Text(t("gui.diagnostics_title")),
                content=result_content,
                actions=[
                    ft.TextButton(t("gui.close"),
                                  on_click=lambda e: self._close_dialog(dlg)),
                ],
            )
            self.page.overlay.append(dlg)
            dlg.open = True

        try:
            self.page.update()
        except Exception:
            pass

    def _close_dialog(self, dlg: ft.AlertDialog) -> None:
        """Close an open dialog."""
        dlg.open = False
        try:
            self.page.update()
        except Exception:
            pass


# -----------------------------------------------------------------------
def _standalone_main(page: ft.Page):
    """Standalone entry point for previewing the GUI without the controller."""
    page.title = "ARGUS – Dome Control"
    page.bgcolor = COLOR_BG
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1280
    page.window.height = 720
    gui = ArgusGUI(page)
    # Keep a reference on the page to prevent garbage collection
    page._argus_gui = gui


if __name__ == "__main__":
    ft.app(target=_standalone_main)
