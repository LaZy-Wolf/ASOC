---
doc_type: runbook
department: platform
owner: api-team
severity_scope: P2-P3
---

# Runbook: API Latency Spike

## Trigger

The `api_p99_latency` alert fires when p99 response time on the public API exceeds 2000ms for five
consecutive minutes. This is a P2 by default and escalates to P1 if the error rate also crosses 5%.

## Triage order

Work these in order. Each step is cheap and rules out a large class of causes.

### 1. Is it one endpoint or all of them?

Check the latency breakdown by route in Grafana. A single slow route is almost always a query or a
downstream dependency. Latency across every route points at the database, the pooler, or the host.

### 2. Check database connection saturation

The most common cause of a broad latency spike is pgbouncer pool exhaustion, not the database
itself. If `pgbouncer_pools_cl_waiting` is non-zero, requests are queuing for a connection.

Raising the pool size is a temporary mitigation, not a fix. It shifts the queue into the database.

### 3. Check for a slow query

```
SELECT pid, now() - query_start AS duration, state, query
FROM pg_stat_activity
WHERE state != 'idle' AND now() - query_start > interval '5 seconds'
ORDER BY duration DESC;
```

A single long-running analytical query can starve the pool. Cancel it with `pg_cancel_backend(pid)`
before reaching for `pg_terminate_backend`.

### 4. Check downstream dependencies

The payments and auth services are the usual suspects. Their status is on the dependency dashboard.
If a downstream is degraded, the correct action is to shed load with the circuit breaker rather than
scaling the API tier.

## Mitigations

| Situation | Action |
|---|---|
| Pool exhaustion, no slow query | Scale API replicas; investigate request volume |
| One slow query | Cancel it, then file a ticket against the owning team |
| Downstream degraded | Enable circuit breaker for that dependency |
| Host-level CPU saturation | Cordon the node and let the scheduler rebalance |

## Do not

Do not restart the API deployment as a first move. It clears the symptom, destroys the evidence, and
the spike returns within the hour.
