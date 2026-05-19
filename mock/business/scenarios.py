"""Business scenarios — predefined workflows for integration testing.

Each scenario is a sequence of business system actions that represent
a real-world workflow. Tests iterate through these scenarios and verify
the proxy handles each step correctly.

Usage in tests:
    from mock.business.scenarios import SCENARIOS, run_scenario
    from mock.business.server import BusinessMockClient

    client = BusinessMockClient(proxy_url="http://127.0.0.1:8080", vendor="ticketmaster")
    results = await run_scenario(client, SCENARIOS["happy_path"])
"""

from __future__ import annotations

from typing import Any

# ── Scenario type ──────────────────────────────────────────────

# Each step is a tuple: (action_name, kwargs_dict)
# Actions map to BusinessMockClient methods
Scenario = list[tuple[str, dict[str, Any]]]


# ── Scenarios (vendor-agnostic — vendor is set at client creation) ──

HAPPY_PATH: Scenario = [
    # Step 1: 業務系統查詢 Coldplay 活動
    ("search", {"keyword": "Coldplay"}),
    # Step 2: 業務系統對該活動下單
    (
        "create_order",
        {
            "event_id": "evt_001",
            "seat_category": "seat_a",
            "quantity": 2,
            "customer": {
                "name": "王小明",
                "email": "wang@example.com",
                "phone": "+886912345678",
            },
            "idempotency_key": "scenario_happy_001",
        },
    ),
    # Step 3: 業務系統查詢訂單狀態
    ("get_order", {"order_id": "{order_id}"}),
    # Step 4: 業務系統輪詢訂單
    ("poll_order", {"order_id": "{order_id}"}),
    # Step 5: 業務系統查詢庫存
    ("check_inventory", {"event_id": "evt_001"}),
]


VENDOR_TIMEOUT: Scenario = [
    ("search", {"keyword": "Coldplay"}),
    (
        "create_order",
        {
            "event_id": "evt_timeout",
            "seat_category": "seat_a",
            "quantity": 1,
            "customer": {"name": "測試", "email": "test@example.com", "phone": "+886900000000"},
            "idempotency_key": "scenario_timeout_001",
        },
    ),
    ("get_order", {"order_id": "ord_timeout_001"}),
]


EMPTY_RESULTS: Scenario = [
    ("search", {"keyword": "NONEXISTENT_EVENT_999"}),
]


INVALID_REQUEST: Scenario = [
    (
        "create_order",
        {
            "event_id": "evt_001",
            # Missing: seat_category, quantity, customer
        },
    ),
]


MULTI_PAGE_SEARCH: Scenario = [
    ("search", {"keyword": "演唱會", "page": 1, "page_size": 2}),
    ("search", {"keyword": "演唱會", "page": 2, "page_size": 2}),
]


# ── All scenarios registry ────────────────────────────────────

SCENARIOS: dict[str, Scenario] = {
    "happy_path": HAPPY_PATH,
    "vendor_timeout": VENDOR_TIMEOUT,
    "empty_results": EMPTY_RESULTS,
    "invalid_request": INVALID_REQUEST,
    "multi_page_search": MULTI_PAGE_SEARCH,
}


def get_scenario(name: str) -> Scenario:
    """Get a scenario by name. Raises KeyError if not found."""
    if name not in SCENARIOS:
        raise KeyError(f"Scenario '{name}' not found. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[name]


async def run_scenario(client: Any, scenario: Scenario, context: dict = None) -> list[dict]:
    """Run a scenario against a BusinessMockClient instance.

    Args:
        client: BusinessMockClient instance (already configured with vendor)
        scenario: List of (action_name, kwargs) steps
        context: Shared context dict for passing data between steps
                 (e.g. order_id from create_order → get_order)

    Returns:
        List of {"action": ..., "status": ..., "data": ...} results
    """
    ctx = context or {}
    results = []

    for action, kwargs in scenario:
        # Resolve template variables like {order_id} from context
        resolved_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                key = v[1:-1]
                resolved_kwargs[k] = ctx.get(key, v)
            else:
                resolved_kwargs[k] = v

        method = getattr(client, action, None)
        if method is None:
            results.append({"action": action, "error": f"Unknown action: {action}"})
            continue

        result = await method(**resolved_kwargs)
        results.append({"action": action, **result})

        # Auto-capture order_id for subsequent steps
        if action == "create_order" and result.get("status") == 202:
            order_id = result.get("data", {}).get("data", {}).get("order_id")
            if order_id:
                ctx["order_id"] = order_id

    return results
