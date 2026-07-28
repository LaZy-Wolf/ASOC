---
doc_type: runbook
department: platform
owner: security-team
severity_scope: P1-P3
---

# Runbook: TLS Certificate Expiry

## Alert thresholds

| Days to expiry | Severity | Action |
|---|---|---|
| 30 | P4 ticket | Auto-filed to the owning team |
| 14 | P3 | Owning team must confirm a renewal plan |
| 7 | P2 | On-call takes ownership |
| Expired | P1 | Immediate incident |

## Renewal: automated certificates

Most public endpoints use cert-manager with Let's Encrypt. If one of these is approaching expiry,
the renewal has failed rather than not been attempted.

```
kubectl describe certificate <name> -n <namespace>
kubectl get certificaterequest -n <namespace>
```

The two failures that account for nearly all cases:

- **DNS-01 challenge failure** — the ACME solver cannot write the TXT record because the DNS API
  token has itself expired.
- **Rate limiting** — Let's Encrypt allows 5 duplicate certificates per week. A crash-looping
  cert-manager burns through this quickly.

## Renewal: internal PKI certificates

Internal service-to-service certificates are issued by the internal CA and are **not** automated.
They are renewed by the security team on request. File a ticket with at least ten business days of
lead time; renewal requires a signing ceremony that is scheduled weekly.

## Expired certificate in production

1. Declare a P1.
2. If the endpoint is public and behind the CDN, the fastest mitigation is to fail over to the CDN's
   managed certificate. This takes about five minutes and is reversible.
3. If internal, there is no fast path. Contact the security on-call directly — the weekly ceremony
   can be convened out of band for a P1, but only by the security on-call.

## Do not

Do not disable certificate verification on clients as a mitigation. This has happened twice and both
times the flag survived into the next release.
