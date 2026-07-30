"""ASOC IT-operations MCP server.

Eight tools over a real SQLite store. Four read, four write — the split matters: the P4
orchestrator gates every write behind a human approval, and reads flow through untouched.

Each docstring is the contract the model reads to decide whether and how to call the tool.
Keep them specific: the valid values below are what stop the model inventing a priority.

Run:            python server.py
Inspect:        npx @modelcontextprotocol/inspector python server.py
"""

from __future__ import annotations

from typing import Literal

import db
from fastmcp import FastMCP

mcp = FastMCP("asoc-itsm")

# These annotations become `enum` in the advertised JSON schema, so a client cannot even propose an
# invented value — the model is constrained at the protocol level rather than corrected afterwards.
# Groq rejects a tool call that violates the schema, which is a cheaper failure than a bad write.
# The runtime checks below stay as defence for callers that are not going through MCP.
Category = Literal["access", "hardware", "network", "application", "incident", "request"]
Priority = Literal["P1", "P2", "P3", "P4"]
Status = Literal["open", "awaiting-approval", "in-progress", "resolved", "closed"]

# "" means "leave unchanged" on the optional parameters
OptionalPriority = Literal["", "P1", "P2", "P3", "P4"]
OptionalStatus = Literal["", "open", "awaiting-approval", "in-progress", "resolved", "closed"]

CATEGORIES = {"access", "hardware", "network", "application", "incident", "request"}
PRIORITIES = {"P1", "P2", "P3", "P4"}
STATUSES = {"open", "awaiting-approval", "in-progress", "resolved", "closed"}

# which team owns which category, per the ticket triage guide
ROUTING = {
    "access": "security",
    "hardware": "it-support",
    "network": "network",
    "application": "it-support",
    "incident": "platform",
    "request": "it-support",
}


def _row(row) -> dict:
    return dict(row) if row else {}


def _user_id(conn, email: str) -> int:
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        raise ValueError(f"no user with email {email!r}")
    return row["id"]


# --------------------------------------------------------------------------- reads


@mcp.tool
def get_user(email: str) -> dict:
    """Look up an employee by their exact corporate email address.

    Returns name, email, department, and team. Raises if no such user exists.
    Use this to resolve a requester before creating a ticket on their behalf.
    """
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        raise ValueError(f"no user with email {email!r}")
    return _row(row)


@mcp.tool
def get_asset(tag: str) -> dict:
    """Look up a hardware asset by its tag, for example "LT-4471".

    Returns kind, model, warranty_until, status, and the email of the person it is
    assigned to. Use this to check warranty before proposing a repair or replacement.
    """
    with db.connect() as conn:
        row = conn.execute(
            "SELECT a.*, u.email AS assigned_email FROM assets a"
            " LEFT JOIN users u ON u.id = a.assigned_to WHERE a.tag = ?",
            (tag,),
        ).fetchone()
    if not row:
        raise ValueError(f"no asset with tag {tag!r}")
    return _row(row)


@mcp.tool
def search_tickets(
    query: str = "", status: OptionalStatus = "", priority: OptionalPriority = "", limit: int = 20
) -> list[dict]:
    """Search tickets by free text over title and description, with optional filters.

    query    substring matched against title and description; empty matches everything
    status   one of open, awaiting-approval, in-progress, resolved, closed
    priority one of P1, P2, P3, P4

    Returns newest first. Use this to check for duplicates before creating a ticket —
    three or more open tickets naming the same system suggests an underlying incident.
    """
    if status and status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    if priority and priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(PRIORITIES)}")

    sql = "SELECT * FROM tickets WHERE (title LIKE ? OR description LIKE ?)"
    args: list = [f"%{query}%", f"%{query}%"]
    if status:
        sql, args = sql + " AND status = ?", [*args, status]
    if priority:
        sql, args = sql + " AND priority = ?", [*args, priority]
    sql += " ORDER BY id DESC LIMIT ?"

    with db.connect() as conn:
        rows = conn.execute(sql, [*args, limit]).fetchall()
    return [_row(r) for r in rows]


@mcp.tool
def find_oncall(team: str) -> list[dict]:
    """Who is on call for a team right now.

    team is one of platform, security, identity, payments, it-support.
    Returns one entry per tier (primary, secondary) with the engineer's name and email.
    Page the primary first; the escalation policy climbs to secondary after 5 minutes.
    """
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT o.tier, o.starts_at, o.ends_at, u.name, u.email FROM oncall o"
            " JOIN users u ON u.id = o.engineer_id WHERE o.team = ? ORDER BY o.tier",
            (team,),
        ).fetchall()
    if not rows:
        raise ValueError(f"no on-call rotation for team {team!r}")
    return [_row(r) for r in rows]


