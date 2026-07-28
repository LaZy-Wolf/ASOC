---
doc_type: policy
department: it-support
owner: it-support
audience: all-employees
---

# Laptop Provisioning

Covers issuing a laptop to a **new** employee or contractor. Replacing a laptop that is broken,
lost, or out of warranty is covered by the hardware replacement policy.

## Standard configurations

| Role | Configuration |
|---|---|
| Engineering | 16" laptop, 36GB RAM, 1TB SSD |
| Data / ML | 16" laptop, 64GB RAM, 2TB SSD |
| Design | 16" laptop, 36GB RAM, 1TB SSD, colour-calibrated display |
| All other roles | 14" laptop, 18GB RAM, 512GB SSD |

Non-standard configurations require the hiring manager's approval on the provisioning ticket and add
roughly two weeks to delivery, because they are not held in stock.

## Timeline

Provisioning is triggered automatically by the HR system when a start date is confirmed. IT support
does not need a separate request.

| Stage | Lead time |
|---|---|
| Stock configuration, local | 5 business days before start date |
| Stock configuration, remote | 10 business days before start date |
| Non-standard configuration | 4 weeks |

If a start date is confirmed with less than the required lead time, a loaner is issued on day one
and the permanent machine follows.

## What arrives configured

Disk encryption, the management agent, the VPN client with the corporate certificate bundle,
endpoint protection, and the standard application set. The employee sets their password and enrols
MFA on first boot.

Machines are never shipped with a pre-set password.

## Contractors

Contractors receive the "all other roles" configuration by default and a machine tagged to the
contract end date. The management agent locks the machine automatically at contract end unless the
contract is extended in the HR system.

## Personal devices

Personal devices may not be used for corporate work, may not join the VPN, and may not hold
corporate data. If hardware has not arrived, request a loaner — do not work from a personal machine
in the interim.

## Returns

Laptops are returned on the last working day. The offboarding ticket tracks the return; access
revocation is independent and happens within one hour regardless of whether the hardware has been
returned.
