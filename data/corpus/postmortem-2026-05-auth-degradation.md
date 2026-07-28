---
doc_type: postmortem
department: platform
owner: identity-team
incident_id: INC-2026-0518
severity: P1
date: 2026-05-18
---

# Postmortem: Authentication Degradation, 18 May 2026

## Summary

Login success rate fell to 34% for 2 hours 12 minutes. Cause was a readiness probe timeout shorter
than the identity service's cold start after a dependency upgrade, so healthy pods were killed
before they could serve traffic.

## Impact

- 08:14–10:26 UTC, 132 minutes
- Login success rate 34% at worst
- Already-authenticated sessions unaffected
- No data loss or exposure

## Timeline

| Time (UTC) | Event |
|---|---|
| 08:02 | Routine deploy of the identity service, including a JWT library upgrade. |
| 08:09 | Pods begin failing readiness and entering CrashLoopBackOff. |
| 08:14 | Login error rate crosses 5%. P2 declared. |
| 08:31 | Raised to P1 as the success rate falls below 50%. |
| 08:40 | Rollback attempted. It does not help — see below. |
| 09:15 | Cold start identified as slower than the 10s readiness timeout. |
| 09:44 | Readiness timeout raised to 45s and initial delay to 30s. |
| 10:04 | Pods stable, success rate climbing. |
| 10:26 | Recovered. |

## Root cause

The upgraded JWT library builds its key cache at startup. Cold start went from roughly 6 seconds to
roughly 24 seconds. The readiness probe timeout was 10 seconds with a 5-second initial delay, so
every pod was killed mid-startup.

## Why the rollback did not work

The rollback rolled back the deployment, but the rolled-back pods still had to cold start into a
cluster where none of their peers were serving. The resulting stampede meant even the 6-second cold
start could not complete under load. Rollback is not a universal escape hatch when the failure is
capacity-shaped.

## What went wrong beyond the trigger

**The crash loop was read as an application error.** Exit code 143 (SIGTERM) was assumed to be an
app crash. The crash-loop runbook did not at the time distinguish a failing readiness probe from an
application fault; the two look identical in the pod list.

**No staging signal.** Staging runs a fraction of production load and cold starts finish there
comfortably. The regression was invisible until production scale.

## Action items

| Action | Owner | Due |
|---|---|---|
| Add a "false crash loop" section to the crash-loop runbook | infra-team | 2026-05-25 |
| Startup probes on all latency-sensitive services, separate from readiness | identity-team | 2026-06-08 |
| Cold-start duration tracked as a release metric with a regression gate | identity-team | 2026-06-15 |
| Load-test staging at 30% of production before identity releases | identity-team | 2026-06-22 |
