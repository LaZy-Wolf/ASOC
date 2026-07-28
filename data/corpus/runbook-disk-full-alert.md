---
doc_type: runbook
department: platform
owner: infra-team
severity_scope: P2-P3
---

# Runbook: Disk Space Critical

## Trigger

`node_filesystem_avail_bytes` below 10% on any production host. Below 5% the alert escalates to P1,
because Postgres and the container runtime both fail in confusing ways when the disk is full rather
than merely tight.

## First: buy time

Before diagnosing, reclaim enough space that the host stays functional. This is safe on every
production host:

```
journalctl --vacuum-size=200M
docker system prune -f --filter "until=24h"
```

Do not delete anything under `/var/lib/postgresql` or `/var/lib/docker/volumes` to buy time. That is
data, not cache.

## Then: find the actual consumer

```
du -x -h -d 2 / 2>/dev/null | sort -rh | head -30
```

### Common causes, in order of frequency

1. **Log growth from a chatty deploy.** A service logging at DEBUG in production. Fix the log level;
   do not just rotate.
2. **Orphaned container images** after a series of failed deploys.
3. **Postgres WAL accumulation** because a replication slot is inactive. Check
   `pg_replication_slots` for slots with `active = false`. An inactive slot pins WAL forever and
   will fill the disk again in hours. Drop the slot only after confirming the standby is genuinely
   gone.
4. **Core dumps** in `/var/crash` from a repeatedly crashing process.

## Escalation

If free space is below 5% and you cannot reclaim it within fifteen minutes, page the infra on-call.
A full disk on the database host is a P1.

## Prevention

Every service must declare a log retention policy. Hosts without a retention policy are flagged in
the monthly infrastructure review.
