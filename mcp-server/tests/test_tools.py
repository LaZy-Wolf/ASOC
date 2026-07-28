"""Every tool: one happy path, one bad input. Runs against a temp SQLite file."""

import asyncio

import pytest

import db
import server

EXPECTED_TOOLS = {
    "create_ticket",
    "find_oncall",
    "get_asset",
    "get_user",
    "log_interaction",
    "schedule_maintenance_window",
    "search_tickets",
    "update_ticket",
}


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init()


# fastmcp 3.x @mcp.tool registers the function and returns it unchanged, so it stays
# directly callable. (In 2.x it returned a FunctionTool wrapper with a .fn attribute.)
def call(tool, **kwargs):
    return tool(**kwargs)


def test_all_tools_are_registered_with_the_server():
    """A typo'd decorator leaves the function callable but invisible to MCP clients."""
    registered = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert registered == EXPECTED_TOOLS


def test_round_trip_over_the_mcp_protocol():
    """What Claude Desktop actually does: call by name with a JSON payload.

    The direct-call tests below skip schema validation and serialisation; this one does not.
    """

    async def scenario():
        from fastmcp import Client

        async with Client(server.mcp) as client:
            created = await client.call_tool(
                "create_ticket",
                {
                    "title": "Laptop will not power on",
                    "description": "No response on two adapters.",
                    "category": "hardware",
                    "priority": "P3",
                    "requester_email": "mira.kovac@example.com",
                },
            )
            found = await client.call_tool("search_tickets", {"query": "power on"})
            return created.data, found.data

    created, found = asyncio.run(scenario())
    assert created["assignee_team"] == "it-support"
    assert [t["id"] for t in found] == [created["id"]]


# ------------------------------------------------------------------ reads


def test_get_user_found_and_missing():
    assert call(server.get_user, email="priya.raman@example.com")["team"] == "platform"
    with pytest.raises(ValueError, match="no user"):
        call(server.get_user, email="nobody@example.com")


def test_get_asset_reports_warranty_and_holder():
    asset = call(server.get_asset, tag="LT-4388")
    assert asset["status"] == "out-of-warranty"
    assert asset["assigned_email"] == "sana.iqbal@example.com"
    with pytest.raises(ValueError, match="no asset"):
        call(server.get_asset, tag="LT-0000")


def test_search_tickets_filters():
    assert len(call(server.search_tickets, query="VPN")) == 1
    assert call(server.search_tickets, query="", priority="P2")[0]["priority"] == "P2"
    with pytest.raises(ValueError, match="priority must be"):
        call(server.search_tickets, priority="urgent")


def test_find_oncall_returns_both_tiers():
    tiers = [r["tier"] for r in call(server.find_oncall, team="platform")]
    assert tiers == ["primary", "secondary"]
    with pytest.raises(ValueError, match="no on-call"):
        call(server.find_oncall, team="marketing")


# ----------------------------------------------------------------- writes


def test_create_ticket_routes_by_category_and_persists():
    ticket = call(
        server.create_ticket,
        title="Cannot reach internal wiki",
        description="Resolves to a public IP on the tunnel.",
        category="network",
        priority="P3",
        requester_email="owen.brooks@example.com",
    )
    assert ticket["assignee_team"] == "network"
    assert ticket["status"] == "open"

    # the row is really on disk, not just in the return value
    with db.connect() as conn:
        stored = conn.execute("SELECT title FROM tickets WHERE id = ?", (ticket["id"],)).fetchone()
    assert stored["title"] == "Cannot reach internal wiki"


def test_create_ticket_rejects_invented_priority():
    with pytest.raises(ValueError, match="priority must be"):
        call(
            server.create_ticket,
            title="x",
            description="y",
            category="request",
            priority="urgent",
            requester_email="owen.brooks@example.com",
        )


def test_create_ticket_rejects_unknown_requester():
    with pytest.raises(ValueError, match="no user"):
        call(
            server.create_ticket,
            title="x",
            description="y",
            category="request",
            priority="P4",
            requester_email="ghost@example.com",
        )


def test_update_ticket_changes_only_what_is_passed():
    before = call(server.search_tickets, query="VPN")[0]
    after = call(server.update_ticket, ticket_id=before["id"], status="in-progress")
    assert after["status"] == "in-progress"
    assert after["priority"] == before["priority"]

    with pytest.raises(ValueError, match="nothing to update"):
        call(server.update_ticket, ticket_id=before["id"])
    with pytest.raises(ValueError, match="no ticket"):
        call(server.update_ticket, ticket_id=9999, status="closed")


def test_log_interaction_requires_a_real_ticket():
    ticket = call(server.search_tickets, query="VPN")[0]
    note = call(
        server.log_interaction,
        ticket_id=ticket["id"],
        author="owen.brooks@example.com",
        note="Re-added profile; certificate re-enrolled.",
    )
    assert note["ticket_id"] == ticket["id"]
    with pytest.raises(ValueError, match="no ticket"):
        call(server.log_interaction, ticket_id=9999, author="x", note="y")


def test_maintenance_window_rejects_overlap_on_same_subsystem():
    booked = call(
        server.schedule_maintenance_window,
        subsystem="prod-pg",
        starts_at="2026-08-04T02:00:00Z",
        ends_at="2026-08-04T05:00:00Z",
        change_ticket="CHG-1001",
        booked_by="priya.raman@example.com",
    )
    assert booked["subsystem"] == "prod-pg"

    with pytest.raises(ValueError, match="already has a window"):
        call(
            server.schedule_maintenance_window,
            subsystem="prod-pg",
            starts_at="2026-08-04T04:00:00Z",
            ends_at="2026-08-04T06:00:00Z",
            change_ticket="CHG-1002",
            booked_by="tom.alvarez@example.com",
        )

    # a different subsystem in the same slot is fine
    call(
        server.schedule_maintenance_window,
        subsystem="identity",
        starts_at="2026-08-04T02:00:00Z",
        ends_at="2026-08-04T05:00:00Z",
        change_ticket="CHG-1003",
        booked_by="sana.iqbal@example.com",
    )


def test_maintenance_window_rejects_inverted_times():
    with pytest.raises(ValueError, match="before ends_at"):
        call(
            server.schedule_maintenance_window,
            subsystem="prod-pg",
            starts_at="2026-08-04T05:00:00Z",
            ends_at="2026-08-04T02:00:00Z",
            change_ticket="CHG-1004",
            booked_by="priya.raman@example.com",
        )
