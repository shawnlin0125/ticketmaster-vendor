"""Mock TicketMaster API server for isolated testing.

Simulates the TicketMaster API using fixtures data.
No real external calls — 100% deterministic.
"""

import json
from pathlib import Path
from aiohttp import web


class TicketmasterMockServer:
    """Fake TicketMaster API that serves fixture data."""

    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir
        self.fixtures = self._load_all_fixtures()
        self.app = web.Application()
        self._setup_routes()
        self._runner = None

    def _load_all_fixtures(self) -> dict:
        """Load all JSON fixtures into memory."""
        data = {}
        for f in sorted(self.fixtures_dir.glob("*.json")):
            data[f.stem] = json.loads(f.read_text())
        return data

    def _setup_routes(self):
        """Define fake API endpoints."""
        self.app.router.add_get("/ping", self._ping)
        self.app.router.add_get("/events", self._list_events)
        self.app.router.add_get("/events/{event_id}", self._get_event)
        self.app.router.add_get("/events/{event_id}/tickets", self._list_tickets)

    # ── Handlers ──────────────────────────────────────────────

    async def _ping(self, request):
        return web.json_response({"status": "ok"})

    async def _list_events(self, request):
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 50))
        all_events = self.fixtures.get("events", {}).get("events", [])
        start = (page - 1) * page_size
        return web.json_response({
            "events": all_events[start:start + page_size],
            "total": len(all_events),
            "page": page,
        })

    async def _get_event(self, request):
        event_id = request.match_info["event_id"]
        all_events = self.fixtures.get("events", {}).get("events", [])
        for e in all_events:
            if e.get("id") == event_id:
                return web.json_response(e)
        raise web.HTTPNotFound(text=json.dumps({"error": "event not found"}))

    async def _list_tickets(self, request):
        event_id = request.match_info["event_id"]
        all_tickets = self.fixtures.get("tickets", {}).get("tickets", [])
        event_tickets = [t for t in all_tickets if t.get("event_id") == event_id]
        return web.json_response({"tickets": event_tickets})

    # ── Lifecycle ─────────────────────────────────────────────

    async def start(self, port: int = 0) -> int:
        """Start mock server. port=0 → random available port."""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", port)
        await site.start()
        actual_port = site._server.sockets[0].getsockname()[1]
        return actual_port

    async def stop(self):
        """Stop mock server."""
        if self._runner:
            await self._runner.cleanup()
