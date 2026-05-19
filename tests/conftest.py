"""Pytest fixtures for ticketmaster plugin tests."""

import pytest
from ticketmaster_plugin.plugin import TicketmasterPlugin


@pytest.fixture
def plugin():
    """Return a TicketmasterPlugin instance for testing."""
    return TicketmasterPlugin()
# CI trigger
