"""
ARGUS - Advanced Rotation Guidance Using Sensors
Main Application Entry Point (Controller Pattern)

Connects the GUI (ArgusApp) with a SimulationSensor so that
clicking the manual-control buttons changes the displayed dome azimuth.
"""

import threading
import time

import customtkinter as ctk

from gui import ArgusApp
from simulation_sensor import SimulationSensor


class ArgusController:
    """Controller that bridges the GUI and the (simulated) sensor."""

    def __init__(self):
        # Appearance (must be set before any widget is created)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.app = ArgusApp()
        self.sensor = SimulationSensor()
        self._running = True

        # -- Bind buttons to controller handlers -------------------------
        self.app.btn_ccw.configure(command=self.on_move_left)
        self.app.btn_stop.configure(command=self.on_stop)
        self.app.btn_cw.configure(command=self.on_move_right)

        # -- Start background control loop -------------------------------
        self._thread = threading.Thread(target=self.control_loop, daemon=True)
        self._thread.start()

    # ---- Button handlers ------------------------------------------------
    def on_move_left(self):
        """Rotate counter-clockwise."""
        self.sensor.slew_rate = -3.0

    def on_stop(self):
        """Stop rotation."""
        self.sensor.slew_rate = 0.0

    def on_move_right(self):
        """Rotate clockwise."""
        self.sensor.slew_rate = 3.0

    # ---- Background loop ------------------------------------------------
    def control_loop(self):
        """~20 FPS loop: update sensor, push telemetry to the GUI."""
        last = time.time()
        while self._running:
            now = time.time()
            dt = now - last
            last = now

            self.sensor.update(dt)
            az = self.sensor.get_azimuth()

            # Schedule the GUI update on the main thread (tkinter requirement)
            try:
                self.app.after(0, self.app.update_telemetry, 180.0, az)
            except RuntimeError:
                # mainloop not yet (or no longer) running – skip GUI update
                pass

            time.sleep(0.05)


def main():
    """Main entry point."""
    controller = ArgusController()
    controller.app.mainloop()
    controller._running = False


if __name__ == '__main__':
    main()
