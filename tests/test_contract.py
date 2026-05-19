"""Contract tests — verify TicketmasterPlugin implements all required contracts.

Two contracts:
  1. Plugin ABC (platform_plugin_sdk)  — lifecycle: start/stop/health
  2. VendorProxy ABC (unified_ticket_api) — business: search/orders/inventory
"""

import asyncio
from platform_plugin_sdk import Plugin
from unified_ticket_api import VendorProxy


async def test_plugin_metadata(plugin: Plugin):
    """Plugin must declare plugin_id, plugin_name, version."""
    assert plugin.plugin_id == "ticketmaster"
    assert plugin.plugin_name == "TicketMaster"
    assert plugin.version > "0"


async def test_implements_plugin_abc(plugin):
    """Must inherit from platform_plugin_sdk.Plugin."""
    assert isinstance(plugin, Plugin)


async def test_implements_vendor_proxy_abc(plugin):
    """Must inherit from unified_ticket_api.VendorProxy."""
    assert isinstance(plugin, VendorProxy)


async def test_db_schema(plugin: Plugin):
    """Schema name must follow convention."""
    assert plugin.db_schema == "plugin_ticketmaster"


async def test_redis_prefix(plugin: Plugin):
    """Redis prefix must follow convention."""
    assert plugin.redis_prefix == "plugin:ticketmaster:"


async def test_has_mock_server(plugin: Plugin):
    """Plugin must provide a vendor mock server (downstream)."""
    mock = plugin.get_mock_server()
    assert mock is not None
    assert hasattr(mock, "start")
    assert hasattr(mock, "stop")


async def test_has_business_mock_server(plugin: Plugin):
    """Plugin must provide a business mock client (upstream)."""
    client_class = plugin.get_business_mock_server()
    assert client_class is not None


async def test_has_fixtures(plugin: Plugin):
    """Plugin must provide test fixtures."""
    fixtures = plugin.get_fixtures()
    assert len(fixtures) > 0
    names = [f.name for f in fixtures]
    assert "events" in names
    assert "tickets" in names


async def test_has_business_methods(plugin):
    """Plugin must implement all VendorProxy business methods."""
    assert hasattr(plugin, "search")
    assert hasattr(plugin, "create_order")
    assert hasattr(plugin, "get_order")
    assert hasattr(plugin, "poll_order")
    assert hasattr(plugin, "check_inventory")
    assert callable(plugin.search)
    assert callable(plugin.create_order)


async def test_repo_url(plugin):
    """Plugin must declare its source repo URL for traceability."""
    assert hasattr(plugin, "repo_url")
    assert "ticketmaster-vendor" in plugin.repo_url


async def test_version_format(plugin):
    """Version must follow semver format."""
    parts = plugin.version.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
