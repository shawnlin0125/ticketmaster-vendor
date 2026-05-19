"""Business mock tests — verify the proxy's unified API works correctly.

These tests simulate the 業務系統（主系統）making calls to the proxy's
unified API (/api/v1/{vendor}/search, /orders, ...) and verify the proxy
handles them correctly against the vendor mock.

The vendor is specified in the URL path, not in a header.
"""

import pytest


async def test_business_mock_client_exists(plugin):
    """Business mock client factory must be importable."""
    client_class = plugin.get_business_mock_server()
    assert client_class is not None

    # Create a client instance with vendor
    client = client_class(proxy_base_url="http://127.0.0.1:8080", vendor="ticketmaster")
    assert client.vendor == "ticketmaster"

    # Verify all required API methods exist
    assert hasattr(client, "search")
    assert hasattr(client, "create_order")
    assert hasattr(client, "get_order")
    assert hasattr(client, "poll_order")
    assert hasattr(client, "check_inventory")


async def test_business_mock_url_format():
    """Verify the URL format includes vendor in the path."""
    from ticketmaster_plugin.mock.business.server import BusinessMockClient

    client = BusinessMockClient(proxy_base_url="http://127.0.0.1:8080", vendor="ticketmaster")
    assert client._api_prefix == "/api/v1/ticketmaster"

    # Test with different vendor
    client2 = BusinessMockClient(proxy_base_url="http://127.0.0.1:8080", vendor="kktix")
    assert client2._api_prefix == "/api/v1/kktix"


async def test_scenarios_exist():
    """All required business scenarios must be defined."""
    from ticketmaster_plugin.mock.business.scenarios import SCENARIOS

    assert "happy_path" in SCENARIOS
    assert "vendor_timeout" in SCENARIOS
    assert "empty_results" in SCENARIOS
    assert "invalid_request" in SCENARIOS
    assert "multi_page_search" in SCENARIOS


async def test_happy_path_scenario_covers_all_endpoints():
    """Happy path scenario must cover: search → order → get → poll → inventory."""
    from ticketmaster_plugin.mock.business.scenarios import HAPPY_PATH

    actions = [step[0] for step in HAPPY_PATH]
    assert "search" in actions
    assert "create_order" in actions
    assert "get_order" in actions
    assert "poll_order" in actions
    assert "check_inventory" in actions


# ── Full E2E integration tests will be implemented ──
# when the proxy's unified API handlers are wired up.
# These tests will:
#   1. Start vendor mock server (simulates TicketMaster API)
#   2. Start business mock client (simulates 業務系統)
#   3. Point proxy at vendor mock
#   4. Run business scenarios through proxy
#   5. Verify responses match expected unified API format
