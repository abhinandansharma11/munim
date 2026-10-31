"""Live updates: every screen keeps a WebSocket open and gets each event as it happens."""
import asyncio
import json


class Bus:
    def __init__(self):
        self.clients = set()

    async def connect(self, ws):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws):
        self.clients.discard(ws)

    async def emit(self, type_, **data):
        msg = json.dumps({"type": type_, **data}, default=str)
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


class NullBus:
    """Used by the test-set runner, which works on its own copy of the data and needs no screens."""

    async def emit(self, type_, **data):
        await asyncio.sleep(0)
