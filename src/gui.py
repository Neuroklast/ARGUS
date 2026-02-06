"""
ARGUS - Advanced Rotation Guidance Using Sensors
GUI Module

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
Proprietary and confidential. See LICENSE for details.

Professional dark-mode Sci-Fi / SpaceX interface built with Flet for
observatory dome control and monitoring.
"""

import datetime
import logging
import math

import flet as ft
import flet.canvas as cv

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
# Colour Constants
# ---------------------------------------------------------------------------
COLOR_BG = "#0B0B0B"            # Page background
COLOR_ERROR = "#FF8C00"          # Orange for error readout
COLOR_STOP_BTN = "#C0392B"      # Red for STOP button
COLOR_STOP_HOVER = "#E74C3C"
COLOR_OFF = "#555555"            # Grey – indicator off
COLOR_ON = "#2ECC71"            # Green – indicator on
COLOR_MOVING = "#F1C40F"        # Yellow – motor moving
COLOR_NO_SIGNAL = "#888888"      # Grey text for "NO SIGNAL"
COLOR_CARD_BG = "#161616"       # Card background (Material Design 3)
COLOR_ACCENT = ft.Colors.CYAN   # Accent colour
CARD_CORNER_RADIUS = 16         # Rounded corners for card containers

# Radar constants
_RADAR_SIZE = 180
_RADAR_CX = _RADAR_SIZE / 2
_RADAR_CY = _RADAR_SIZE / 2
_RADAR_R = 70


def _card(content: ft.Control, **kwargs) -> ft.Container:
    """Wrap *content* in a Material Design 3 card container."""
    return ft.Container(
        content=content,
        bgcolor=COLOR_CARD_BG,
        border_radius=CARD_CORNER_RADIUS,
        padding=12,
        **kwargs,
    )


