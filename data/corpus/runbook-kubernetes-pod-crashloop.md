---
doc_type: runbook
department: platform
owner: infra-team
severity_scope: P2-P4
---

# Runbook: Pod CrashLoopBackOff

## Scope

A workload is restarting repeatedly. Severity depends on the workload, not the symptom: a
crash-looping batch job is a P4, a crash-looping payments API is a P1.

## Diagnose

### 1. Read the previous container's logs, not the current one

The current container has usually not produced the interesting output yet.

```
kubectl logs <pod> -n <ns> --previous
```

### 2. Check the exit code

```
kubectl describe pod <pod> -n <ns> | grep -A3 "Last State"
```

| Exit code | Meaning | Usual cause |
|---|---|---|
| 0 | Clean exit | Process is not meant to be long-running; wrong workload type |
| 1 | Application error | Read the logs |
| 137 | SIGKILL | OOMKilled — memory limit too low, or a leak |
| 139 | Segfault | Native dependency mismatch |
| 143 | SIGTERM | Being evicted; check node pressure |

### 3. OOMKilled specifically

`137` with `OOMKilled: true` means the container exceeded its memory limit. Raising the limit is
correct only if the workload genuinely needs the memory. If memory grows without bound across
restarts, it is a leak and raising the limit only lengthens the interval between crashes.

### 4. Failing readiness probe

A pod that starts, fails readiness, and gets killed looks like a crash loop but is not. Check
whether the probe timeout is shorter than the application's cold start. This is the most common
false crash loop after a dependency upgrade.

## Mitigation

Roll back to the last known good revision rather than debugging live:

```
kubectl rollout undo deployment/<name> -n <ns>
```

Rolling back is not a resolution. File a ticket against the owning team with the exit code and the
previous container's logs attached.
