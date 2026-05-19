"""Vendor mock tests — verify the proxy correctly handles external vendor API.

These tests start the vendor mock server (simulates TicketMaster API)
and verify the proxy's interactions with the downstream vendor.
"""

import json
from pathlib import Path

import aiohttp

FIXTURES = Path(__file__).parent.parent / "fixtures"


async def test_mock_returns_events(plugin):
    """Mock server must return events from fixtures."""
    mock = plugin.get_mock_server()
    port = await mock.start(port=0)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/events") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "events" in data
                assert len(data["events"]) == 3
                assert data["events"][0]["name"].startswith("Coldplay")
    finally:
        await mock.stop()


async def test_mock_returns_tickets(plugin):
    """Mock server must return tickets for a specific event."""
    mock = plugin.get_mock_server()
    port = await mock.start(port=0)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/events/evt_001/tickets") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert "tickets" in data
                assert len(data["tickets"]) == 3
    finally:
        await mock.stop()


async def test_mock_pagination(plugin):
    """Mock server must support pagination."""
    mock = plugin.get_mock_server()
    port = await mock.start(port=0)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/events?page=1&page_size=2") as resp:
                data = await resp.json()
                assert len(data["events"]) == 2
                assert data["total"] == 3

            async with session.get(f"http://127.0.0.1:{port}/events?page=2&page_size=2") as resp:
                data = await resp.json()
                assert len(data["events"]) == 1
    finally:
        await mock.stop()
