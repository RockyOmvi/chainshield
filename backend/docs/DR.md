# ChainShield Disaster Recovery Plan

## Overview

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | 4 hours |
| RPO (Recovery Point Objective) | 1 hour |
| Backup Frequency | Hourly |
| Backup Retention | 30 days |

---

## Backup Strategy

### Database (PostgreSQL)

```bash
# Automated daily backup
pg_dump chainshield > backup_$(date +%Y%m%d).sql

# To S3
aws s3 cp backup_*.sql s3://chainshield-backups/db/
```

### Redis Cache

- Cache is ephemeral, no backup needed
- Warm cache on startup from DB

### Application Logs

- Shipped to S3 daily
- Retained for 90 days

---

## Recovery Procedures

### Scenario 1: Database Failure

1. Spin up new PostgreSQL instance
2. Restore from latest backup
3. Verify data integrity
4. Update connection string
5. Restart application

```bash
# Restore command
psql chainshield < backup_latest.sql
```

### Scenario 2: Application Crash

1. Deploy new container from latest image
2. Verify health endpoint
3. Route traffic

```bash
# Railway redeploy
railway up --force
```

### Scenario 3: Region Outage

1. Failover DNS to backup region
2. Start services in DR region
3. Restore DB from cross-region replica

---

## Runbook

### Health Checks

```bash
# Check API health
curl https://api.chainshield.io/health

# Check readiness
curl https://api.chainshield.io/ready
```

### Rollback

```bash
# Railway rollback
railway rollback
```

---

## Contacts

| Role | Contact |
|------|---------|
| On-call Engineer | oncall@chainshield.io |
| DevOps Lead | devops@chainshield.io |
| CTO | cto@chainshield.io |

---

## Testing

DR tests should be conducted quarterly:
- [ ] Database restore test
- [ ] Failover test
- [ ] Full recovery simulation
