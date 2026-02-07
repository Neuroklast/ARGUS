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

# NASA Day theme – inspired by NASA Mission Control / JPL aesthetics
# Clean white/light-grey background with navy-blue accents
THEME_DAY = {
    "bg": "#F0F2F5",
    "card_bg": "#FFFFFF",
    "accent": "#0B3D91",        # NASA blue
    "error_readout": "#DD361C", # NASA red
    "stop_btn": "#DD361C",
    "off": "#C8CDD3",
    "on": "#2ECC71",
    "moving": "#E8A317",
    "no_signal": "#9EA7B0",
    "text": "#1A1A2E",
    "heading": "#0B3D91",
    "border": "#D0D5DD",
    "radar_circle": "#B0B8C4",
    "radar_mount": "#DD361C",
    "radar_dome": "#0B3D91",
    "banner_warn_bg": "#FFF3CD",
    "banner_warn_fg": "#664D03",
    "banner_crit_bg": "#DD361C",
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

# Radar constants – larger for detail
_RADAR_SIZE = 200
_RADAR_CX = _RADAR_SIZE / 2
_RADAR_CY = _RADAR_SIZE / 2
_RADAR_R = 80


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
        auto_mount: If ``True`` (default), the layout is immediately added
            to the page.  Pass ``False`` when a splash screen is active
            and call :meth:`mount` explicitly after removing it.
    """

    def __init__(self, page: ft.Page, auto_mount: bool = True):
        self.page = page
        self._theme = dict(THEME_DARK)
        self._night_mode = False
        self._theme_cycle_index = 0  # 0=dark, 1=day, 2=night
        self._slit_open = False

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

        # Extended telemetry labels
        self.lbl_mount_alt = ft.Text(
            "---.-°", size=14, font_family="RobotoMono",
            color=self._theme["accent"],
        )
        self.lbl_sidereal = ft.Text(
            "--:--:--", size=14, font_family="RobotoMono",
            color=self._theme["accent"],
        )
        self.lbl_tracking_rate = ft.Text(
            "---", size=14, font_family="RobotoMono",
            color=self._theme["accent"],
        )
        self.lbl_pier_side = ft.Text(
            "---", size=14, font_family="RobotoMono",
            color=self._theme["accent"],
        )

        # Slit status indicator
        self.slit_indicator = ft.Container(
            width=36, height=16, bgcolor=COLOR_OFF, border_radius=6,
        )
        self.hint_slit = ft.Text(
            t("gui.slit_closed"), size=10, color=COLOR_NO_SIGNAL, italic=True,
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

        # Radar canvas (larger for detail)
        self.radar_canvas = cv.Canvas(
            width=_RADAR_SIZE, height=_RADAR_SIZE,
            shapes=self._radar_shapes(0.0, 0.0),
        )

        # Log list
        self.log_list = ft.ListView(
            height=60, spacing=2, auto_scroll=True,
        )

        # Control buttons with labels (callbacks set later by the controller)
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

        # Simulation controls (telescope azimuth / altitude sliders)
        self.sim_az_slider = ft.Slider(
            min=0, max=360, value=180, divisions=360, label="{value}°",
        )
        self.sim_alt_slider = ft.Slider(
            min=0, max=90, value=45, divisions=90, label="{value}°",
        )
        self.btn_sim_slit = ft.Button(
            content=ft.Text(t("gui.open_slit")),
            icon=ft.Icons.OPEN_IN_BROWSER,
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

        # Theme cycle button (dark → day → night → dark)
        self.btn_night_mode = ft.IconButton(
            icon=ft.Icons.NIGHTLIGHT_ROUND,
            tooltip=t("gui.toggle_night"),
            icon_size=24,
            on_click=lambda e: self.toggle_night_mode(),
        )

        # Help button (toolbar)
        self.btn_help = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            tooltip=t("gui.help_tooltip"),
            icon_size=24,
        )

        # Wizard button (toolbar)
        self.btn_wizard = ft.IconButton(
            icon=ft.Icons.AUTO_FIX_HIGH,
            tooltip=t("gui.setup_wizard"),
            icon_size=24,
        )

        # -- Build layout ------------------------------------------------
        self._build_layout()
        if auto_mount:
            self.mount()

    # ===================================================================
    # Layout
    # ===================================================================
    def _build_layout(self):
        """Assemble the full dashboard layout (does NOT add to page)."""

        # Lists to track theme-dependent text elements for theme switching
        self._heading_labels: list[ft.Text] = []
        self._text_labels: list[ft.Text] = []

        def _heading(key: str) -> ft.Text:
            lbl = ft.Text(t(key), weight=ft.FontWeight.BOLD, size=11,
                          color=self._theme["heading"])
            self._heading_labels.append(lbl)
            return lbl

        def _text(key: str, **kwargs) -> ft.Text:
            lbl = ft.Text(t(key), color=self._theme["text"], **kwargs)
            self._text_labels.append(lbl)
            return lbl

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

        # --- Telemetry card (extended) ---
        telemetry_card = _card(ft.Column([
            _heading("gui.telemetry"),
            ft.Row([_text("gui.mount_az", size=11), self.lbl_mount_az],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([_text("gui.dome_az", size=11), self.lbl_dome_az],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([_text("gui.error", size=11), self.lbl_error],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, thickness=0.5),
            ft.Row([_text("gui.mount_alt", size=10),
                    self.lbl_mount_alt],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([_text("gui.sidereal_time", size=10),
                    self.lbl_sidereal],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([_text("gui.tracking_rate", size=10),
                    self.lbl_tracking_rate],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([_text("gui.pier_side", size=10),
                    self.lbl_pier_side],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=2))

        # --- Radar card (compact) with vertical telescope angle ---
        # Accent-colored readouts updated via toggle_night_mode() directly
        self.lbl_telescope_alt_radar = ft.Text(
            "ALT ---.-°", size=10, font_family="RobotoMono",
            color=self._theme["accent"],
        )
        self.lbl_pier_side_radar = ft.Text(
            "PIER ---", size=10, font_family="RobotoMono",
            color=self._theme["accent"],
        )
        radar_card = _card(ft.Column([
            _heading("gui.dome_position"),
            ft.Container(
                content=self.radar_canvas,
                alignment=ft.Alignment(0, 0),
            ),
            ft.Row([
                self.lbl_telescope_alt_radar,
                self.lbl_pier_side_radar,
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
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
            _heading("gui.connection_status"),
            ft.Row([
                _indicator_col(t("gui.telescope"), self.ind_ascom, self.hint_ascom),
                _indicator_col(t("gui.camera"), self.ind_vision, self.hint_vision),
                _indicator_col(t("gui.motor"), self.ind_motor, self.hint_motor),
                _indicator_col(t("gui.slit"), self.slit_indicator, self.hint_slit),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        ], spacing=2))

        # --- Controls card (with CCW/CW labels) ---
        self._lbl_ccw = ft.Text("CCW", size=9, text_align=ft.TextAlign.CENTER,
                                color=self._theme["text"])
        self._lbl_cw = ft.Text("CW", size=9, text_align=ft.TextAlign.CENTER,
                               color=self._theme["text"])
        self._text_labels.extend([self._lbl_ccw, self._lbl_cw])
        controls_card = _card(ft.Column([
            _heading("gui.dome_control"),
            ft.Row([
                ft.Column([self.btn_ccw, self._lbl_ccw],
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          spacing=0),
                self.btn_stop,
                ft.Column([self.btn_cw, self._lbl_cw],
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          spacing=0),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        ], spacing=2))

        # --- Mode card ---
        mode_card = _card(ft.Column([
            _heading("gui.operating_mode"),
            self.mode_selector,
        ], spacing=2))

        # --- Simulation card (telescope position sliders) ---
        self.sim_card = _card(ft.Column([
            _heading("gui.simulation"),
            ft.Row([_text("gui.sim_telescope_az", size=10),
                    self.sim_az_slider], spacing=4),
            ft.Row([_text("gui.sim_telescope_alt", size=10),
                    self.sim_alt_slider], spacing=4),
            ft.Row([self.btn_sim_slit], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=2))

        # --- Toolbar card (settings, diagnostics, theme cycle, help, wizard) ---
        toolbar_card = _card(ft.Row([
            _heading("gui.tools"),
            ft.Row([
                self.btn_wizard,
                self.btn_help,
                self.btn_night_mode,
                self.btn_diagnostics,
                self.btn_settings,
            ], spacing=0),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        # --- Log card (fixed height) ---
        self._log_card = _card(ft.Column([
            _heading("gui.system_log"),
            self.log_list,
        ], spacing=2))

        # --- Dashboard (right column) – NO scroll, all elements visible ---
        self._dashboard_cards = [
            telemetry_card, radar_card, status_card,
            controls_card, mode_card, self.sim_card, toolbar_card,
        ]
        dashboard = ft.Column(
            self._dashboard_cards,
            expand=True, spacing=6,
            scroll=ft.ScrollMode.AUTO,
        )

        # --- Main layout ---
        main_row = ft.Row([
            ft.Container(content=self.video_card, expand=2),
            ft.Container(content=dashboard, expand=1),
        ], expand=True, spacing=8)

        self._root = ft.Column([
            self.connection_banner,
            ft.Container(content=main_row, expand=True),
            ft.Container(
                content=self._log_card,
                height=100,
            ),
        ], expand=True, spacing=6)

    def mount(self) -> None:
        """Add the built layout to the page.  Safe to call only once."""
        self.page.add(self._root)

    # ===================================================================
    # Radar drawing helpers
    # ===================================================================
    @staticmethod
    def _radar_shapes(mount_az: float, dome_az: float,
                      slit_open: bool = False,
                      theme: dict | None = None) -> list:
        """Return a list of canvas shapes for the radar view.

        The radar now includes cardinal direction labels, concentric grid
        rings, a telescope line, a dome slit arc, and a slit-open indicator.
        """
        cx, cy, r = _RADAR_CX, _RADAR_CY, _RADAR_R
        shapes: list = []
        th = theme or THEME_DARK

        # 1. Concentric grid rings (30° intervals represented as rings)
        for frac in (0.33, 0.66, 1.0):
            shapes.append(cv.Circle(
                cx, cy, r * frac,
                paint=ft.Paint(color=th["radar_circle"], stroke_width=1,
                               style=ft.PaintingStyle.STROKE),
            ))

        # 2. Cross-hair lines (N-S, E-W)
        shapes.append(cv.Line(
            cx, cy - r - 6, cx, cy + r + 6,
            paint=ft.Paint(color=th["radar_circle"], stroke_width=0.5,
                           style=ft.PaintingStyle.STROKE),
        ))
        shapes.append(cv.Line(
            cx - r - 6, cy, cx + r + 6, cy,
            paint=ft.Paint(color=th["radar_circle"], stroke_width=0.5,
                           style=ft.PaintingStyle.STROKE),
        ))

        # 3. Cardinal direction labels
        label_offset = r + 14
        for label_text, angle_deg in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            angle_rad = math.radians(angle_deg - 90)
            lx = cx + label_offset * math.cos(angle_rad) - 4
            ly = cy + label_offset * math.sin(angle_rad) + 4
            shapes.append(cv.Text(
                lx, ly, label_text,
                style=ft.TextStyle(size=10, color=th["text"],
                                   weight=ft.FontWeight.BOLD),
            ))

        # 4. Dome outline (thick outer circle)
        shapes.append(cv.Circle(
            cx, cy, r,
            paint=ft.Paint(color=th["radar_dome"], stroke_width=2.5,
                           style=ft.PaintingStyle.STROKE),
        ))

        # 5. Red line for mount azimuth (telescope pointing direction)
        angle_rad = math.radians(mount_az - 90)
        arrow_len = r - 6
        ax = cx + arrow_len * math.cos(angle_rad)
        ay = cy + arrow_len * math.sin(angle_rad)
        shapes.append(cv.Line(
            cx, cy, ax, ay,
            paint=ft.Paint(color=th["radar_mount"], stroke_width=3,
                           style=ft.PaintingStyle.STROKE),
        ))
        # Arrowhead dot
        shapes.append(cv.Circle(
            ax, ay, 4,
            paint=ft.Paint(color=th["radar_mount"],
                           style=ft.PaintingStyle.FILL),
        ))

        # 6. Dome slit arc (~20° wide)
        arc_half_deg = 10
        start_deg = dome_az - 90 - arc_half_deg
        sweep_deg = 2 * arc_half_deg
        slit_color = th["on"] if slit_open else th["moving"]
        shapes.append(cv.Arc(
            cx - r, cy - r, 2 * r, 2 * r,
            start_angle=math.radians(start_deg),
            sweep_angle=math.radians(sweep_deg),
            paint=ft.Paint(color=slit_color, stroke_width=6,
                           style=ft.PaintingStyle.STROKE),
        ))

        # 7. Pier marker at centre
        shapes.append(cv.Circle(
            cx, cy, 3,
            paint=ft.Paint(color=th["text"],
                           style=ft.PaintingStyle.FILL),
        ))

        return shapes

    def draw_radar(self, mount_az: float, dome_az: float) -> None:
        """Redraw the radar view showing mount and dome positions.

        Args:
            mount_az: Current mount azimuth in degrees.
            dome_az:  Current dome slit azimuth in degrees.
        """
        self.radar_canvas.shapes = self._radar_shapes(
            mount_az, dome_az, slit_open=self._slit_open, theme=self._theme,
        )

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
        # No page.update() here – caller uses batch_update() to coalesce

    # ===================================================================
    # Theme cycling (dark → day → night → dark)
    # ===================================================================
    def toggle_night_mode(self) -> None:
        """Cycle through Dark → NASA Day → Night-Vision themes."""
        themes = [THEME_DARK, THEME_DAY, THEME_NIGHT]
        icons = [ft.Icons.BRIGHTNESS_2, ft.Icons.NIGHTLIGHT_ROUND,
                 ft.Icons.BRIGHTNESS_7]
        self._theme_cycle_index = (self._theme_cycle_index + 1) % len(themes)
        self._theme = dict(themes[self._theme_cycle_index])
        self._night_mode = self._theme_cycle_index == 2

        # Update page background
        self.page.bgcolor = self._theme["bg"]
        if self._theme_cycle_index == 1:
            self.page.theme_mode = ft.ThemeMode.LIGHT
        else:
            self.page.theme_mode = ft.ThemeMode.DARK

        # Update accent colours on telemetry labels
        self.lbl_mount_az.color = self._theme["accent"]
        self.lbl_dome_az.color = self._theme["accent"]
        self.lbl_error.color = self._theme["error_readout"]
        for lbl in (self.lbl_mount_alt, self.lbl_sidereal,
                    self.lbl_tracking_rate, self.lbl_pier_side):
            lbl.color = self._theme["accent"]

        # Update radar altitude / pier side labels
        self.lbl_telescope_alt_radar.color = self._theme["accent"]
        self.lbl_pier_side_radar.color = self._theme["accent"]

        # Update all heading labels (section titles)
        for lbl in self._heading_labels:
            lbl.color = self._theme["heading"]

        # Update all text labels (body text)
        for lbl in self._text_labels:
            lbl.color = self._theme["text"]

        # Update all card backgrounds and borders
        for card in self._dashboard_cards:
            card.bgcolor = self._theme["card_bg"]
            if self._night_mode or self._theme_cycle_index == 1:
                card.border = ft.Border.all(1, self._theme["border"])
            else:
                card.border = None
        # Also update video card and log card
        if hasattr(self, 'video_card'):
            self.video_card.bgcolor = self._theme["card_bg"]
            if self._night_mode or self._theme_cycle_index == 1:
                self.video_card.border = ft.Border.all(1, self._theme["border"])
            else:
                self.video_card.border = None
        if hasattr(self, '_log_card'):
            self._log_card.bgcolor = self._theme["card_bg"]
            if self._night_mode or self._theme_cycle_index == 1:
                self._log_card.border = ft.Border.all(1, self._theme["border"])
            else:
                self._log_card.border = None

        # Update toolbar icon colours
        self.btn_night_mode.icon = icons[self._theme_cycle_index]
        self.btn_night_mode.icon_color = self._theme["accent"]
        self.btn_help.icon_color = self._theme["accent"]
        self.btn_wizard.icon_color = self._theme["accent"]
        self.btn_diagnostics.icon_color = self._theme["accent"]
        self.btn_settings.icon_color = self._theme["accent"]

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

    def update_telemetry(self, mount_az: float, dome_az: float,
                         mount_alt: float | None = None,
                         sidereal_time: str | None = None,
                         tracking_rate: str | None = None,
                         pier_side: str | None = None) -> None:
        """Update the telemetry readouts on the dashboard.

        Thread-safe: modifies text values; caller should use batch_update().

        Args:
            mount_az: Current mount azimuth in degrees.
            dome_az:  Current dome azimuth in degrees.
            mount_alt: Optional mount altitude in degrees.
            sidereal_time: Optional local sidereal time string.
            tracking_rate: Optional tracking rate description.
            pier_side: Optional pier side (East/West).
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

        # Extended telemetry
        if mount_alt is not None:
            self.lbl_mount_alt.value = f"{mount_alt:05.1f}°"
            self.lbl_telescope_alt_radar.value = f"ALT {mount_alt:05.1f}°"
        if sidereal_time is not None:
            self.lbl_sidereal.value = sidereal_time
        if tracking_rate is not None:
            self.lbl_tracking_rate.value = tracking_rate
        if pier_side is not None:
            self.lbl_pier_side.value = pier_side
            self.lbl_pier_side_radar.value = f"PIER {pier_side}"

        self.draw_radar(mount_az, dome_az)

    def set_slit_status(self, is_open: bool) -> None:
        """Update the slit open/closed status indicator.

        Args:
            is_open: ``True`` when the dome slit is open.
        """
        self._slit_open = is_open
        self.slit_indicator.bgcolor = COLOR_ON if is_open else COLOR_OFF
        self.hint_slit.value = (
            t("gui.slit_open") if is_open else t("gui.slit_closed")
        )

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

        When *dlg* is provided (from :meth:`show_diagnostics_loading`),
        the loading content is replaced in-place so the dialog transitions
        seamlessly without closing and re-opening.

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

        th = self._theme

        rows: list = []
        for r in report.results:
            icon_char, icon_color = _STATUS_ICONS.get(
                r.status, ("?", "#888888")
            )
            parts = [
                ft.Text(icon_char, color=icon_color, size=14,
                        weight=ft.FontWeight.BOLD),
                ft.Text(f"[{r.category}] {r.name}", size=12,
                        weight=ft.FontWeight.BOLD,
                        color=th["heading"]),
                ft.Text(r.message, size=11, color=th["text"]),
            ]
            if r.suggestion:
                parts.append(ft.Text(
                    f"💡 {r.suggestion}", size=10, italic=True,
                    color=th["accent"],
                ))
            rows.append(ft.Container(
                content=ft.Column(parts, spacing=2),
                padding=6,
                border=ft.Border(
                    bottom=ft.BorderSide(1, th["border"]),
                ),
            ))

        # Troubleshooting tips for errors
        if report.errors:
            rows.append(ft.Container(
                content=ft.Column([
                    ft.Text(t("diag.tips_title"), size=12,
                            weight=ft.FontWeight.BOLD, color=th["accent"]),
                    ft.Text(t("diag.tips_body"), size=10, color=th["text"]),
                ], spacing=4),
                padding=8,
            ))

        # Summary header
        header = ft.Text(
            f"{t('gui.diagnostics_title')}: {report.summary}  "
            f"({report.duration_s}s)",
            size=13, weight=ft.FontWeight.BOLD,
            color=th["heading"],
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
            # Replace loading content in-place (seamless transition)
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

    # ===================================================================
    # Help dialog
    # ===================================================================
    def show_help_dialog(self) -> None:
        """Display a help dialog with quick-start instructions."""
        sections = [
            (t("help.quick_start_title"), t("help.quick_start_body")),
            (t("help.modes_title"), t("help.modes_body")),
            (t("help.troubleshooting_title"), t("help.troubleshooting_body")),
        ]
        rows: list = []
        for title, body in sections:
            rows.append(ft.Container(
                content=ft.Column([
                    ft.Text(title, size=13, weight=ft.FontWeight.BOLD,
                            color=self._theme["accent"]),
                    ft.Text(body, size=11, color=self._theme["text"]),
                ], spacing=4),
                padding=6,
                border=ft.Border(
                    bottom=ft.BorderSide(1, self._theme["border"]),
                ),
            ))

        dlg = ft.AlertDialog(
            title=ft.Text(t("help.title")),
            content=ft.Container(
                content=ft.Column(rows, scroll=ft.ScrollMode.AUTO, spacing=4),
                width=520,
                height=380,
            ),
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

    # ===================================================================
    # Setup wizard dialog
    # ===================================================================
    def show_setup_wizard(self, config: dict,
                          on_save_callback=None) -> None:
        """Display a step-by-step setup wizard for first-time configuration.

        Args:
            config: Current configuration dictionary.
            on_save_callback: Called with the updated config dict on save.
        """
        steps = [
            {
                "key": "location",
                "title": t("wizard.step_location_title"),
                "help": t("wizard.step_location_help"),
                "fields": [],
            },
            {
                "key": "hardware",
                "title": t("wizard.step_hardware_title"),
                "help": t("wizard.step_hardware_help"),
                "fields": [],
            },
            {
                "key": "dome",
                "title": t("wizard.step_dome_title"),
                "help": t("wizard.step_dome_help"),
                "fields": [],
            },
            {
                "key": "finish",
                "title": t("wizard.step_finish_title"),
                "help": t("wizard.step_finish_help"),
                "fields": [],
            },
        ]

        obs = config.get("math", {}).get("observatory", {})
        hw = config.get("hardware", {})
        dome = config.get("math", {}).get("dome", {})

        # Step 1: Location
        tf_lat = ft.TextField(label=t("settings.latitude"),
                              value=str(obs.get("latitude", 0.0)))
        tf_lon = ft.TextField(label=t("settings.longitude"),
                              value=str(obs.get("longitude", 0.0)))
        tf_elev = ft.TextField(label=t("settings.elevation"),
                               value=str(obs.get("elevation", 0)))
        steps[0]["fields"] = [tf_lat, tf_lon, tf_elev]

        # Step 2: Hardware
        tf_port = ft.TextField(label=t("settings.serial_port"),
                               value=str(hw.get("serial_port", "COM3")))
        tf_baud = ft.TextField(label=t("settings.baud_rate"),
                               value=str(hw.get("baud_rate", 9600)))
        steps[1]["fields"] = [tf_port, tf_baud]

        # Step 3: Dome geometry
        tf_radius = ft.TextField(label=t("settings.dome_radius"),
                                 value=str(dome.get("radius", 2.5)))
        tf_slit_w = ft.TextField(label=t("settings.slit_width"),
                                 value=str(dome.get("slit_width", 0.8)))
        # Rotation limits
        dome_cfg = config.get("dome", {})
        tf_az_min = ft.TextField(
            label=t("settings.az_min"),
            value=str(dome_cfg.get("az_min", 0.0)),
        )
        tf_az_max = ft.TextField(
            label=t("settings.az_max"),
            value=str(dome_cfg.get("az_max", 360.0)),
        )
        steps[2]["fields"] = [tf_radius, tf_slit_w, tf_az_min, tf_az_max]

        current_step = [0]

        step_title = ft.Text(steps[0]["title"], size=16,
                             weight=ft.FontWeight.BOLD,
                             color=self._theme["accent"])
        step_help = ft.Text(steps[0]["help"], size=11,
                            color=self._theme["text"])
        step_body = ft.Column(steps[0]["fields"], spacing=8)
        step_indicator = ft.Text(
            f"1 / {len(steps)}", size=11, color=self._theme["text"],
        )

        def _update_step():
            idx = current_step[0]
            s = steps[idx]
            step_title.value = s["title"]
            step_help.value = s["help"]
            step_body.controls = s["fields"]
            step_indicator.value = f"{idx + 1} / {len(steps)}"
            btn_back.visible = idx > 0
            btn_next.text = (t("wizard.finish")
                             if idx == len(steps) - 1 else t("wizard.next"))
            try:
                self.page.update()
            except Exception:
                pass

        def _on_next(e):
            if current_step[0] < len(steps) - 1:
                current_step[0] += 1
                _update_step()
            else:
                # Finish – save values
                _save_wizard()

        def _on_back(e):
            if current_step[0] > 0:
                current_step[0] -= 1
                _update_step()

        def _to_float(val, default):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def _to_int(val, default):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def _save_wizard():
            config.setdefault("math", {}).setdefault("observatory", {})
            config["math"]["observatory"]["latitude"] = _to_float(
                tf_lat.value, 0.0)
            config["math"]["observatory"]["longitude"] = _to_float(
                tf_lon.value, 0.0)
            config["math"]["observatory"]["elevation"] = _to_float(
                tf_elev.value, 0.0)

            config.setdefault("hardware", {})
            config["hardware"]["serial_port"] = tf_port.value
            config["hardware"]["baud_rate"] = _to_int(tf_baud.value, 9600)

            config.setdefault("math", {}).setdefault("dome", {})
            config["math"]["dome"]["radius"] = _to_float(
                tf_radius.value, 2.5)
            config["math"]["dome"]["slit_width"] = _to_float(
                tf_slit_w.value, 0.8)

            config.setdefault("dome", {})
            config["dome"]["az_min"] = _to_float(tf_az_min.value, 0.0)
            config["dome"]["az_max"] = _to_float(tf_az_max.value, 360.0)

            if on_save_callback:
                on_save_callback(config)
            self._close_dialog(dlg)

        btn_back = ft.TextButton(t("wizard.back"), on_click=_on_back,
                                 visible=False)
        btn_next = ft.TextButton(t("wizard.next"), on_click=_on_next)

        content = ft.Container(
            content=ft.Column([
                step_title,
                ft.Container(
                    content=step_help,
                    padding=ft.Padding(0, 0, 0, 8),
                ),
                step_body,
            ], scroll=ft.ScrollMode.AUTO, spacing=8),
            width=480,
            height=380,
        )

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Text(t("wizard.title")),
                step_indicator,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            content=content,
            actions=[btn_back, btn_next],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.page.overlay.append(dlg)
        dlg.open = True
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
