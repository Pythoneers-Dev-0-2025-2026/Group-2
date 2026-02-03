import asyncio
import json
import threading
from websockets import serve

from backend.camera.train_and_monitor import monitor_stream, LATEST_STATE
from backend.services import lock


async def main():
    def start_camera():
        monitor_stream()

    threading.Thread(target=start_camera, daemon=True).start()

    async with serve(
        lambda ws, path: handle_client(ws),
        "0.0.0.0",
        12345,
    ):
        await asyncio.Future()


async def handle_client(websocket):
    try:
        while True:
            try:
                raw_msg = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                msg = json.loads(raw_msg)
                if msg.get("type") == "COMMAND":
                    action = msg.get("payload", {}).get("action")
                    if action == "LOCK":
                        lock()
            except asyncio.TimeoutError:
                pass

            await websocket.send(json.dumps({
                "type": "STATE",
                "payload": LATEST_STATE
            }))
            await asyncio.sleep(0.2)
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
