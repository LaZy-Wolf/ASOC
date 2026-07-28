---
doc_type: policy
department: platform
owner: sre-leads
review_cycle: quarterly
---

# On-Call Rotation Policy

## Structure

Each service team runs a primary and a secondary rotation. A cross-team SRE rotation sits above both
and is paged only for cross-cutting incidents or when a team's ladder is exhausted.

- Shift length: **one week**, Wednesday 10:00 to Wednesday 10:00
- Minimum rotation size: **four people**. A rotation that drops below four is escalated to the
  engineering director, because a three-person rotation burns out within a quarter.
- No engineer may be scheduled for consecutive weeks except by their own request.

## Handoff

Handoff happens at the Wednesday shift boundary and is a **live conversation**, not a document
drop. The outgoing engineer walks through:

1. Any open incidents and their current state
2. Anything deliberately deferred to the incoming shift
3. Alerts that fired but were not actionable, and whether a tuning ticket exists
4. Any planned maintenance windows falling inside the incoming shift

If handoff does not happen, the outgoing engineer remains responsible until it does.

## Compensation

On-call is compensated per shift, with an additional per-incident payment for pages received outside
business hours. Compensation is processed automatically from the paging system's records — you do
not need to file anything.

## Swapping a shift

Swaps are self-service in the paging tool and require the accepting engineer's confirmation. Swaps
inside 48 hours of the shift start additionally require the team lead's approval, because the
handoff conversation has usually already been scheduled.

## Rest after a night page

An engineer paged between 00:00 and 06:00 is entitled to a delayed start the following day, and to a
full day off if the incident ran longer than three hours. This is not discretionary and does not
require manager approval — inform your team and take it.

## Alert quality

An alert that pages and is not actionable is a defect. The on-call engineer files a tuning ticket
for every non-actionable page. Rotations reporting more than three non-actionable pages per shift
are reviewed at the monthly reliability meeting.
