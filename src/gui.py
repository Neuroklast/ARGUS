"""
ARGUS - Advanced Rotation Guidance Using Sensors
GUI Module

Professional dark-mode interface built with customtkinter for
observatory dome control and monitoring.
"""

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Font Constants (Monospace is critical for telemetry readouts)
# ---------------------------------------------------------------------------
FONT_DATA = ("Roboto Mono", 24, "bold")
FONT_LABEL = ("Roboto Mono", 12)
FONT_BUTTON = ("Roboto Mono", 14, "bold")
FONT_SECTION = ("Roboto Mono", 13, "bold")
FONT_INDICATOR = ("Roboto Mono", 11)

# ---------------------------------------------------------------------------
# Colour Constants
# ---------------------------------------------------------------------------
COLOR_ERROR = "#FF8C00"       # Orange for error readout
COLOR_STOP_BTN = "#C0392B"    # Red for STOP button
COLOR_STOP_HOVER = "#E74C3C"
COLOR_OFF = "#555555"         # Grey – indicator off
COLOR_ON = "#2ECC71"          # Green – indicator on
COLOR_MOVING = "#F1C40F"      # Yellow – motor moving
COLOR_NO_SIGNAL = "#888888"   # Grey text for "NO SIGNAL"


class ArgusApp(ctk.CTk):
    """Main ARGUS GUI application."""

    def __init__(self):
        super().__init__()

        # -- Window setup ------------------------------------------------
        self.title("ARGUS – Dome Control")
        self.geometry("1280x720")
        self.minsize(960, 540)

        # -- Grid configuration ------------------------------------------
        self.grid_columnconfigure(0, weight=3)   # Video column
        self.grid_columnconfigure(1, weight=1)   # Controls column
        self.grid_rowconfigure(0, weight=1)

        # -- Build panels ------------------------------------------------
        self.create_video_panel()
        self.create_dashboard_panel()

    # ===================================================================
    # LEFT PANEL – Video Feed
    # ===================================================================
    def create_video_panel(self):
        """Create the left video-feed panel."""
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        self.video_label = ctk.CTkLabel(
            self.video_frame,
            text="NO SIGNAL",
            font=FONT_DATA,
            text_color=COLOR_NO_SIGNAL,
        )
        self.video_label.grid(row=0, column=0, sticky="nsew")

    # ===================================================================
    # RIGHT PANEL – Dashboard
    # ===================================================================
    def create_dashboard_panel(self):
        """Create the right dashboard panel with all control sections."""
        self.dashboard_frame = ctk.CTkFrame(self)
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.dashboard_frame.grid_columnconfigure(0, weight=1)

        # Distribute vertical space among sections
        for i in range(4):
            self.dashboard_frame.grid_rowconfigure(i, weight=1)

        self._create_telemetry_section()
        self._create_status_section()
        self._create_controls_section()
        self._create_mode_section()

    # -- A. Telemetry ---------------------------------------------------
    def _create_telemetry_section(self):
        """Section A – large monospace readouts for azimuth data."""
        frame = ctk.CTkFrame(self.dashboard_frame)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="TELEMETRY", font=FONT_SECTION).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )

        # MOUNT AZ
        ctk.CTkLabel(frame, text="MOUNT AZ", font=FONT_LABEL).grid(
            row=1, column=0, sticky="w", padx=8, pady=2
        )
        self.lbl_mount_az = ctk.CTkLabel(frame, text="---.-°", font=FONT_DATA)
        self.lbl_mount_az.grid(row=1, column=1, sticky="e", padx=8, pady=2)

        # DOME AZ
        ctk.CTkLabel(frame, text="DOME AZ", font=FONT_LABEL).grid(
            row=2, column=0, sticky="w", padx=8, pady=2
        )
        self.lbl_dome_az = ctk.CTkLabel(frame, text="---.-°", font=FONT_DATA)
        self.lbl_dome_az.grid(row=2, column=1, sticky="e", padx=8, pady=2)

        # ERROR
        ctk.CTkLabel(frame, text="ERROR", font=FONT_LABEL).grid(
            row=3, column=0, sticky="w", padx=8, pady=(2, 8)
        )
        self.lbl_error = ctk.CTkLabel(
            frame, text="---.-°", font=FONT_DATA, text_color=COLOR_ERROR
        )
        self.lbl_error.grid(row=3, column=1, sticky="e", padx=8, pady=(2, 8))

    # -- B. Status Monitor ----------------------------------------------
    def _create_status_section(self):
        """Section B – small coloured status indicators."""
        frame = ctk.CTkFrame(self.dashboard_frame)
        frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(frame, text="STATUS", font=FONT_SECTION).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4)
        )

        # Helper to build an indicator pair (label + coloured badge)
        def _indicator(parent, text, row, col):
            container = ctk.CTkFrame(parent, fg_color="transparent")
            container.grid(row=row, column=col, padx=6, pady=(2, 8))
            lbl = ctk.CTkLabel(container, text=text, font=FONT_INDICATOR)
            lbl.pack()
            badge = ctk.CTkLabel(
                container, text="  ", width=40, height=18,
                corner_radius=6, fg_color=COLOR_OFF,
            )
            badge.pack(pady=(2, 0))
            return badge

        self.ind_ascom = _indicator(frame, "ASCOM", 1, 0)
        self.ind_vision = _indicator(frame, "VISION", 1, 1)
        self.ind_motor = _indicator(frame, "MOTOR", 1, 2)

    # -- C. Manual Controls ---------------------------------------------
    def _create_controls_section(self):
        """Section C – CCW / STOP / CW buttons."""
        frame = ctk.CTkFrame(self.dashboard_frame)
        frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(frame, text="MANUAL CONTROL", font=FONT_SECTION).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4)
        )

        self.btn_ccw = ctk.CTkButton(
            frame, text="◀ CCW", font=FONT_BUTTON,
            command=self.on_btn_left_pressed,
        )
        self.btn_ccw.grid(row=1, column=0, sticky="ew", padx=6, pady=(2, 8))

        self.btn_stop = ctk.CTkButton(
            frame, text="STOP", font=FONT_BUTTON,
            fg_color=COLOR_STOP_BTN, hover_color=COLOR_STOP_HOVER,
            command=self.on_btn_stop_pressed,
        )
        self.btn_stop.grid(row=1, column=1, sticky="ew", padx=6, pady=(2, 8))

        self.btn_cw = ctk.CTkButton(
            frame, text="CW ▶", font=FONT_BUTTON,
            command=self.on_btn_right_pressed,
        )
        self.btn_cw.grid(row=1, column=2, sticky="ew", padx=6, pady=(2, 8))

    # -- D. Settings / Mode ---------------------------------------------
    def _create_mode_section(self):
        """Section D – mode selector segmented button."""
        frame = ctk.CTkFrame(self.dashboard_frame)
        frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(4, 8))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="MODE", font=FONT_SECTION).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )

        self.mode_selector = ctk.CTkSegmentedButton(
            frame,
            values=["MANUAL", "AUTO-SLAVE", "CALIBRATE"],
            font=FONT_BUTTON,
            command=self.on_mode_changed,
        )
        self.mode_selector.set("MANUAL")
        self.mode_selector.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 8))

    # ===================================================================
    # Public API
    # ===================================================================
    def update_telemetry(self, mount_az: float, dome_az: float) -> None:
        """
        Update the telemetry readouts on the dashboard.

        Args:
            mount_az: Current mount azimuth in degrees.
            dome_az:  Current dome azimuth in degrees.
        """
        error = mount_az - dome_az
        self.lbl_mount_az.configure(text=f"{mount_az:06.1f}°")
        self.lbl_dome_az.configure(text=f"{dome_az:06.1f}°")
        self.lbl_error.configure(text=f"{error:+06.1f}°")

    def set_indicator(self, name: str, active: bool) -> None:
        """
        Set the colour of a status indicator.

        Args:
            name:   One of "ascom", "vision", "motor".
            active: ``True`` to turn the indicator on.
        """
        mapping = {
            "ascom": (self.ind_ascom, COLOR_ON),
            "vision": (self.ind_vision, COLOR_ON),
            "motor": (self.ind_motor, COLOR_MOVING),
        }
        if name not in mapping:
            return
        badge, on_colour = mapping[name]
        badge.configure(fg_color=on_colour if active else COLOR_OFF)

    # ===================================================================
    # Button / Event Callbacks (Dummies)
    # ===================================================================
    def on_btn_left_pressed(self):
        """Dummy handler – rotate counter-clockwise."""
        print("Left")

    def on_btn_stop_pressed(self):
        """Dummy handler – emergency stop."""
        print("Stop")

    def on_btn_right_pressed(self):
        """Dummy handler – rotate clockwise."""
        print("Right")

    def on_mode_changed(self, value: str):
        """Dummy handler – mode selection changed."""
        print(f"Mode: {value}")


# -----------------------------------------------------------------------
# Direct execution
# -----------------------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")

    app = ArgusApp()
    app.mainloop()
