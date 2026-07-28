---
doc_type: policy
department: security
owner: security-team
audience: all-employees
---

# MFA Enrolment and Recovery

Covers the second factor. Resetting a **password** is a separate process — see the password policy.

## Accepted factors

| Factor | Permitted for | Notes |
|---|---|---|
| Hardware security key (FIDO2) | All access, including elevated | Required for production write and IAM |
| Authenticator app (TOTP) | Standard access | Default for most employees |
| Push notification | Standard access | Convenient, phishable; not permitted for elevated access |
| SMS | **Not permitted** | Removed company-wide after a SIM-swap incident |

Anyone holding elevated access must enrol a hardware key. An authenticator app alone will not
satisfy the check, and the access grant will be refused at approval time rather than at use time.

## Enrolment

New employees enrol during onboarding, before their first VPN connection. Enrolment is
self-service:

1. Sign in to the identity portal from the corporate laptop.
2. Choose the factor type.
3. For TOTP, scan the code and confirm one generated code.
4. For a hardware key, insert the key and follow the prompt.
5. **Save the recovery codes.** Ten single-use codes are issued once and are never shown again.

## Enrolling a second factor

Everyone should enrol at least two factors — typically a hardware key and an authenticator app.
Employees with a single enrolled factor are prompted quarterly until they add a second.

## Lost device

With a recovery code: use it at the identity portal, then immediately enrol a replacement factor.
Recovery codes are single-use.

Without a recovery code: the reset requires IT support and a **live video call** with photo ID, the
same verification standard as an assisted password reset. There is no chat-based path.

## Replacing a phone

Re-register before wiping the old device. Migrating a TOTP secret requires access to the old device;
once wiped, you are on the lost-device path.

## Elevated access and re-authentication

Elevated sessions require re-authentication with the hardware key every four hours. This is not
configurable per-team.

## Emergency

During a declared P1, an on-call engineer who has lost their second factor may be verified by the
security on-call over a live video call and issued a temporary factor valid for four hours. This is
logged and reviewed. It is not available outside a declared incident.
