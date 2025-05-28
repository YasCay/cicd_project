# Monitoring Runbook

## Reddit Sentiment Analysis Pipeline - Monitoring and Operations Runbook

This runbook provides operational procedures for monitoring, troubleshooting, and maintaining the Reddit Sentiment Analysis Pipeline in production.

## Table of Contents

1. [Alert Response Procedures](#alert-response-procedures)
2. [Health Check Procedures](#health-check-procedures)
3. [Performance Monitoring](#performance-monitoring)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Escalation Procedures](#escalation-procedures)
6. [Maintenance Windows](#maintenance-windows)
7. [Emergency Procedures](#emergency-procedures)

## Alert Response Procedures

### Critical Alerts

#### Service Down Alert

**Alert**: `RedditSentimentPipelineDown`
**Severity**: Critical
**Response Time**: Immediate (within 5 minutes)

**Investigation Steps**:
1. Check service status:
   ```bash
   sudo systemctl status reddit-sentiment-pipeline.service
   sudo systemctl status reddit-sentiment-monitor.service
   ```

2. Check recent logs:
   ```bash
   sudo journalctl -u reddit-sentiment-pipeline.service -n 100
   tail -50 /home/cayir/cicd_project/logs/reddit_sentiment_errors.log
   ```

3. Check system resources:
   ```bash
   htop
   df -h
   free -h
   ```

**Resolution Steps**:
1. If service crashed, restart it:
   ```bash
   sudo systemctl restart reddit-sentiment-pipeline.service
   ```

2. If system resources are exhausted:
   ```bash
   # Clear temporary files
   sudo find /tmp -type f -atime +1 -delete
   
   # Restart if necessary
   sudo systemctl restart reddit-sentiment-pipeline.service
   ```

3. If persistent failures, investigate logs and escalate.

#### Disk Space Critical

**Alert**: `DiskSpaceRunningLow`
**Severity**: Critical
**Response Time**: Within 10 minutes

**Investigation Steps**:
1. Check disk usage:
   ```bash
   df -h
   du -sh /home/cayir/cicd_project/*
   ```

2. Identify large files:
   ```bash
   find /home/cayir/cicd_project -type f -size +100M -ls
   ```

**Resolution Steps**:
1. Clean up old log files:
   ```bash
   find /home/cayir/cicd_project/logs -name "*.log.*" -mtime +7 -delete
   ```

2. Clean up old backups:
   ```bash
   python3 /home/cayir/cicd_project/scripts/backup_manager.py cleanup
   ```

3. Compress large CSV files:
   ```bash
   find /home/cayir/cicd_project/data -name "*.csv" -size +50M -exec gzip {} \;
   ```

### Warning Alerts

#### High CPU Usage

**Alert**: `HighCPUUsage`
**Severity**: Warning
**Response Time**: Within 15 minutes

**Investigation Steps**:
1. Check CPU usage:
   ```bash
   top -p $(pgrep -f reddit-sentiment)
   iostat -x 1 5
   ```

2. Check for CPU-intensive processes:
   ```bash
   ps aux --sort=-%cpu | head -10
   ```

**Resolution Steps**:
1. If sentiment analysis is causing high CPU:
   ```bash
   # Reduce batch size in configuration
   sed -i 's/SENTIMENT_BATCH_SIZE=32/SENTIMENT_BATCH_SIZE=16/' /home/cayir/cicd_project/config/production.env
   sudo systemctl restart reddit-sentiment-pipeline.service
   ```

2. If other processes are consuming CPU, investigate and optimize.

#### High Memory Usage

**Alert**: `HighMemoryUsage`
**Severity**: Warning
**Response Time**: Within 15 minutes

**Investigation Steps**:
1. Check memory usage:
   ```bash
   free -h
   ps aux --sort=-%mem | head -10
   ```

2. Check for memory leaks:
   ```bash
   pmap $(pgrep -f reddit-sentiment)
   ```

**Resolution Steps**:
1. Restart the service to clear memory:
   ```bash
   sudo systemctl restart reddit-sentiment-pipeline.service
   ```

2. If persistent, reduce memory usage:
   ```bash
   # Reduce model cache size
   sed -i 's/SENTIMENT_MAX_LENGTH=512/SENTIMENT_MAX_LENGTH=256/' /home/cayir/cicd_project/config/production.env
   sudo systemctl restart reddit-sentiment-pipeline.service
   ```

#### Reddit API Errors

**Alert**: `RedditAPIErrors`
**Severity**: Warning
**Response Time**: Within 10 minutes

**Investigation Steps**:
1. Check Reddit API logs:
   ```bash
   grep -i "reddit.*error" /home/cayir/cicd_project/logs/reddit_sentiment_pipeline.log | tail -20
   ```

2. Test Reddit API connectivity:
   ```bash
   curl -H "User-Agent: Reddit Sentiment Pipeline v1.0.0" https://www.reddit.com/r/technology.json
   ```

**Resolution Steps**:
1. If rate limiting, reduce request frequency:
   ```bash
   # Increase delay between requests
   sed -i 's/REDDIT_API_RATE_LIMIT=60/REDDIT_API_RATE_LIMIT=30/' /home/cayir/cicd_project/config/production.env
   ```

2. If authentication issues, verify credentials:
   ```bash
   # Check Reddit API credentials (do not log them)
   python3 -c "
   import os
   os.chdir('/home/cayir/cicd_project')
   from apps.collector.collector import verify_reddit_credentials
   verify_reddit_credentials()
   "
   ```

## Health Check Procedures

### Automated Health Checks

The system performs automated health checks every 60 seconds:

- **Service Status**: Verifies the main service is running
- **Database Connectivity**: Tests SQLite database access
- **Reddit API**: Validates API connectivity and credentials
- **Sentiment Model**: Ensures FinBERT model is loaded
- **Disk Space**: Monitors available storage
- **Memory Usage**: Tracks memory consumption

### Manual Health Checks

#### Quick Health Check

```bash
# Check all health endpoints
curl -s http://localhost:8001/health | jq '.'
curl -s http://localhost:8001/health/database | jq '.'
curl -s http://localhost:8001/health/reddit-api | jq '.'
curl -s http://localhost:8001/health/sentiment-model | jq '.'
```

#### Comprehensive Health Check

```bash
# Run the health check script
python3 /home/cayir/cicd_project/scripts/health_check.py --comprehensive

# Check metrics endpoint
curl -s http://localhost:8000/metrics | grep -E "(reddit|sentiment|posts)"
```

#### Component-Specific Checks

**Database Health**:
```bash
# Test database connectivity
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "SELECT COUNT(*) FROM posts;"

# Check database size
ls -lh /home/cayir/cicd_project/data/reddit_sentiment.db
```

**Model Health**:
```bash
# Test sentiment analysis
python3 -c "
import sys
sys.path.append('/home/cayir/cicd_project')
from apps.collector.sentiment import SentimentAnalyzer
analyzer = SentimentAnalyzer()
result = analyzer.analyze_sentiment('This is a test message')
print(f'Sentiment analysis working: {result}')
"
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

1. **Processing Rate**: Posts processed per hour
2. **API Response Time**: Reddit API response latency
3. **Sentiment Analysis Speed**: Time per sentiment analysis
4. **Error Rate**: Percentage of failed operations
5. **Resource Utilization**: CPU, memory, and disk usage

### Performance Metrics Queries

**Prometheus Queries**:

```promql
# Processing rate (posts per hour)
rate(posts_processed_total[1h]) * 3600

# API response time (95th percentile)
histogram_quantile(0.95, rate(reddit_api_duration_seconds_bucket[5m]))

# Error rate percentage
(rate(errors_total[5m]) / rate(requests_total[5m])) * 100

# Memory usage percentage
(process_resident_memory_bytes / node_memory_MemTotal_bytes) * 100
```

### Performance Baselines

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Posts/hour | >50 | 20-50 | <20 |
| API Response Time | <2s | 2-5s | >5s |
| Sentiment Analysis | <1s | 1-3s | >3s |
| Error Rate | <1% | 1-5% | >5% |
| CPU Usage | <50% | 50-80% | >80% |
| Memory Usage | <60% | 60-85% | >85% |
| Disk Usage | <70% | 70-90% | >90% |

### Performance Optimization

**If processing is slow**:
1. Check CPU and memory usage
2. Verify database performance
3. Optimize sentiment analysis batch size
4. Consider parallel processing

**If API calls are slow**:
1. Check network connectivity
2. Verify Reddit API status
3. Reduce request frequency
4. Implement request caching

## Troubleshooting Guide

### Common Issues and Solutions

#### Service Fails to Start

**Symptoms**: Service status shows failed, logs show startup errors

**Troubleshooting**:
1. Check configuration file syntax:
   ```bash
   python3 -c "
   import configparser
   config = configparser.ConfigParser()
   config.read('/home/cayir/cicd_project/config/production.env')
   print('Configuration valid')
   "
   ```

2. Verify environment variables:
   ```bash
   systemctl show reddit-sentiment-pipeline.service --property=Environment
   ```

3. Check file permissions:
   ```bash
   ls -la /home/cayir/cicd_project/apps/collector/
   ```

**Resolution**:
- Fix configuration syntax errors
- Set missing environment variables
- Correct file permissions

#### Database Connection Issues

**Symptoms**: Database-related errors in logs

**Troubleshooting**:
1. Check database file exists and is readable:
   ```bash
   ls -la /home/cayir/cicd_project/data/reddit_sentiment.db
   ```

2. Test database connectivity:
   ```bash
   sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db ".tables"
   ```

3. Check disk space:
   ```bash
   df -h /home/cayir/cicd_project/data/
   ```

**Resolution**:
- Create missing database file
- Fix file permissions
- Free up disk space

#### Sentiment Analysis Errors

**Symptoms**: High sentiment analysis error rate

**Troubleshooting**:
1. Check model files:
   ```bash
   find ~/.cache/huggingface/ -name "*finbert*" -ls
   ```

2. Test model loading:
   ```bash
   python3 -c "
   from transformers import AutoTokenizer, AutoModelForSequenceClassification
   tokenizer = AutoTokenizer.from_pretrained('ProsusAI/finbert')
   model = AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')
   print('Model loaded successfully')
   "
   ```

**Resolution**:
- Re-download model files
- Increase memory allocation
- Reduce batch size

### Log Analysis

#### Important Log Patterns

**Critical Errors**:
```bash
grep -E "CRITICAL|ERROR" /home/cayir/cicd_project/logs/reddit_sentiment_pipeline.log
```

**API Issues**:
```bash
grep -E "reddit.*error|api.*fail" /home/cayir/cicd_project/logs/reddit_sentiment_pipeline.log
```

**Performance Issues**:
```bash
grep -E "slow|timeout|memory" /home/cayir/cicd_project/logs/reddit_sentiment_pipeline.log
```

#### Log Aggregation Commands

```bash
# Last hour's errors
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" /home/cayir/cicd_project/logs/reddit_sentiment_errors.log

# Error frequency analysis
awk '{print $4}' /home/cayir/cicd_project/logs/reddit_sentiment_errors.log | sort | uniq -c | sort -nr

# Performance trend analysis
grep "duration" /home/cayir/cicd_project/logs/reddit_sentiment_pipeline.log | tail -100
```

## Escalation Procedures

### Escalation Matrix

| Severity | Response Time | Primary Contact | Secondary Contact |
|----------|---------------|-----------------|-------------------|
| Critical | 5 minutes | On-call Engineer | DevOps Lead |
| High | 15 minutes | DevOps Team | Platform Team |
| Medium | 1 hour | Platform Team | Product Owner |
| Low | 4 hours | Development Team | - |

### Escalation Triggers

**Immediate Escalation (Critical)**:
- Service down for >5 minutes
- Data loss detected
- Security breach suspected
- Complete system failure

**Escalate to DevOps Lead**:
- Multiple consecutive failures
- Resource exhaustion
- Infrastructure issues
- Configuration problems

**Escalate to Product Owner**:
- Data quality issues
- Business logic problems
- Feature-related failures

### Contact Information

```bash
# Emergency contacts (example)
DevOps Lead: devops-lead@company.com
Platform Team: platform-team@company.com
On-call Engineer: Check PagerDuty rotation
Security Team: security@company.com
```

## Maintenance Windows

### Scheduled Maintenance

**Weekly Maintenance**: Sundays 02:00-04:00 UTC
- System updates
- Log rotation
- Performance optimization
- Backup verification

**Monthly Maintenance**: First Sunday 01:00-05:00 UTC
- Security updates
- Configuration reviews
- Disaster recovery testing
- Capacity planning

### Maintenance Procedures

#### Pre-maintenance Checklist

1. Create backup:
   ```bash
   python3 scripts/backup_manager.py create pre-maintenance-$(date +%Y%m%d)
   ```

2. Notify stakeholders
3. Prepare rollback plan
4. Stop non-critical services

#### Post-maintenance Checklist

1. Verify service functionality:
   ```bash
   curl http://localhost:8001/health
   python3 scripts/health_check.py --comprehensive
   ```

2. Check metrics and logs
3. Update documentation
4. Notify completion

## Emergency Procedures

### Emergency Contacts

- **Primary On-call**: Check rotation schedule
- **Secondary On-call**: Backup engineer
- **Escalation Manager**: DevOps Lead
- **Emergency Hotline**: +1-xxx-xxx-xxxx

### Emergency Response

#### Severity 1 Incident (Service Down)

1. **Immediate Response** (0-5 minutes):
   - Acknowledge alert
   - Check service status
   - Attempt automatic restart

2. **Initial Investigation** (5-15 minutes):
   - Review logs and metrics
   - Identify root cause
   - Implement quick fix if available

3. **Escalation** (15+ minutes):
   - If not resolved, escalate to on-call lead
   - Update incident status
   - Begin detailed investigation

#### Disaster Recovery

1. **Data Loss Event**:
   - Stop all services immediately
   - Assess extent of data loss
   - Restore from latest backup
   - Verify data integrity

2. **Security Incident**:
   - Isolate affected systems
   - Contact security team
   - Preserve logs and evidence
   - Follow security incident response plan

3. **Complete System Failure**:
   - Activate disaster recovery site
   - Restore from backups
   - Update DNS and routing
   - Verify full functionality

### Recovery Procedures

#### Service Recovery

```bash
# Full service restart
sudo systemctl stop reddit-sentiment-pipeline.timer
sudo systemctl stop reddit-sentiment-pipeline.service
sudo systemctl stop reddit-sentiment-monitor.service

# Wait 30 seconds
sleep 30

# Restart services
sudo systemctl start reddit-sentiment-pipeline.service
sudo systemctl start reddit-sentiment-monitor.service
sudo systemctl start reddit-sentiment-pipeline.timer

# Verify startup
sleep 60
curl http://localhost:8001/health
```

#### Data Recovery

```bash
# Restore from backup
python3 scripts/backup_manager.py restore latest

# Verify database integrity
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "PRAGMA integrity_check;"

# Restart services
sudo systemctl restart reddit-sentiment-pipeline.service
```

---

**Document Version**: 1.0  
**Last Updated**: May 28, 2025  
**Maintained By**: DevOps Team  
**Review Schedule**: Monthly
