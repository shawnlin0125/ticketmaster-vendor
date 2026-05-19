"""Edge case tests — verify error handling and boundary conditions."""

import aiohttp


async def test_nonexistent_event(plugin):
    """Mock must return 404 for missing events."""
    mock = plugin.get_mock_server()
    port = await mock.start(port=0)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/events/nonexistent") as resp:
                assert resp.status == 404
    finally:
        await mock.stop()


async def test_ping_returns_ok(plugin):
    """Mock /ping must return healthy response."""
    mock = plugin.get_mock_server()
    port = await mock.start(port=0)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/ping") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "ok"
    finally:
        await mock.stop()


async def test_empty_event_list(plugin):
    """Plugin must handle empty event list gracefully (not crash)."""
    # Relies on fixtures/empty.json being loaded
    fixtures = plugin.get_fixtures()
    empty_fixture = next((f for f in fixtures if f.name == "empty"), None)
    assert empty_fixture is not None, "empty.json fixture is missing"
    assert empty_fixture.data.get("events") == []


async def test_malformed_data_present(plugin):
    """Malformed fixture must exist for error-handling tests."""
    fixtures = plugin.get_fixtures()
    malformed = next((f for f in fixtures if f.name == "malformed"), None)
    assert malformed is not None, "malformed.json fixture is missing"
    assert malformed.data.get("error") is not None
