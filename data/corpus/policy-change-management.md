---
doc_type: policy
department: platform
owner: sre-leads
review_cycle: quarterly
---

# Change Management Policy

## Change classes

### Standard change

Pre-approved, routine, reversible, and covered by automation. Deploying a service through the
regular pipeline is a standard change. No approval, no maintenance window, no ticket beyond the
deploy record.

### Normal change

Anything touching shared infrastructure, schemas, network topology, or IAM. Requires a change ticket
and an approver from the owning team. Must be scheduled inside a maintenance window if it carries
downtime.

### Emergency change

A change made to resolve an active P1 or P2. Proceed first, document within 24 hours. The change
ticket is filed retroactively and reviewed at the next reliability meeting.

## Maintenance windows

| Window | Time (UTC) | Suitable for |
|---|---|---|
| Weekly | Tuesday 02:00–05:00 | Schema migrations, node replacement |
| Weekly | Thursday 02:00–05:00 | Network and IAM changes |
| Monthly | First Sunday 01:00–07:00 | Major version upgrades |

Windows are booked through the change calendar. Two changes touching the same subsystem may not
share a window — if the first one goes wrong you need the window to recover, not to start a second
change.

## Change freeze

A freeze applies to all normal changes:

- The last two weeks of each quarter
- Any period with an active P1
- Company-wide freeze periods announced by engineering leadership

Standard changes continue during a freeze. Emergency changes are always permitted. A normal change
during a freeze requires the engineering director's approval, in writing, on the change ticket.

## Rollback requirement

Every normal change ticket must state its rollback procedure before approval. "Roll forward" is not
a rollback procedure. If a change genuinely cannot be rolled back — a destructive migration, for
example — the ticket must say so explicitly and name the recovery path.

## Postmortems

Postmortems are required for every P1 and for any customer-visible P2, within five business days.
They are blameless: the output is a list of systemic changes, not a list of people. Every action
item gets a ticket with an owner and a due date, or it does not count as an action item.
