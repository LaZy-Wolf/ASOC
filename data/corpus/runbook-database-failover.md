---
doc_type: runbook
department: platform
owner: database-team
severity_scope: P1-P2
---

# Runbook: Primary Database Failover

## When to use this runbook

Use this runbook when the primary Postgres cluster (`prod-pg-primary`) is unreachable, is returning
sustained write errors, or replication lag to the standby exceeds 300 seconds. Do not use it for
read-only slowness — see the API latency runbook instead.

## Preconditions

- You are on the on-call rotation or have been explicitly paged in.
- You have `pg-operator` role in the production IAM group.
- A standby (`prod-pg-standby-a` or `prod-pg-standby-b`) is reporting healthy in Grafana.

## Procedure

### 1. Confirm the primary is actually down

Run the health probe from the bastion, not from your laptop. A VPN hiccup looks identical to a
database outage from outside the network.

```
psql -h prod-pg-primary -U probe -c "SELECT 1" --connect-timeout=5
```

If this succeeds, the database is up and the problem is elsewhere. Stop here.

### 2. Declare the incident

Failover is a P1 by definition. Open the incident channel before touching anything — the audit trail
matters more than thirty seconds of latency.

### 3. Fence the old primary

Stop the primary before promoting a standby. Promoting without fencing risks split-brain, which is
substantially worse than the outage you are fixing.

```
patronictl -c /etc/patroni.yml pause --wait
patronictl -c /etc/patroni.yml restart prod-pg-primary --force
```

### 4. Promote the standby

Choose the standby with the lowest replication lag. `patronictl list` shows lag per node.

```
patronictl -c /etc/patroni.yml failover --candidate prod-pg-standby-a
```

### 5. Verify

- Writes succeed against the new primary.
- Connection pooler (`pgbouncer`) has picked up the new topology; if not, reload it.
- Replication has re-established to at least one remaining standby.

### 6. Resume automatic failover

```
patronictl -c /etc/patroni.yml resume
```

## Rollback

There is no rollback for a promotion. If the promoted standby is also unhealthy, promote the second
standby rather than trying to un-promote.

## After the incident

A postmortem is required within five business days. See the change management policy for the
template and the review meeting cadence.
