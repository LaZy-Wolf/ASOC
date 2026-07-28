---
doc_type: policy
department: platform
owner: sre-leads
review_cycle: quarterly
---

# Escalation Policy

This policy defines **who to contact and when**. It does not define how severe an incident is — see
the incident severity policy for that.

## Escalation ladder

Every escalation follows the same ladder. Each rung has a timeout; when the timeout expires without
acknowledgement, the page automatically climbs to the next rung.

| Rung | Who | Ack timeout |
|---|---|---|
| 1 | Primary on-call for the owning service | 5 minutes |
| 2 | Secondary on-call for the owning service | 5 minutes |
| 3 | Team lead of the owning service | 10 minutes |
| 4 | SRE on-call (cross-team) | 10 minutes |
| 5 | Engineering director | — |

## When paging is allowed

| Severity | Business hours | Outside business hours |
|---|---|---|
| P1 | Page immediately | Page immediately |
| P2 | Ticket + Slack to the team channel | Page |
| P3 | Ticket only | Ticket only |
| P4 | Ticket only | Ticket only |

Paging someone for a P3 outside business hours is a policy violation, not a judgement call. If a P3
genuinely cannot wait until morning, it is not a P3 — raise the severity first, then page.

## Cross-team escalation

If the owning team cannot be determined within ten minutes, page the SRE on-call directly at rung 4.
Do not spend the incident searching for an owner.

## Customer communication

For P1 incidents the incident commander owns customer communication. The status page must be updated
within 60 minutes of declaration and every 60 minutes thereafter until resolution. Engineers working
the incident do not post customer-facing updates.

## Vendor escalation

For incidents traced to a third-party provider, the vendor escalation contacts are held by the
procurement team, not by engineering. Request them through the incident channel; do not hunt for a
support phone number during a P1.
