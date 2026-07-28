---
doc_type: policy
department: platform
owner: sre-leads
review_cycle: quarterly
---

# Incident Severity Policy

Severity describes **impact**, not effort. A five-minute fix for a total outage is still a P1.

## Definitions

### P1 — Critical

Complete loss of a customer-facing service, any data loss or data exposure, or a total failure of
authentication. Also includes anything that blocks all customer payments.

- Response time: **15 minutes**, any hour
- Requires: incident channel, incident commander, customer communication within 60 minutes
- Postmortem: **mandatory**, within 5 business days

### P2 — High

Major degradation with a workaround available, or complete loss of an internal system that blocks a
team. Elevated error rates above 5% sustained for ten minutes.

- Response time: **1 hour** during business hours, **4 hours** overnight
- Requires: incident channel
- Postmortem: required if customer-visible

### P3 — Moderate

Partial degradation affecting a subset of users, or a non-blocking failure in an internal tool.

- Response time: **1 business day**
- Postmortem: not required

### P4 — Low

Cosmetic issues, individual user requests, hardware requests, access requests, documentation gaps.

- Response time: **3 business days**
- Postmortem: not required

## Severity is set by impact, revised by evidence

The person who declares the incident sets the initial severity. Anyone may raise it. Only the
incident commander may lower it, and only with a stated reason recorded in the incident channel.

**When in doubt, declare higher.** Downgrading a P1 to a P2 costs nothing. Discovering four hours
late that a P3 was a P1 costs a great deal.

## Severity and escalation are different things

This policy defines *how bad* an incident is. Who gets paged, and how quickly it climbs the chain,
is defined in the escalation policy. A P1 always pages; a P2 pages only outside business hours.