class ArgusGUI:
    """Main ARGUS GUI built with Flet.

    Args:
        page: The Flet ``Page`` object provided by ``ft.app(target=...)``.
    """

    def __init__(self, page: ft.Page):
        self.page = page

        # -- Text elements for thread-safe updates -----------------------
        self.lbl_mount_az = ft.Text(
            "---.-°", size=40, font_family="RobotoMono",
            color=COLOR_ACCENT, weight=ft.FontWeight.BOLD,
        )
        self.lbl_dome_az = ft.Text(
            "---.-°", size=40, font_family="RobotoMono",
            color=COLOR_ACCENT, weight=ft.FontWeight.BOLD,
        )
        self.lbl_error = ft.Text(
            "---.-°", size=40, font_family="RobotoMono",
            color=COLOR_ERROR, weight=ft.FontWeight.BOLD,
        )

        # Status indicator badges
        self.ind_ascom = ft.Container(width=40, height=18, bgcolor=COLOR_OFF,
                                       border_radius=6)
        self.ind_vision = ft.Container(width=40, height=18, bgcolor=COLOR_OFF,
                                        border_radius=6)
        self.ind_motor = ft.Container(width=40, height=18, bgcolor=COLOR_OFF,
                                       border_radius=6)

        # Radar canvas
        self.radar_canvas = cv.Canvas(
            width=_RADAR_SIZE, height=_RADAR_SIZE,
            shapes=self._radar_shapes(0.0, 0.0),
        )

        # Log list
        self.log_list = ft.ListView(
            height=120, spacing=2, auto_scroll=True,
        )

        # Control buttons (callbacks set later by the controller)
        self.btn_ccw = ft.IconButton(
            icon=ft.Icons.ARROW_BACK, tooltip="CCW",
            icon_size=32,
        )
        self.btn_stop = ft.IconButton(
            icon=ft.Icons.STOP_CIRCLE, tooltip="STOP",
            icon_color="red", icon_size=40,
        )
        self.btn_cw = ft.IconButton(
            icon=ft.Icons.ARROW_FORWARD, tooltip="CW",
            icon_size=32,
        )

        # Mode selector
        self.mode_selector = ft.SegmentedButton(
            segments=[
                ft.Segment(value="MANUAL", label=ft.Text("MANUAL")),
                ft.Segment(value="AUTO-SLAVE", label=ft.Text("AUTO-SLAVE")),
                ft.Segment(value="CALIBRATE", label=ft.Text("CALIBRATE")),
            ],
            selected={"MANUAL"},
            allow_multiple_selection=False,
        )

        # Settings button
        self.btn_settings = ft.IconButton(
            icon=ft.Icons.SETTINGS, tooltip="Settings",
            icon_size=28,
        )

        # -- Build layout ------------------------------------------------
        self._build_layout()

    # ===================================================================
    # Layout
    # ===================================================================
    def _build_layout(self):
        """Assemble the full dashboard layout on the page."""

        # --- Video feed placeholder ---
        video_card = _card(
            ft.Container(
                content=ft.Text(
                    "NO SIGNAL", size=24,
                    font_family="RobotoMono",
                    color=COLOR_NO_SIGNAL,
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.Alignment(0, 0),
                expand=True,
                border=ft.Border.all(1, "#333333"),
            ),
            expand=True,
        )

        # --- Telemetry card ---
        telemetry_card = _card(ft.Column([
            ft.Text("TELEMETRY", weight=ft.FontWeight.BOLD, size=13),
            ft.Row([ft.Text("MOUNT AZ", size=12), self.lbl_mount_az],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("DOME AZ", size=12), self.lbl_dome_az],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("ERROR", size=12), self.lbl_error],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=4))

        # --- Radar card ---
        radar_card = _card(ft.Column([
            ft.Text("RADAR", weight=ft.FontWeight.BOLD, size=13),
            ft.Container(
                content=self.radar_canvas,
                alignment=ft.Alignment(0, 0),
            ),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        # --- Status card ---
        def _indicator_col(label: str, badge: ft.Container) -> ft.Column:
            return ft.Column([
                ft.Text(label, size=11, text_align=ft.TextAlign.CENTER),
                badge,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)

        status_card = _card(ft.Column([
            ft.Text("STATUS", weight=ft.FontWeight.BOLD, size=13),
            ft.Row([
                _indicator_col("ASCOM", self.ind_ascom),
                _indicator_col("VISION", self.ind_vision),
                _indicator_col("MOTOR", self.ind_motor),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        ], spacing=4))

        # --- Controls card ---
        controls_card = _card(ft.Column([
            ft.Text("MANUAL CONTROL", weight=ft.FontWeight.BOLD, size=13),
            ft.Row([
                self.btn_ccw, self.btn_stop, self.btn_cw,
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        ], spacing=4))

        # --- Mode card ---
        mode_card = _card(ft.Column([
            ft.Text("MODE", weight=ft.FontWeight.BOLD, size=13),
            self.mode_selector,
        ], spacing=4))

        # --- Settings card ---
        settings_card = _card(ft.Row([
            ft.Text("SETTINGS", weight=ft.FontWeight.BOLD, size=13),
            self.btn_settings,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        # --- Log card ---
        log_card = _card(ft.Column([
            ft.Text("SYSTEM LOG", weight=ft.FontWeight.BOLD, size=13),
            self.log_list,
        ], spacing=4), expand=True)

        # --- Dashboard (right column) ---
        dashboard = ft.Column([
            telemetry_card,
            radar_card,
            status_card,
            controls_card,
            mode_card,
            settings_card,
        ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)

        # --- Main layout ---
        main_row = ft.Row([
            ft.Container(content=video_card, expand=3),
            ft.Container(content=dashboard, expand=1),
        ], expand=True, spacing=8)

        self.page.add(
            ft.Column([
                ft.Container(content=main_row, expand=True),
                log_card,
            ], expand=True, spacing=8),
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
    # Public API
    # ===================================================================
    def update_telemetry(self, mount_az: float, dome_az: float) -> None:
        """Update the telemetry readouts on the dashboard.

        Thread-safe: calls ``page.update()`` after modifying text values.

        Args:
            mount_az: Current mount azimuth in degrees.
            dome_az:  Current dome azimuth in degrees.
        """
        error = mount_az - dome_az
        self.lbl_mount_az.value = f"{mount_az:06.1f}°"
        self.lbl_dome_az.value = f"{dome_az:06.1f}°"
        self.lbl_error.value = f"{error:+06.1f}°"
        self.draw_radar(mount_az, dome_az)
        try:
            self.page.update()
        except Exception:
            pass

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
        try:
            self.page.update()
        except Exception:
            pass

    # Backward-compatible alias used by ArgusController
    set_indicator = set_status


# -----------------------------------------------------------------------
# Direct execution (standalone preview)
# -----------------------------------------------------------------------
def _standalone_main(page: ft.Page):
    page.title = "ARGUS – Dome Control"
    page.bgcolor = COLOR_BG
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1280
    page.window.height = 720
    ArgusGUI(page)


if __name__ == "__main__":
    ft.app(target=_standalone_main)
