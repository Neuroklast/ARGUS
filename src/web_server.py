"""
ARGUS Web Server
=================
FastAPI application that exposes the ARGUS dome controller over HTTP and
WebSocket.  The frontend (React + Vite, built to ``src/static/``) is served
as static files from the root endpoint.

Endpoints
---------
GET  /api/status         – current controller state as JSON
GET  /api/config         – config.yaml as JSON
POST /api/config         – update config.yaml (JSON body)
POST /api/move           – { "azimuth": 180.0 }
POST /api/stop           – immediate stop
POST /api/park           – park at 0°
POST /api/home           – homing sequence
POST /api/mode           – { "mode": "AUTO" | "MANUAL" }
POST /api/slaved         – { "slaved": true | false }
GET  /api/cameras        – list available camera indices
GET  /api/video_feed     – MJPEG stream
WS   /ws                 – WebSocket, JSON state push ~10 Hz
GET  /                   – serves web/dist/index.html via StaticFiles

Copyright (c) 2026 Kay Schäfer. All Rights Reserved.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import uvicorn
import yaml
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class MoveRequest(BaseModel):
    azimuth: float


class ModeRequest(BaseModel):
    mode: str  # "MANUAL" | "AUTO"


class SlavedRequest(BaseModel):
    slaved: bool


# ---------------------------------------------------------------------------
# Factory – creates the FastAPI app bound to a controller instance
# ---------------------------------------------------------------------------

def create_app(controller) -> FastAPI:
    """Build and return the FastAPI application.

    Args:
        controller: An :class:`~argus_controller.ArgusController` instance.

    Returns:
        Configured FastAPI application.
    """
    web_cfg = controller.config.get("web", {})
    token: str = web_cfg.get("token", "") or os.environ.get("ARGUS_TOKEN", "")

    cors_origins: list = web_cfg.get(
        "cors_origins",
        ["http://localhost:5173", "http://localhost:7373"],
    )

    app = FastAPI(title="ARGUS Web API", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    #  Optional token auth                                                #
    # ------------------------------------------------------------------ #
    def _check_token(x_api_token: Optional[str] = None) -> None:
        """Dependency: validate X-API-Token header when a token is configured."""
        if not token:
            return  # auth disabled
        from fastapi import Header
        if x_api_token != token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API token",
            )

    # ------------------------------------------------------------------ #
    #  REST endpoints                                                     #
    # ------------------------------------------------------------------ #
    @app.get("/api/status")
    async def get_status():
        return controller.get_state()

    @app.get("/api/config")
    async def get_config():
        return controller.config

    @app.post("/api/config")
    async def post_config(new_config: dict):
        from main import save_config
        controller.update_config(new_config)
        try:
            save_config(controller.config)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return {"ok": True}

    @app.post("/api/move")
    async def move(req: MoveRequest):
        await asyncio.to_thread(controller.move_dome, req.azimuth)
        return {"ok": True}

    @app.post("/api/stop")
    async def stop():
        await asyncio.to_thread(controller.stop_dome)
        return {"ok": True}

    @app.post("/api/park")
    async def park():
        await asyncio.to_thread(controller.park_dome)
        return {"ok": True}

    @app.post("/api/home")
    async def home():
        await asyncio.to_thread(controller.home_dome)
        return {"ok": True}

    @app.post("/api/mode")
    async def set_mode(req: ModeRequest):
        if req.mode not in ("MANUAL", "AUTO", "AUTO-SLAVE"):
            raise HTTPException(status_code=400, detail="Invalid mode")
        await asyncio.to_thread(controller.set_mode, req.mode)
        return {"ok": True}

    @app.post("/api/slaved")
    async def set_slaved(req: SlavedRequest):
        await asyncio.to_thread(controller.set_slaved, req.slaved)
        return {"ok": True}

    @app.get("/api/cameras")
    async def list_cameras():
        cameras = await asyncio.to_thread(_find_cameras)
        return cameras

    # ------------------------------------------------------------------ #
    #  MJPEG video feed                                                   #
    # ------------------------------------------------------------------ #
    @app.get("/api/video_feed")
    async def video_feed():
        stream_cfg = web_cfg.get("stream", {})
        jpeg_quality = stream_cfg.get("jpeg_quality", 75)
        fps = stream_cfg.get("fps", 15)

        if not stream_cfg.get("enabled", True):
            raise HTTPException(status_code=503, detail="Video stream disabled")

        return StreamingResponse(
            _mjpeg_generator(controller, jpeg_quality, fps),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    # ------------------------------------------------------------------ #
    #  WebSocket – state push ~10 Hz                                      #
    # ------------------------------------------------------------------ #
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        ctrl_cfg = controller.config.get("control", {})
        update_rate = ctrl_cfg.get("update_rate", 10)
        interval = 1.0 / max(update_rate, 1)
        try:
            while True:
                state = await asyncio.to_thread(controller.get_state)
                await ws.send_text(json.dumps(state))
                await asyncio.sleep(interval)
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("WebSocket closed: %s", exc)

    # ------------------------------------------------------------------ #
    #  Serve React frontend (static files)                                #
    # ------------------------------------------------------------------ #
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        @app.get("/")
        async def root():
            return {
                "message": "ARGUS API is running. Build the frontend with `cd web && npm run build`."
            }

    return app


# ---------------------------------------------------------------------------
# Helper: MJPEG generator
# ---------------------------------------------------------------------------

async def _mjpeg_generator(controller, jpeg_quality: int, fps: int):
    """Async generator that yields MJPEG frames from the vision system."""
    try:
        import cv2
    except ImportError:
        cv2 = None

    interval = 1.0 / max(fps, 1)

    while True:
        frame_bytes: Optional[bytes] = None

        if cv2 is not None and controller.vision is not None and controller.vision_active:
            try:
                frame = await asyncio.to_thread(controller.vision.capture_frame)
                if frame is not None:
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
                    ok, buf = cv2.imencode(".jpg", frame, encode_params)
                    if ok:
                        frame_bytes = buf.tobytes()
            except Exception as exc:
                logger.debug("MJPEG capture error: %s", exc)

        if frame_bytes is None:
            # Placeholder black frame
            if cv2 is not None:
                import numpy as np
                placeholder = np.zeros((240, 320, 3), dtype="uint8")
                ok, buf = cv2.imencode(".jpg", placeholder)
                if ok:
                    frame_bytes = buf.tobytes()

        if frame_bytes:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes
                + b"\r\n"
            )

        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Helper: enumerate available cameras
# ---------------------------------------------------------------------------

def _find_cameras() -> list:
    """Try camera indices 0–9 and return those that open successfully."""
    results = []
    try:
        import cv2
    except ImportError:
        return results

    for idx in range(10):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            results.append({"index": idx, "name": f"Camera {idx}"})
            cap.release()
    return results


# ---------------------------------------------------------------------------
# Entrypoint (called from main.py --mode web)
# ---------------------------------------------------------------------------

def run_web_server(config: dict) -> None:
    """Initialise controller and start the uvicorn server (blocking)."""
    from argus_controller import ArgusController

    controller = ArgusController(config=config)
    controller.start()

    app = create_app(controller)

    web_cfg = config.get("web", {})
    host = web_cfg.get("host", "0.0.0.0")
    port = web_cfg.get("port", 7373)

    logger.info("Starting ARGUS web server on %s:%d", host, port)
    try:
        uvicorn.run(app, host=host, port=port)
    finally:
        controller.stop_all()
