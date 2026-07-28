---
doc_type: policy
department: security
owner: security-team
review_cycle: annual
---

# Data Retention

## Retention periods

| Data | Retention | Basis |
|---|---|---|
| Application logs | 30 days hot, 90 days archived | Operational |
| Audit logs (auth, IAM, break-glass) | 7 years | Regulatory |
| Customer records | Life of contract + 7 years | Regulatory |
| Support tickets | 3 years | Operational |
| Incident records and postmortems | Indefinite | Institutional memory |
| Database backups | 35 days | Operational |
| Employee records | Per HR policy | Regulatory |
| Email and chat | 3 years | Legal |

Audit logs are written to append-only storage. No individual, including administrators, can delete
them inside the retention window.

## Deletion requests

Customer deletion requests are honoured within 30 days and cover application data, logs referencing
the customer, and backups on their normal expiry schedule. Backups are not selectively edited —
deletion completes when the last backup containing the record expires, which is disclosed in the
response.

Audit records of the deletion itself are retained. Deleting the evidence of a deletion is not
compliance.

## Legal hold

A legal hold overrides every retention period and suspends all automatic deletion for the data in
scope. Holds are placed and released only by the legal team. An engineer who receives a hold notice
must not act on it directly — confirm scope with legal first.

## Backups

Database backups run nightly with 35-day retention and are tested by restore **monthly**. An
untested backup is not a backup. Restore tests are logged and reviewed at the reliability meeting.

Backups are encrypted at rest and stored in a separate account from production, so that a compromise
of production credentials does not reach them.

## Local copies

Production data may not be copied to laptops, personal cloud storage, or non-production
environments. Where realistic test data is needed, use the anonymisation pipeline — it preserves
data shape without carrying real identifiers.

Exporting production data for debugging is a normal change requiring an approver, and the export
must be destroyed within seven days.
