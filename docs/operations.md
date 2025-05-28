# Operations Runbook - Reddit Sentiment Analysis Pipeline

## Overview

This runbook provides comprehensive operational procedures for managing the Reddit Sentiment Analysis Pipeline in production environments. It covers daily operations, maintenance tasks, scaling procedures, and standard operating procedures (SOPs) for production support teams.

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Weekly Maintenance](#weekly-maintenance)
3. [Monthly Procedures](#monthly-procedures)
4. [Scaling Operations](#scaling-operations)
5. [Deployment Procedures](#deployment-procedures)
6. [Backup and Recovery](#backup-and-recovery)
7. [Security Operations](#security-operations)
8. [Performance Tuning](#performance-tuning)
9. [Capacity Planning](#capacity-planning)
10. [Emergency Procedures](#emergency-procedures)

## Daily Operations

### Morning Health Check (Start of Business)

Execute this checklist every weekday morning:

```bash
#!/bin/bash
# Daily morning health check script

echo "🌅 Starting Daily Health Check - $(date)"
echo "================================================"

# 1. Check all services are running
echo "🔍 Checking service status..."
kubectl get pods -o wide | grep -E "(reddit-|sentiment-)"
echo ""

# 2. Verify API endpoints
echo "🌐 Testing API endpoints..."
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/metrics | grep -c "^# HELP"
echo ""

# 3. Check database connectivity
echo "🗄️ Testing database connectivity..."
psql -h localhost -U reddit_user -d reddit_sentiment -c "SELECT COUNT(*) as post_count FROM reddit_posts WHERE created_at > NOW() - INTERVAL '24 hours';"
echo ""

# 4. Verify queue depths
echo "📊 Checking queue depths..."
echo "Posts queue: $(redis-cli llen reddit:posts:queue)"
echo "Comments queue: $(redis-cli llen reddit:comments:queue)"
echo "Failed queue: $(redis-cli llen reddit:failed:queue)"
echo ""

# 5. Check disk space
echo "💾 Checking disk space..."
df -h | grep -E "(/$|/data|/var/lib/docker)"
echo ""

# 6. Review overnight alerts
echo "🚨 Checking for overnight alerts..."
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | select(.state=="firing") | {alertname: .labels.alertname, severity: .labels.severity}'
echo ""

# 7. Check processing rates
echo "⚡ Checking processing rates..."
echo "Posts processed (last hour): $(redis-cli get reddit:stats:posts_processed_hourly)"
echo "Comments processed (last hour): $(redis-cli get reddit:stats:comments_processed_hourly)"
echo ""

echo "✅ Daily health check completed - $(date)"
```

### Continuous Monitoring Tasks

#### Real-time Metrics Review

Check these metrics throughout the day:

```bash
# System resource utilization
kubectl top nodes
kubectl top pods --sort-by=memory | head -20

# Application metrics
curl -s http://localhost:8000/metrics | grep -E "(request_duration|queue_depth|error_rate)"

# Queue processing rates
watch -n 30 'redis-cli llen reddit:posts:queue; redis-cli llen reddit:comments:queue'
```

#### Log Monitoring

```bash
# Monitor error logs in real-time
kubectl logs -f -l app=reddit-sentiment-api | grep -i error

# Check for rate limiting issues
kubectl logs -l app=reddit-data-collector | grep -i "rate.*limit" | tail -10

# Monitor database performance
tail -f /var/log/postgresql/postgresql.log | grep -E "(slow|error|connection)"
```

### End of Day Procedures

```bash
#!/bin/bash
# End of day operational summary

echo "🌆 End of Day Summary - $(date)"
echo "======================================="

# Generate daily metrics report
echo "📈 Daily Processing Summary:"
echo "Posts collected: $(redis-cli get reddit:stats:posts_collected_daily)"
echo "Comments collected: $(redis-cli get reddit:stats:comments_collected_daily)"
echo "Sentiment analyses performed: $(redis-cli get reddit:stats:analyses_performed_daily)"
echo "API requests served: $(redis-cli get reddit:stats:api_requests_daily)"
echo ""

# Check for any critical alerts
echo "🚨 Active Critical Alerts:"
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | select(.labels.severity=="critical") | .labels.alertname'
echo ""

# Backup status verification
echo "💾 Backup Status:"
ls -la /backups/daily/ | tail -3
echo ""

# Reset daily counters
redis-cli set reddit:stats:posts_collected_daily 0
redis-cli set reddit:stats:comments_collected_daily 0
redis-cli set reddit:stats:analyses_performed_daily 0
redis-cli set reddit:stats:api_requests_daily 0

echo "✅ End of day procedures completed"
```

## Weekly Maintenance

### Sunday Maintenance Window (Weekly)

Execute every Sunday during low-traffic hours:

```bash
#!/bin/bash
# Weekly maintenance script

echo "🛠️ Starting Weekly Maintenance - $(date)"
echo "=========================================="

# 1. Database maintenance
echo "🗄️ Performing database maintenance..."
psql -h localhost -U reddit_user -d reddit_sentiment -c "VACUUM ANALYZE;"
psql -h localhost -U reddit_user -d reddit_sentiment -c "REINDEX DATABASE reddit_sentiment;"

# 2. Clean up old data (keep 90 days)
echo "🧹 Cleaning up old data..."
psql -h localhost -U reddit_user -d reddit_sentiment -c "
DELETE FROM reddit_posts WHERE created_at < NOW() - INTERVAL '90 days';
DELETE FROM reddit_comments WHERE created_at < NOW() - INTERVAL '90 days';
"

# 3. Container image cleanup
echo "🐳 Cleaning up Docker images..."
docker image prune -f
docker volume prune -f

# 4. Log rotation and cleanup
echo "📋 Rotating logs..."
find /var/log -name "*.log" -mtime +30 -delete
journalctl --vacuum-time=30d

# 5. Update system packages (if approved)
echo "📦 Checking for system updates..."
apt list --upgradable | grep -E "(security|critical)"

# 6. Backup verification
echo "💾 Verifying weekly backup..."
pg_dump -h localhost -U reddit_user reddit_sentiment | gzip > /backups/weekly/reddit_sentiment_$(date +%Y%m%d).sql.gz

# 7. Performance metrics collection
echo "📊 Collecting weekly performance metrics..."
psql -h localhost -U reddit_user -d reddit_sentiment -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public' 
ORDER BY tablename, attname;
" > /reports/weekly_performance_$(date +%Y%m%d).txt

echo "✅ Weekly maintenance completed - $(date)"
```

### Weekly Capacity Review

```bash
# Resource utilization trending
kubectl top nodes --use-protocol-buffers=false > /reports/weekly_node_usage_$(date +%Y%m%d).txt
kubectl top pods --all-namespaces --sort-by=memory > /reports/weekly_pod_usage_$(date +%Y%m%d).txt

# Database growth analysis
psql -h localhost -U reddit_user -d reddit_sentiment -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as bytes
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
" > /reports/weekly_database_growth_$(date +%Y%m%d).txt

# Generate weekly operational report
python3 /scripts/generate_weekly_report.py
```

## Monthly Procedures

### First Sunday of Month - Comprehensive Review

```bash
#!/bin/bash
# Monthly comprehensive maintenance

echo "📅 Starting Monthly Maintenance - $(date)"
echo "========================================="

# 1. Full system backup
echo "💾 Creating full system backup..."
tar -czf /backups/monthly/system_backup_$(date +%Y%m%d).tar.gz \
    /home/yasar/cicd_project \
    /etc/kubernetes \
    /var/lib/docker/volumes

# 2. Security updates
echo "🔒 Applying security updates..."
apt update && apt upgrade -y

# 3. Certificate renewal check
echo "🔐 Checking SSL certificates..."
openssl x509 -in /etc/ssl/certs/reddit-sentiment.crt -text -noout | grep "Not After"

# 4. Performance baseline update
echo "📊 Updating performance baselines..."
python3 /scripts/update_performance_baselines.py

# 5. Capacity planning analysis
echo "📈 Performing capacity analysis..."
python3 /scripts/capacity_planning_analysis.py

# 6. Dependency updates check
echo "📦 Checking for dependency updates..."
pip list --outdated > /reports/monthly_outdated_packages_$(date +%Y%m%d).txt

# 7. Model performance review
echo "🤖 Reviewing ML model performance..."
python3 /scripts/model_performance_review.py

echo "✅ Monthly maintenance completed - $(date)"
```

### Monthly Security Review

```bash
# Security audit checklist
echo "🔍 Monthly Security Audit - $(date)"

# Check for CVEs in dependencies
safety check --json > /reports/security/cve_report_$(date +%Y%m%d).json

# Review access logs
grep -E "(4[0-9]{2}|5[0-9]{2})" /var/log/nginx/access.log | tail -100

# Check for unusual API usage patterns
psql -h localhost -U reddit_user -d reddit_sentiment -c "
SELECT 
    client_ip,
    COUNT(*) as request_count,
    MIN(timestamp) as first_request,
    MAX(timestamp) as last_request
FROM api_access_logs 
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY client_ip 
HAVING COUNT(*) > 10000 
ORDER BY request_count DESC;
"

# Verify backup integrity
pg_restore --list /backups/monthly/system_backup_$(date +%Y%m%d).tar.gz > /dev/null
echo "Backup integrity: $?"
```

## Scaling Operations

### Horizontal Scaling Procedures

#### Scale Up (Increased Load)

```bash
#!/bin/bash
# Scale up procedure for high load

echo "⬆️ Scaling up services for increased load"

# 1. Scale API services
kubectl scale deployment reddit-sentiment-api --replicas=5
kubectl scale deployment sentiment-workers --replicas=10

# 2. Increase database connections
psql -h localhost -U reddit_user -d reddit_sentiment -c "ALTER SYSTEM SET max_connections = 300;"
psql -h localhost -U reddit_user -d reddit_sentiment -c "SELECT pg_reload_conf();"

# 3. Scale Redis cluster
kubectl scale statefulset redis --replicas=3

# 4. Update resource limits
kubectl patch deployment reddit-sentiment-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"memory":"4Gi","cpu":"2"}}}]}}}}'

# 5. Enable horizontal pod autoscaler
kubectl autoscale deployment reddit-sentiment-api --cpu-percent=70 --min=3 --max=10
kubectl autoscale deployment sentiment-workers --cpu-percent=80 --min=5 --max=20

echo "✅ Scale up completed"
```

#### Scale Down (Reduced Load)

```bash
#!/bin/bash
# Scale down procedure for reduced load

echo "⬇️ Scaling down services for reduced load"

# 1. Remove autoscalers
kubectl delete hpa reddit-sentiment-api
kubectl delete hpa sentiment-workers

# 2. Scale down gradually
kubectl scale deployment reddit-sentiment-api --replicas=2
kubectl scale deployment sentiment-workers --replicas=3

# 3. Reduce resource limits
kubectl patch deployment reddit-sentiment-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"memory":"2Gi","cpu":"1"}}}]}}}}'

# 4. Scale down Redis if appropriate
kubectl scale statefulset redis --replicas=1

echo "✅ Scale down completed"
```

### Vertical Scaling Procedures

```bash
# Increase memory allocation
kubectl patch deployment reddit-sentiment-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"requests":{"memory":"2Gi"},"limits":{"memory":"4Gi"}}}]}}}}'

# Increase CPU allocation
kubectl patch deployment reddit-sentiment-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"requests":{"cpu":"1"},"limits":{"cpu":"2"}}}]}}}}'

# Monitor impact
kubectl top pods -l app=reddit-sentiment-api
```

## Deployment Procedures

### Blue-Green Deployment

```bash
#!/bin/bash
# Blue-green deployment procedure

echo "🔄 Starting blue-green deployment"

# 1. Deploy green environment
kubectl apply -f k8s/green-deployment.yaml

# 2. Wait for green to be ready
kubectl wait --for=condition=available --timeout=300s deployment/reddit-sentiment-api-green

# 3. Run health checks on green
GREEN_POD=$(kubectl get pod -l app=reddit-sentiment-api-green -o jsonpath='{.items[0].metadata.name}')
kubectl exec $GREEN_POD -- curl -f http://localhost:8000/health

# 4. Switch traffic to green
kubectl patch service reddit-sentiment-api -p '{"spec":{"selector":{"version":"green"}}}'

# 5. Monitor for issues
sleep 300
ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query?query=rate\(http_requests_total\{status=~\"5..\"\}\[5m\]\) | jq '.data.result[0].value[1]')

if [ "$(echo "$ERROR_RATE > 0.01" | bc)" -eq 1 ]; then
    echo "❌ High error rate detected, rolling back"
    kubectl patch service reddit-sentiment-api -p '{"spec":{"selector":{"version":"blue"}}}'
    exit 1
fi

# 6. Cleanup blue environment
kubectl delete deployment reddit-sentiment-api-blue

echo "✅ Blue-green deployment completed successfully"
```

### Rolling Update Procedure

```bash
#!/bin/bash
# Rolling update procedure

echo "🔄 Starting rolling update"

# 1. Update deployment with new image
kubectl set image deployment/reddit-sentiment-api api=reddit-sentiment-api:$NEW_VERSION

# 2. Monitor rollout
kubectl rollout status deployment/reddit-sentiment-api --timeout=600s

# 3. Verify health
kubectl get pods -l app=reddit-sentiment-api
curl -f http://localhost:8000/health

# 4. If issues, rollback
if [ $? -ne 0 ]; then
    echo "❌ Health check failed, rolling back"
    kubectl rollout undo deployment/reddit-sentiment-api
    kubectl rollout status deployment/reddit-sentiment-api
fi

echo "✅ Rolling update completed"
```

## Backup and Recovery Operations

### Automated Backup Procedures

```bash
#!/bin/bash
# Automated backup script (runs via cron)

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/automated"

echo "💾 Starting automated backup - $BACKUP_DATE"

# 1. Database backup
pg_dump -h localhost -U reddit_user reddit_sentiment | gzip > "$BACKUP_DIR/db_$BACKUP_DATE.sql.gz"

# 2. Redis snapshot
redis-cli bgsave
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$BACKUP_DATE.rdb"

# 3. Configuration backup
tar -czf "$BACKUP_DIR/config_$BACKUP_DATE.tar.gz" \
    /home/yasar/cicd_project/config \
    /home/yasar/cicd_project/k8s \
    /home/yasar/cicd_project/helm

# 4. Model files backup
tar -czf "$BACKUP_DIR/models_$BACKUP_DATE.tar.gz" /models

# 5. Cleanup old backups (keep 30 days)
find $BACKUP_DIR -type f -mtime +30 -delete

# 6. Upload to cloud storage (if configured)
if [ -n "$AWS_S3_BUCKET" ]; then
    aws s3 cp "$BACKUP_DIR/db_$BACKUP_DATE.sql.gz" "s3://$AWS_S3_BUCKET/backups/"
    aws s3 cp "$BACKUP_DIR/config_$BACKUP_DATE.tar.gz" "s3://$AWS_S3_BUCKET/backups/"
fi

echo "✅ Automated backup completed - $BACKUP_DATE"
```

### Recovery Procedures

#### Database Recovery

```bash
#!/bin/bash
# Database recovery procedure

BACKUP_FILE="$1"
RECOVERY_DB="reddit_sentiment_recovery_$(date +%Y%m%d)"

echo "🔄 Starting database recovery from $BACKUP_FILE"

# 1. Create recovery database
createdb -h localhost -U reddit_user $RECOVERY_DB

# 2. Restore from backup
gunzip -c $BACKUP_FILE | psql -h localhost -U reddit_user -d $RECOVERY_DB

# 3. Verify data integrity
RECORD_COUNT=$(psql -h localhost -U reddit_user -d $RECOVERY_DB -t -c "SELECT COUNT(*) FROM reddit_posts;")
echo "Recovered records: $RECORD_COUNT"

# 4. If verification passes, switch to recovery database
read -p "Switch to recovery database? (y/N): " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Stop applications
    kubectl scale deployment reddit-sentiment-api --replicas=0
    
    # Rename databases
    psql -h localhost -U reddit_user -c "ALTER DATABASE reddit_sentiment RENAME TO reddit_sentiment_old;"
    psql -h localhost -U reddit_user -c "ALTER DATABASE $RECOVERY_DB RENAME TO reddit_sentiment;"
    
    # Restart applications
    kubectl scale deployment reddit-sentiment-api --replicas=3
fi

echo "✅ Database recovery completed"
```

## Security Operations

### Daily Security Checks

```bash
#!/bin/bash
# Daily security monitoring

echo "🔒 Daily Security Check - $(date)"

# 1. Check for failed login attempts
grep "Failed password" /var/log/auth.log | tail -10

# 2. Monitor API authentication failures
kubectl logs -l app=reddit-sentiment-api | grep "401\|403" | tail -10

# 3. Check for unusual network activity
netstat -ant | grep :8000 | wc -l

# 4. Verify certificate status
openssl s_client -connect localhost:443 -servername reddit-sentiment.local < /dev/null 2>/dev/null | openssl x509 -noout -dates

# 5. Check for security updates
apt list --upgradable | grep -i security

echo "✅ Daily security check completed"
```

### Incident Response Procedures

```bash
#!/bin/bash
# Security incident response

INCIDENT_ID="$1"
INCIDENT_TYPE="$2"

echo "🚨 Security Incident Response - ID: $INCIDENT_ID, Type: $INCIDENT_TYPE"

# 1. Immediate containment
case $INCIDENT_TYPE in
    "unauthorized_access")
        echo "🔒 Implementing access controls"
        # Revoke all active sessions
        redis-cli flushdb
        # Force password reset for all users
        psql -h localhost -U reddit_user -d reddit_sentiment -c "UPDATE users SET force_password_reset = true;"
        ;;
    "ddos_attack")
        echo "🛡️ Implementing DDoS protection"
        # Enable rate limiting
        kubectl apply -f security/rate-limiting.yaml
        ;;
    "data_breach")
        echo "🔐 Securing sensitive data"
        # Encrypt sensitive tables
        psql -h localhost -U reddit_user -d reddit_sentiment -c "UPDATE reddit_posts SET content = encrypt(content, 'encryption_key') WHERE content IS NOT NULL;"
        ;;
esac

# 2. Evidence collection
mkdir -p /incident_response/$INCIDENT_ID
kubectl logs --all-containers=true --since=1h > /incident_response/$INCIDENT_ID/k8s_logs.txt
cp /var/log/nginx/access.log /incident_response/$INCIDENT_ID/
cp /var/log/nginx/error.log /incident_response/$INCIDENT_ID/

# 3. Notification
echo "Incident $INCIDENT_ID detected at $(date)" | mail -s "Security Incident Alert" security-team@company.com

echo "✅ Initial incident response completed for $INCIDENT_ID"
```

## Performance Tuning

### Database Performance Optimization

```sql
-- Monthly database optimization queries

-- Update table statistics
ANALYZE;

-- Rebuild indexes if fragmented
REINDEX INDEX CONCURRENTLY idx_reddit_posts_created_at;
REINDEX INDEX CONCURRENTLY idx_reddit_posts_subreddit;

-- Check for slow queries
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
WHERE mean_time > 100 
ORDER BY total_time DESC 
LIMIT 20;

-- Optimize autovacuum settings
ALTER TABLE reddit_posts SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE reddit_comments SET (autovacuum_vacuum_scale_factor = 0.1);
```

### Application Performance Tuning

```bash
# Optimize Python application
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Tune gunicorn workers
kubectl set env deployment/reddit-sentiment-api GUNICORN_WORKERS=4
kubectl set env deployment/reddit-sentiment-api GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker

# Optimize Redis configuration
redis-cli config set save "900 1 300 10 60 10000"
redis-cli config set maxmemory-policy allkeys-lru
```

## Capacity Planning

### Monthly Capacity Assessment

```bash
#!/bin/bash
# Monthly capacity planning report

echo "📊 Monthly Capacity Assessment - $(date)"

# 1. Resource utilization trends
kubectl top nodes --use-protocol-buffers=false
kubectl top pods --all-namespaces --sort-by=memory | head -20

# 2. Database growth analysis
psql -h localhost -U reddit_user -d reddit_sentiment -c "
SELECT 
    DATE(created_at) as date,
    COUNT(*) as posts_per_day,
    pg_size_pretty(SUM(LENGTH(content))) as data_size
FROM reddit_posts 
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
"

# 3. API usage trends
echo "API Requests per day (last 30 days):"
grep "$(date -d '30 days ago' +%Y-%m)" /var/log/nginx/access.log | wc -l

# 4. Projected growth
python3 /scripts/capacity_projection.py

# 5. Recommendations
echo "📈 Capacity Recommendations:"
echo "- Current cluster can handle estimated load for next 3 months"
echo "- Consider adding 2 more worker nodes by month 4"
echo "- Database storage will need expansion in 6 months"

echo "✅ Capacity assessment completed"
```

## Emergency Procedures

### System Outage Response

```bash
#!/bin/bash
# Complete system outage response

echo "🚨 EMERGENCY: System Outage Response"

# 1. Immediate assessment
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running

# 2. Critical service restoration priority
CRITICAL_SERVICES=("postgres" "redis" "reddit-sentiment-api")

for service in "${CRITICAL_SERVICES[@]}"; do
    echo "Restoring $service..."
    kubectl rollout restart deployment/$service
    kubectl wait --for=condition=available --timeout=300s deployment/$service
done

# 3. Health verification
curl -f http://localhost:8000/health || echo "API still down"
redis-cli ping || echo "Redis still down"
psql -h localhost -U reddit_user -d reddit_sentiment -c "SELECT 1;" || echo "Database still down"

# 4. Notification
echo "Emergency response initiated at $(date)" | mail -s "URGENT: System Outage Response" ops-team@company.com

echo "✅ Emergency response phase 1 completed"
```

### Data Corruption Recovery

```bash
#!/bin/bash
# Data corruption emergency recovery

echo "🚨 EMERGENCY: Data Corruption Recovery"

# 1. Stop all data writes immediately
kubectl scale deployment reddit-data-collector --replicas=0
kubectl scale deployment sentiment-workers --replicas=0

# 2. Assess corruption extent
psql -h localhost -U reddit_user -d reddit_sentiment -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename)) as size,
    (SELECT COUNT(*) FROM information_schema.constraint_violations) as violations
FROM pg_tables 
WHERE schemaname = 'public';
"

# 3. Restore from most recent clean backup
LATEST_BACKUP=$(ls -t /backups/automated/db_*.sql.gz | head -1)
echo "Restoring from: $LATEST_BACKUP"

# Create recovery database
createdb -h localhost -U reddit_user reddit_sentiment_recovery
gunzip -c $LATEST_BACKUP | psql -h localhost -U reddit_user -d reddit_sentiment_recovery

# 4. Verify backup integrity
BACKUP_COUNT=$(psql -h localhost -U reddit_user -d reddit_sentiment_recovery -t -c "SELECT COUNT(*) FROM reddit_posts;")
echo "Backup contains $BACKUP_COUNT posts"

echo "✅ Emergency data recovery initiated - manual intervention required"
```

---

This operations runbook provides comprehensive procedures for managing the Reddit Sentiment Analysis Pipeline in production. Regular updates should be made based on operational experience and system changes.
