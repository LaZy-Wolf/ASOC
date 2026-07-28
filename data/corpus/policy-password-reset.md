---
doc_type: policy
department: security
owner: security-team
audience: all-employees
---

# Password Policy and Reset

Covers corporate account passwords. Resetting a **second factor** is a different process with
different identity checks — see the MFA enrolment policy.

## Requirements

- Minimum 14 characters
- Checked against a breached-password list at set time; a password appearing in a known breach is
  rejected regardless of complexity
- Expiry every 180 days
- The last 10 passwords may not be reused
- No composition rules beyond length. Enforced symbol-and-digit rules produce predictable passwords
  and are deliberately not used here.

## Self-service reset

The self-service portal handles the overwhelming majority of resets. It requires an active second
factor.

1. Open the self-service portal from any device.
2. Enter your corporate email.
3. Approve the MFA prompt.
4. Set the new password.

Replication takes up to five minutes. Do not attempt to log in to the VPN immediately after a
reset — a rejection during that window is expected and not a second fault.

## Assisted reset

If you cannot use self-service — no working second factor, or a locked account — the reset must be
performed by IT support with identity verification.

Verification requires a **live video call** with the support engineer, showing a photo ID matching
the employee record. Verification over chat or email is not permitted, regardless of how well the
requester is known to the engineer. This rule exists because the two most damaging social
engineering attempts against this company both arrived over chat from a convincing internal-looking
account.

## Account lockout

Ten failed attempts locks the account for 30 minutes. The lockout clears on its own. IT support can
clear it early only after the same video verification.

## Compromise

If you believe your password has been exposed, reset it yourself immediately and then file a P2
ticket. Reset first, report second — the report can wait five minutes, the reset cannot.

## Shared accounts

Shared accounts are not permitted. Where a shared identity is genuinely required, such as a
deployment robot, use a service account with a credential in the secret manager and no interactive
login.
