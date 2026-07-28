---
doc_type: guide
department: it-support
owner: it-support
audience: support-desk
---

# Ticket Triage

How the support desk categorises, prioritises, and routes incoming tickets.

## Categories

| Category | Examples | Default queue |
|---|---|---|
| `access` | Permission requests, account lockouts, offboarding | Security |
| `hardware` | Broken laptop, peripherals, loaners | IT support |
| `network` | VPN, wifi, connectivity | Network |
| `application` | SaaS tools, licences, internal apps | IT support |
| `incident` | Anything with production impact | Owning service team |
| `request` | Anything that is neither broken nor blocking | IT support |

A ticket that does not obviously fit a category is `request` until proven otherwise. Do not invent
categories — an unmapped category has no queue and no SLA.

## Priority

Priority follows the incident severity policy. For non-incident tickets the practical rules are:

- **P2** — a person is completely blocked from working, or there is potential data exposure
- **P3** — a person is partially blocked, or a workaround exists
- **P4** — everything else, including all routine requests

"Urgent" in the ticket title does not set priority. Impact sets priority.

## Required fields before routing

A ticket cannot leave triage without: requester, category, priority, and affected system. Tickets
missing these go back to the requester with a specific question, not a generic "more information
required".

## Duplicate detection

Before creating a ticket, search open tickets for the same affected system. Three or more open
tickets naming the same system within an hour is a signal of an underlying incident — raise it to
the owning team rather than working the tickets individually.

## Routing rules

- Anything mentioning production write access routes to Security regardless of category.
- Anything reporting lost or stolen hardware routes to both IT support and Security.
- Anything affecting more than five people routes to the owning service team as an incident.
- Password and MFA resets that require verification route to IT support with a video call flag.

## SLA clock

The clock starts when the ticket is created, not when it is triaged. It pauses only while the ticket
is genuinely waiting on the requester, and the pause reason must be recorded. Pausing the clock for
internal delays is not permitted.

## Escalation from the desk

If the desk cannot resolve within one SLA period, escalate to the owning team with a summary of what
has been ruled out. Escalating with no diagnostic work attached is returned to the desk.
