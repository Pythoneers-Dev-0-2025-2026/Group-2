# backend/app/server.py
import asyncio
import json
from websockets import serve
from system import check_lock_status 

connected_clients = set()

async def handle_client(websocket):
    connected_clients.add(websocket)
    print(f"Client connected: {websocket.remote_address}")

    try:
        while True:
            try:
                raw_msg = await websocket.recv()
            except Exception as e:
                print("Receive error:", e)
                break

            print("Received from client:", raw_msg)

            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError as e:
                print("Invalid JSON:", raw_msg, e)
                continue

            response = {
                "lock_status": check_lock_status(),
                "echo": msg 
            }

            try:
                await websocket.send(json.dumps(response))
            except Exception as e:
                print("Send error:", e)
                break

    finally:
        connected_clients.remove(websocket)
        print(f"Client disconnected: {websocket.remote_address}")


async def main():
    host = "0.0.0.0" 
    port = 12345
    print(f"Starting WebSocket server on {host}:{port}")
    async with serve(handle_client, host, port):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
