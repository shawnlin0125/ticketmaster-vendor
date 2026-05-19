"""Mock Business System — simulates the upstream business system's calls.

This mock plays the role of the 業務系統（主系統）making requests to
the proxy's unified API. The vendor is specified in the URL path.

    GET /api/v1/{vendor}/search?keyword=...
    POST /api/v1/{vendor}/orders
    ...

In tests, this is used to verify that the proxy correctly:
  - Routes by vendor in URL path
  - Accepts the unified API format
  - Translates correctly to vendor-specific API calls
  - Returns responses in the correct unified format
"""

import json
from pathlib import Path
from typing import Optional

import aiohttp

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


class BusinessMockClient:
    """Simulates the business system calling the proxy's unified API.

    Usage:
        client = BusinessMockClient(proxy_url="http://127.0.0.1:8080", vendor="ticketmaster")
        result = await client.search(keyword="Coldplay")
        # → GET http://127.0.0.1:8080/api/v1/ticketmaster/search?keyword=Coldplay
    """

    def __init__(self, proxy_base_url: str, vendor: str):
        self.base = proxy_base_url.rstrip("/")
        self.vendor = vendor

    @property
    def _api_prefix(self) -> str:
        """e.g. /api/v1/ticketmaster"""
        return f"/api/v1/{self.vendor}"

    # ── Search ─────────────────────────────────────────────────

    async def search(
        self,
        keyword: str = "",
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Simulate: 業務系統查詢商品結構 → GET /api/v1/{vendor}/search"""
        params = {"page": page, "page_size": page_size}
        if keyword:
            params["keyword"] = keyword
        if category:
            params["category"] = category
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base}{self._api_prefix}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                return {
                    "status": resp.status,
                    "data": data,
                }

    # ── Orders ─────────────────────────────────────────────────

    async def create_order(
        self,
        event_id: str,
        seat_category: str,
        quantity: int,
        customer: dict,
        idempotency_key: str,
    ) -> dict:
        """Simulate: 業務系統下單 → POST /api/v1/{vendor}/orders"""
        payload = {
            "event_id": event_id,
            "seat_category": seat_category,
            "quantity": quantity,
            "customer": customer,
            "idempotency_key": idempotency_key,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base}{self._api_prefix}/orders",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                return {
                    "status": resp.status,
                    "data": data,
                }

    async def get_order(self, order_id: str) -> dict:
        """Simulate: 業務系統查單 → GET /api/v1/{vendor}/orders/{id}"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base}{self._api_prefix}/orders/{order_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                return {
                    "status": resp.status,
                    "data": data,
                }

    async def poll_order(self, order_id: str) -> dict:
        """Simulate: 業務系統輪詢訂單 → GET /api/v1/{vendor}/orders/{id}/poll"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base}{self._api_prefix}/orders/{order_id}/poll",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                return {
                    "status": resp.status,
                    "data": data,
                }

    # ── Inventory ──────────────────────────────────────────────

    async def check_inventory(self, event_id: str) -> dict:
        """Simulate: 業務系統查庫存 → GET /api/v1/{vendor}/inventory?event_id=..."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base}{self._api_prefix}/inventory",
                params={"event_id": event_id},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                return {
                    "status": resp.status,
                    "data": data,
                }
