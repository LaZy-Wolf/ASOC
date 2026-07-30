"""SQLite store behind the MCP tools.

Real persistence rather than a stub, so "Claude created a ticket" means a row exists on disk.
Plain sqlite3 — no ORM for six tables.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

# module-level so tests can point it at a temp file; ASOC_DB_PATH lets a caller that only
# controls the environment (the stdio-spawned server in the framework comparison) redirect it
DB_PATH = Path(os.environ.get("ASOC_DB_PATH") or Path(__file__).resolve().parent / "asoc.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    team TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    tag TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    model TEXT NOT NULL,
    assigned_to INTEGER REFERENCES users(id),
    issued_on TEXT NOT NULL,
    warranty_until TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    requester_id INTEGER NOT NULL REFERENCES users(id),
    assignee_team TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    author TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS oncall (
    id INTEGER PRIMARY KEY,
    team TEXT NOT NULL,
    tier TEXT NOT NULL,
    engineer_id INTEGER NOT NULL REFERENCES users(id),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS maintenance_windows (
    id INTEGER PRIMARY KEY,
    subsystem TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    change_ticket TEXT NOT NULL,
    booked_by TEXT NOT NULL
);
"""

USERS = [
    ("Priya Raman", "priya.raman@example.com", "engineering", "platform"),
    ("Tom Alvarez", "tom.alvarez@example.com", "engineering", "platform"),
    ("Sana Iqbal", "sana.iqbal@example.com", "engineering", "identity"),
    ("Dev Mehta", "dev.mehta@example.com", "engineering", "payments"),
    ("Lena Fischer", "lena.fischer@example.com", "security", "security"),
    ("Owen Brooks", "owen.brooks@example.com", "operations", "it-support"),
    ("Mira Kovac", "mira.kovac@example.com", "finance", "finance"),
]

ASSETS = [
    ("LT-4471", "laptop", '16" 36GB 1TB', 1, "2024-02-11", "2027-02-11", "active"),
    ("LT-4502", "laptop", '16" 64GB 2TB', 2, "2023-08-02", "2026-08-02", "active"),
    ("LT-4610", "laptop", '14" 18GB 512GB', 6, "2025-11-19", "2028-11-19", "active"),
    ("LT-4388", "laptop", '16" 36GB 1TB', 3, "2023-01-30", "2026-01-30", "out-of-warranty"),
    ("DK-0912", "dock", "USB-C 90W", 1, "2024-02-11", "2027-02-11", "active"),
]

TICKETS = [
    ("VPN drops after 60 seconds", "Connects then disconnects, started this week.",
     "network", "P3", "open", 6, "network"),
    ("Disk at 91% on prod-pg-primary", "Growth since standby-b decommission.",
     "incident", "P2", "open", 1, "infra-team"),
    ("Production write access for payments migration", "Needed for the Thursday window.",
     "access", "P4", "awaiting-approval", 4, "security"),
    ("Laptop will not charge", "LT-4388, no charge on two known-good adapters.",
     "hardware", "P3", "resolved", 3, "it-support"),
]

ONCALL = [
    ("platform", "primary", 1, "2026-07-22T10:00:00Z", "2026-07-29T10:00:00Z"),
    ("platform", "secondary", 2, "2026-07-22T10:00:00Z", "2026-07-29T10:00:00Z"),
    ("security", "primary", 5, "2026-07-22T10:00:00Z", "2026-07-29T10:00:00Z"),
    ("identity", "primary", 3, "2026-07-22T10:00:00Z", "2026-07-29T10:00:00Z"),
    ("it-support", "primary", 6, "2026-07-22T10:00:00Z", "2026-07-29T10:00:00Z"),
]


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init() -> None:
    """Create the schema and seed it once. Safe to call on every start."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            return

        conn.executemany("INSERT INTO users (name, email, department, team) VALUES (?,?,?,?)", USERS)
        conn.executemany(
            "INSERT INTO assets (tag, kind, model, assigned_to, issued_on, warranty_until, status)"
            " VALUES (?,?,?,?,?,?,?)",
            ASSETS,
        )
        conn.executemany(
            "INSERT INTO tickets (title, description, category, priority, status, requester_id,"
            " assignee_team, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            [(*t, now(), now()) for t in TICKETS],
        )
        conn.executemany(
            "INSERT INTO oncall (team, tier, engineer_id, starts_at, ends_at) VALUES (?,?,?,?,?)",
            ONCALL,
        )
