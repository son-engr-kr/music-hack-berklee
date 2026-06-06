"""Magenta RT 2 Web UI server.

Usage:
    uv run python server.py
    # Open http://localhost:8000
"""

import json
import logging
import asyncio
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from src.engine import MRT2Engine, _NOTES_MASKED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine: MRT2Engine | None = None

app = FastAPI(title="Magenta RT 2 Live Instruments")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html", media_type="text/html")


@app.on_event("startup")
async def startup():
    global engine
    logger.info("Initializing Magenta RT 2 engine...")
    engine = MRT2Engine.get_instance()
    logger.info("Engine ready: %s", engine.model_size)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = f"session_{time.time_ns()}"
    logger.info("WebSocket connected: %s", session_id)

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            mode = msg.get("mode", "synth")
            prompt = msg.get("prompt", "synth pad")
            action = msg.get("action", "generate")

            if action == "reset":
                engine.reset_session(session_id)
                await ws.send_json({"type": "reset_ack"})
                continue

            if action == "generate":
                frames = msg.get("frames", 25)

                if mode == "synth":
                    pitch = msg.get("pitch", 60)
                    velocity = msg.get("velocity", 100)
                    notes = _NOTES_MASKED[:]
                    if pitch >= 0:
                        notes[pitch] = 3
                    drums = [-1]

                elif mode == "jam":
                    active_pitches = msg.get("notes", [60])
                    notes = _NOTES_MASKED[:]
                    for p in active_pitches:
                        notes[p] = 3
                    drums = [-1]

                elif mode == "gesture":
                    x = msg.get("x", 0.5)
                    y = msg.get("y", 0.5)
                    pitch = 36 + int(x * 60)
                    velocity = 30 + int((1.0 - y) * 97)
                    notes = _NOTES_MASKED[:]
                    notes[pitch] = 3
                    drums = [-1]

                elif mode == "looper":
                    active_pitches = msg.get("notes", [])
                    notes = _NOTES_MASKED[:]
                    for p in active_pitches:
                        notes[p] = 3
                    drums = [-1]

                else:
                    notes = _NOTES_MASKED
                    drums = [-1]

                wav_bytes = engine.generate(
                    prompt=prompt,
                    session_id=session_id,
                    notes=notes,
                    drums=drums,
                    frames=frames,
                )

                await ws.send_json({
                    "type": "audio",
                    "data": wav_bytes.hex(),
                    "sample_rate": engine.sample_rate,
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        engine.reset_session(session_id)


def main():
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
