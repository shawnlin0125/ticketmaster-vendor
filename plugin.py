"""TicketMaster Plugin — ticket vendor integration.

This is a reference implementation showing the complete plugin structure:
  - plugin.py      ← implements Plugin ABC (hub) + VendorProxy ABC (business)
  - mock/          ← fake API server for isolated testing
  - fixtures/      ← test data files
  - schema/        ← DB migrations (PostgreSQL schema)
  - tests/         ← self-tests (run against mock, not real API)

Architecture:
  - plugin-hub SDK:     lifecycle (start/stop/health)
  - business API SDK:   domain methods (search/orders/inventory)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from platform_plugin_sdk import Plugin, HealthStatus, TestReport, TestResult, Fixture
from unified_ticket_api import (
    VendorProxy,
    SearchRequest,
    SearchResponse,
    CreateOrderRequest,
    OrderResponse,
    InventoryRequest,
    InventoryResponse,
    EventItem,
    OrderStatus,
)

_HERE = Path(__file__).parent


class TicketmasterPlugin(Plugin, VendorProxy):
    """TicketMaster ticket vendor integration.

    Inherits from:
      - Plugin (platform_plugin_sdk)  → lifecycle: start/stop/health
      - VendorProxy (unified_ticket_api) → business: search/orders/inventory
    """

    plugin_id = "ticketmaster"
    plugin_name = "TicketMaster"
    version = "0.1.0"

    def __init__(self):
        self._started = False
        self._api_base = "https://api.ticketmaster.com"  # real API
        self._api_key = ""

    # ═══════════════════════════════════════════════════════════
    # Lifecycle (plugin-hub SDK: Plugin ABC)
    # ═══════════════════════════════════════════════════════════

    async def start(self) -> None:
        """Start the plugin: connect to real API, begin scheduler."""
        self._api_key = self._load_api_key()
        self._started = True
        print(f"[ticketmaster] Started (API: {self._api_base})")

    async def stop(self) -> None:
        """Stop the plugin: disconnect, stop scheduler."""
        self._started = False
        print("[ticketmaster] Stopped")

    async def health(self) -> HealthStatus:
        """Check if the real API is reachable."""
        if not self._started:
            return HealthStatus(healthy=False, latency_ms=0, message="not started")

        start = time.monotonic()
        try:
            await self._ping()
            latency = (time.monotonic() - start) * 1000
            return HealthStatus(healthy=True, latency_ms=latency, message="OK")
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return HealthStatus(healthy=False, latency_ms=latency, message=str(e))

    # ═══════════════════════════════════════════════════════════
    # Business API (unified-ticket-api SDK: VendorProxy ABC)
    # ═══════════════════════════════════════════════════════════

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Query events from TicketMaster and return unified format.

        GET /api/v1/ticketmaster/search?keyword=...
        """
        raw = await self._call_api("GET", "/events", params={
            "keyword": request.keyword,
            "page": request.page,
            "page_size": request.page_size,
        })
        items = [self._transform_event(e) for e in raw.get("events", [])]
        return SearchResponse(
            items=items,
            total=raw.get("total", 0),
            page=request.page,
            page_size=request.page_size,
        )

    async def create_order(self, request: CreateOrderRequest) -> OrderResponse:
        """Create an order via TicketMaster API.

        POST /api/v1/ticketmaster/orders
        """
        payload = {
            "event_id": request.event_id,
            "seat_category": request.seat_category,
            "quantity": request.quantity,
            "customer_name": request.customer.name,
            "customer_email": request.customer.email,
            "idempotency_key": request.idempotency_key,
        }
        raw = await self._call_api("POST", "/orders", json_data=payload)
        return OrderResponse(
            order_id=f"ord_{request.idempotency_key}",
            vendor_order_id=raw.get("order_id", ""),
            status=OrderStatus.PENDING,
            created_at=raw.get("created_at"),
            expires_at=raw.get("expires_at"),
        )

    async def get_order(self, order_id: str) -> OrderResponse:
        """Query order status from TicketMaster.

        GET /api/v1/ticketmaster/orders/{order_id}
        """
        raw = await self._call_api("GET", f"/orders/{order_id}")
        return self._transform_order(raw)

    async def poll_order(self, order_id: str) -> OrderResponse:
        """Poll order status from TicketMaster (same as get_order).

        GET /api/v1/ticketmaster/orders/{order_id}/poll
        """
        return await self.get_order(order_id)

    async def check_inventory(self, request: InventoryRequest) -> InventoryResponse:
        """Check ticket inventory from TicketMaster.

        GET /api/v1/ticketmaster/inventory?event_id=...
        """
        raw = await self._call_api("GET", f"/events/{request.event_id}/inventory")
        from unified_ticket_api import InventorySeatCategory
        seats = [
            InventorySeatCategory(
                id=s.get("id", ""),
                name=s.get("name", ""),
                available=s.get("available", 0),
                total=s.get("total", 0),
            )
            for s in raw.get("seat_categories", [])
        ]
        return InventoryResponse(
            event_id=request.event_id,
            updated_at=raw.get("updated_at", ""),
            seat_categories=seats,
        )

    # ═══════════════════════════════════════════════════════════
    # Data Isolation
    # ═══════════════════════════════════════════════════════════

    @property
    def db_schema(self) -> str:
        return "plugin_ticketmaster"

    @property
    def redis_prefix(self) -> str:
        return "plugin:ticketmaster:"

    @property
    def kafka_topic_prefix(self) -> str:
        return "plugin.ticketmaster."

    # ═══════════════════════════════════════════════════════════
    # Testing Support
    # ═══════════════════════════════════════════════════════════

    def get_mock_server(self):
        """Return a mock TicketMaster API server (downstream: external vendor)."""
        from mock.vendor.server import TicketmasterMockServer

        fixtures_dir = _HERE / "fixtures"
        return TicketmasterMockServer(fixtures_dir)

    def get_business_mock_server(self):
        """Return a mock business system client (upstream: calls unified API).

        This simulates the 業務系統 making requests to the proxy's
        unified API endpoints (search, orders, inventory).
        """
        from mock.business.server import BusinessMockClient

        return BusinessMockClient

    def get_fixtures(self) -> list[Fixture]:
        """List all test fixtures."""
        fixtures_dir = _HERE / "fixtures"
        result = []
        for f in sorted(fixtures_dir.glob("*.json")):
            data = json.loads(f.read_text())
            result.append(Fixture(
                name=f.stem,
                description=data.get("_description", f.stem),
                data=data,
            ))
        return result

    async def run_tests(self, mock_port: int) -> TestReport:
        """Run self-tests against mock server."""
        import asyncio
        import importlib

        self._api_base = f"http://127.0.0.1:{mock_port}"

        results: list[TestResult] = []
        test_files = sorted((_HERE / "tests").glob("test_*.py"))

        for tf in test_files:
            module_name = f"tests.{tf.stem}"
            try:
                mod = importlib.import_module(module_name)
                for name in dir(mod):
                    if name.startswith("test_"):
                        fn = getattr(mod, name)
                        if callable(fn):
                            start = time.monotonic()
                            try:
                                if asyncio.iscoroutinefunction(fn):
                                    await fn(self)
                                else:
                                    fn(self)
                                elapsed = (time.monotonic() - start) * 1000
                                results.append(TestResult(name=name, passed=True, duration_ms=elapsed))
                            except Exception as e:
                                elapsed = (time.monotonic() - start) * 1000
                                results.append(TestResult(name=name, passed=False, duration_ms=elapsed, error=str(e)))
            except Exception as e:
                results.append(TestResult(name=tf.stem, passed=False, duration_ms=0, error=str(e)))

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        return TestReport(
            plugin_id=self.plugin_id,
            plugin_version=self.version,
            passed=(passed == total and total > 0),
            total=total,
            passed_count=passed,
            results=results,
        )

    # ═══════════════════════════════════════════════════════════
    # Internal Helpers
    # ═══════════════════════════════════════════════════════════

    def _load_api_key(self) -> str:
        import os
        return os.environ.get("TICKETMASTER_API_KEY", "")

    async def _ping(self) -> None:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._api_base}/ping",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"API returned {resp.status}")

    async def _call_api(self, method: str, path: str,
                        params: dict = None, json_data: dict = None) -> dict:
        """Call the TicketMaster API and return JSON response."""
        import aiohttp
        url = f"{self._api_base}{path}"
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return await resp.json()
            elif method == "POST":
                async with session.post(
                    url, json=json_data,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    return await resp.json()
            else:
                raise ValueError(f"Unsupported method: {method}")

    def _transform_event(self, raw: dict) -> EventItem:
        """Convert TicketMaster event format → unified EventItem."""
        from unified_ticket_api import SeatCategory, PriceRange
        seats = [
            SeatCategory(id=s["id"], name=s["name"], price=s["price"])
            for s in raw.get("seat_categories", [])
        ]
        prices = [s.price for s in seats]
        return EventItem(
            id=raw.get("id", ""),
            vendor_event_id=raw.get("id", ""),
            name=raw.get("name", ""),
            category=raw.get("category", ""),
            venue=raw.get("venue", ""),
            date=raw.get("date", ""),
            status=raw.get("status", "on_sale"),
            price_range=PriceRange(
                min=min(prices) if prices else 0,
                max=max(prices) if prices else 0,
            ),
            seat_categories=seats,
        )

    def _transform_order(self, raw: dict) -> OrderResponse:
        """Convert TicketMaster order format → unified OrderResponse."""
        from unified_ticket_api import Ticket
        tickets = [
            Ticket(ticket_no=t.get("ticket_no", ""), barcode=t.get("barcode", ""))
            for t in raw.get("tickets", [])
        ]
        status_map = {
            "PENDING": OrderStatus.PENDING,
            "CONFIRMED": OrderStatus.CONFIRMED,
            "FAILED": OrderStatus.FAILED,
            "EXPIRED": OrderStatus.EXPIRED,
        }
        return OrderResponse(
            order_id=raw.get("order_id", ""),
            vendor_order_id=raw.get("vendor_order_id", ""),
            status=status_map.get(raw.get("status", ""), OrderStatus.PENDING),
            event_name=raw.get("event_name"),
            seat_category=raw.get("seat_category"),
            quantity=raw.get("quantity"),
            total_amount=raw.get("total_amount"),
            created_at=raw.get("created_at"),
            confirmed_at=raw.get("confirmed_at"),
            tickets=tickets,
        )
