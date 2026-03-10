# relay_server.py — Jarvis Relay Server
import asyncio
import json
import os
import websockets

_pc = None
_phones = set()

async def handler(websocket):
    global _pc

    try:
        raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(raw)
    except Exception:
        return

    role = data.get("role", "")

    if role == "pc":
        _pc = websocket
        print("[Relay] PC connected")
        await websocket.send(json.dumps({"type": "ok", "msg": "PC registered"}))
        try:
            async for raw in websocket:
                # Forward PC messages to all phones
                dead = set()
                for phone in list(_phones):
                    try:
                        await phone.send(raw)
                    except Exception:
                        dead.add(phone)
                _phones.difference_update(dead)
        except Exception:
            pass
        finally:
            _pc = None
            print("[Relay] PC disconnected")

    elif role == "phone":
        _phones.add(websocket)
        print(f"[Relay] Phone connected — {len(_phones)} phone(s)")
        # Send pong immediately so app shows ONLINE
        await websocket.send(json.dumps({"type": "pong"}))
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                    cmd = data.get("cmd", "")

                    # Handle ping directly
                    if cmd == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                        continue

                    # Forward everything else to PC
                    if _pc:
                        try:
                            await _pc.send(raw)
                        except Exception:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "msg": "Failed to send to PC"
                            }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "msg": "PC not connected"
                        }))
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            _phones.discard(websocket)
            print(f"[Relay] Phone disconnected — {len(_phones)} phone(s)")

async def main():
    port = int(os.environ.get("PORT", 8765))
    print(f"[Relay] Starting on port {port}")
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"[Relay] Server ready")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
