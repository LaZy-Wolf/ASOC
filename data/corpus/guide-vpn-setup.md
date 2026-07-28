---
doc_type: guide
department: it-support
owner: it-support
audience: all-employees
---

# VPN Setup

How to get the VPN working for the first time. If your VPN used to work and has stopped, use the VPN
troubleshooting guide instead — the causes are entirely different.

## Before you start

You need:

- A corporate laptop that has completed provisioning
- MFA enrolled (the VPN client will not accept a password alone)
- Your employee ID, which is on your onboarding ticket

## Install the client

The client is pushed automatically to corporate laptops within two hours of provisioning. If it is
not in your applications list after two hours, file a P4 ticket — do not download the client from
the vendor's website, because the corporate build carries the certificate bundle.

## First connection

1. Open the client and choose the profile matching your region: `vpn-eu`, `vpn-us`, or `vpn-apac`.
   Pick the region you are physically in, not the region your team is in.
2. Enter your corporate email as the username.
3. Enter your password, then approve the MFA push.
4. On first connection only, the client requests a device certificate. This takes up to 90 seconds
   and looks like a hang. Let it finish.

## Split tunnel

The default profile is split tunnel: only corporate traffic goes over the VPN. Personal traffic goes
out over your own connection. This is intentional and is not a misconfiguration.

Full tunnel is available as `vpn-eu-full` and similar, and is required only when accessing the
billing console or the internal CA.

## What the VPN does not give you

Connecting to the VPN puts you on the corporate network. It does **not** grant production access —
that is a separate, role-based grant covered by the access request policy. Being on the VPN and
being authorized are different things.

## Contractors and personal devices

Contractors use the same client but a separate profile (`vpn-contractor`) with a narrower route set.
Personal devices are not permitted on the VPN under any profile. Request a loaner laptop instead.
