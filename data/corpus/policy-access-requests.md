---
doc_type: policy
department: security
owner: security-team
review_cycle: quarterly
---

# Access Request Policy

## Principle

Access is granted per role, time-bounded, and never granted directly to an individual. If you find
yourself granting a permission to a named person, the role model is wrong — fix the role.

## Standard access

Standard access covers the tools every engineer needs: source control, the internal wiki, the
staging environment, the paging tool, and read-only observability.

This is provisioned automatically on the first day and requires no request. If something in the
standard set is missing, file a P4 ticket.

## Elevated access

Elevated access covers production read, production write, IAM administration, the internal CA, and
the billing console.

| Access | Approver | Maximum duration |
|---|---|---|
| Production read-only | Team lead | 90 days |
| Production write | Team lead **and** service owner | 30 days |
| IAM administration | Security team | 7 days |
| Internal CA signing | Security team lead | Per-ceremony |
| Billing console | Finance + engineering director | 90 days |

All elevated access expires automatically. There is no permanent elevated access, including for
team leads.

## Requesting elevated access

File a ticket with the access type, the business justification, and the duration needed. Requests
without a justification are rejected rather than queried — a template rejection costs less than a
round trip.

Approval is not automatic and is not granted during an incident by the requester's own authority.
See emergency access below.

## Emergency access

During a declared P1, the on-call engineer may self-grant production write access through the
break-glass path. This is logged, alerts the security team immediately, and expires after four
hours.

Break-glass access used outside a declared P1 is a security incident. Declaring the incident first
takes fifteen seconds and makes the access legitimate.

## Offboarding

Access is revoked within one hour of an offboarding ticket being filed. Revocation is automatic from
the HR system; the ticket exists for the audit trail, not to trigger the revocation.
