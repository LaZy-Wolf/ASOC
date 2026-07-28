---
doc_type: guide
department: it-support
owner: it-support
audience: all-employees
---

# VPN Troubleshooting

For a VPN that previously worked and has stopped. If you have never successfully connected, use the
VPN setup guide instead — a first connection failure is almost always provisioning, not a fault.

## Symptom: authentication fails

### Password accepted, MFA push never arrives

The push goes to the device registered at enrolment, which is often an old phone. Re-register the
device through the MFA self-service portal. This does not require a ticket.

### Password rejected immediately

Your password may have expired. Passwords expire every 180 days and the VPN client reports an
expired password as an ordinary rejection rather than an expiry. Reset it through the self-service
portal, then wait five minutes for replication before retrying.

## Symptom: connects, then drops after 30–60 seconds

This is nearly always an expired **device certificate**. Certificates are valid for one year and
renew silently while you are connected — a laptop that has been offline for a long stretch misses
the renewal window.

Fix: remove the profile and re-add it. The client re-enrols the certificate on the next connection.

## Symptom: connected but internal sites do not resolve

Split tunnel routes only corporate ranges over the tunnel. If DNS is resolving internal names to
public addresses, your local resolver is winning.

1. Confirm the client shows the corporate DNS servers as active.
2. Flush the local DNS cache.
3. If you are on a home router that forces its own DNS, switch the client to full tunnel as a
   workaround and file a ticket.

## Symptom: severe slowness on the tunnel

Check which region profile you are connected to. Connecting to `vpn-eu` from Asia routes every
packet through Europe. This is the single most common cause of "the VPN is slow" tickets.

## Symptom: everyone is affected

If several people report VPN failure at once, this is not a client problem. Check the status page
before troubleshooting individual laptops, and escalate to the network on-call — a concentrator
failure is a P2.

## When to file a ticket

File a P3 if the steps above do not resolve it, and include: the profile name, the client version,
the exact error text, and whether anyone else on your team is affected.
