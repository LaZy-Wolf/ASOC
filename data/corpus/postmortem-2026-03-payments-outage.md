---
doc_type: postmortem
department: platform
owner: payments-team
incident_id: INC-2026-0312
severity: P1
date: 2026-03-12
---

# Postmortem: Payments Outage, 12 March 2026

## Summary

Payments were unavailable for 47 minutes. Approximately 8,400 transactions failed and were not
charged. No data was lost or exposed. Root cause was an inactive replication slot filling the
primary database's disk.

## Impact

- 14:03–14:50 UTC, 47 minutes
- Checkout returned 500 for all attempts
- 8,400 failed transactions, all retried successfully by customers or by the reconciliation job
- No incorrect charges

## Timeline

| Time (UTC) | Event |
|---|---|
| 09:20 | `prod-pg-standby-b` decommissioned. Its replication slot was not dropped. |
| 09:20–14:00 | WAL accumulates on the primary, pinned by the inactive slot. Disk usage climbs. |
| 13:41 | Disk usage crosses 90%. Alert fires as P3 and is auto-filed as a ticket. |
| 14:03 | Disk reaches 100%. Postgres refuses writes. Checkout begins failing. |
| 14:05 | P1 declared. |
| 14:11 | On-call identifies the full disk. |
| 14:26 | Inactive slot identified as the cause. |
| 14:33 | Slot dropped, WAL reclaimed, disk drops to 61%. |
| 14:50 | Writes recover, checkout confirmed healthy. |

## Root cause

Decommissioning a standby drops the node but does not drop its replication slot. An inactive slot
causes the primary to retain WAL indefinitely, because from the primary's point of view a replica
may still return and need it.

## What went wrong beyond the trigger

**The disk alert was a P3.** A disk filling on the primary database host is a P1 in waiting. The 22
minutes between the alert and the outage were sufficient to prevent it entirely, and were spent in a
ticket queue.

**Ownership was ambiguous.** The alert routed to infra, but the cause sat with the database team.
Six minutes of the incident were spent establishing who owned it.

## What went right

Failover was correctly *not* attempted. The standby would have inherited the same condition, and
promoting into it would have extended the outage.

## Action items

| Action | Owner | Due |
|---|---|---|
| Disk alerts on database hosts raised to P2 at 85%, P1 at 95% | infra-team | 2026-03-26 |
| Add explicit slot-drop step to the decommission runbook | database-team | 2026-03-19 |
| Alert on `pg_replication_slots` inactive for more than 1 hour | database-team | 2026-04-02 |
| Database host alerts route to the database team, not infra | sre-leads | 2026-03-26 |
