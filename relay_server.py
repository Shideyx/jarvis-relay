# relay_server.py — Jarvis Relay Server
# Deploy on Render/Railway — bridges PC and mobile app
import asyncio
import json
import os
import websockets

_pc = None  # PC connection
_phones = set()  # Mobile connections

async def handler(websocket):
    global _pc
    
    # First message identifies the client
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
        try:
            async for raw in websocket:
                # Forward phone messages to PC
                if _pc:
                    try:
                        await _pc.send(raw)
                    except Exception:
                        pass
                else:
                    await websocket.send(json.dumps({
                        "type": "error", 
                        "msg": "PC not connected"
                    }))
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