# -------------------------------------------------------------------------- writes


@mcp.tool
def create_ticket(
    title: str, description: str, category: Category, priority: Priority, requester_email: str
) -> dict:
    """Create a support ticket. This writes to the ticketing system.

    category one of access, hardware, network, application, incident, request
    priority one of P1, P2, P3, P4 — set by impact, not urgency:
             P1 total loss of a customer-facing service or any data exposure
             P2 major degradation with a workaround, or a person fully blocked
             P3 partial degradation, or a workaround exists
             P4 routine requests, access requests, cosmetic issues

    The assignee team is derived from the category. Returns the created ticket.
    """
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(PRIORITIES)}")

    with db.connect() as conn:
        requester = _user_id(conn, requester_email)
        cur = conn.execute(
            "INSERT INTO tickets (title, description, category, priority, status, requester_id,"
            " assignee_team, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                title,
                description,
                category,
                priority,
                "open",
                requester,
                ROUTING[category],
                db.now(),
                db.now(),
            ),
        )
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row(row)


@mcp.tool
def update_ticket(
    ticket_id: int,
    status: OptionalStatus = "",
    priority: OptionalPriority = "",
    assignee_team: str = "",
) -> dict:
    """Change a ticket's status, priority, or owning team. This writes to the ticketing system.

    Pass only the fields you intend to change; empty values are left alone.
    Returns the updated ticket. Raises if the ticket does not exist.
    """
    if status and status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    if priority and priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {sorted(PRIORITIES)}")

    changes = {k: v for k, v in
               {"status": status, "priority": priority, "assignee_team": assignee_team}.items() if v}
    if not changes:
        raise ValueError("nothing to update: pass at least one of status, priority, assignee_team")

    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            raise ValueError(f"no ticket with id {ticket_id}")
        assignments = ", ".join(f"{k} = ?" for k in changes)
        conn.execute(
            f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?",
            [*changes.values(), db.now(), ticket_id],
        )
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return _row(row)


@mcp.tool
def log_interaction(ticket_id: int, author: str, note: str) -> dict:
    """Append a note to a ticket's history. This writes to the ticketing system.

    Use it to record what was tried and ruled out — escalating with no diagnostic
    work attached gets the ticket returned to the desk.
    """
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone():
            raise ValueError(f"no ticket with id {ticket_id}")
        cur = conn.execute(
            "INSERT INTO interactions (ticket_id, author, note, created_at) VALUES (?,?,?,?)",
            (ticket_id, author, note, db.now()),
        )
        row = conn.execute("SELECT * FROM interactions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row(row)


@mcp.tool
def schedule_maintenance_window(
    subsystem: str, starts_at: str, ends_at: str, change_ticket: str, booked_by: str
) -> dict:
    """Book a maintenance window for a subsystem. This writes to the change calendar.

    Times are ISO 8601 UTC, for example "2026-08-04T02:00:00Z". Standard windows are
    Tuesday and Thursday 02:00-05:00 UTC, plus the first Sunday 01:00-07:00 monthly.

    Two changes touching the same subsystem may not share a window — if the first goes
    wrong you need the window to recover, not to start a second change. An overlapping
    booking for the same subsystem is rejected.
    """
    if starts_at >= ends_at:
        raise ValueError("starts_at must be before ends_at")

    with db.connect() as conn:
        clash = conn.execute(
            "SELECT change_ticket FROM maintenance_windows"
            " WHERE subsystem = ? AND starts_at < ? AND ends_at > ?",
            (subsystem, ends_at, starts_at),
        ).fetchone()
        if clash:
            raise ValueError(
                f"{subsystem} already has a window overlapping that time "
                f"(change {clash['change_ticket']})"
            )
        cur = conn.execute(
            "INSERT INTO maintenance_windows (subsystem, starts_at, ends_at, change_ticket,"
            " booked_by) VALUES (?,?,?,?,?)",
            (subsystem, starts_at, ends_at, change_ticket, booked_by),
        )
        row = conn.execute(
            "SELECT * FROM maintenance_windows WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _row(row)


if __name__ == "__main__":
    db.init()
    mcp.run()
