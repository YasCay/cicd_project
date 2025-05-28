# Backup and Recovery Guide

## Reddit Sentiment Analysis Pipeline - Backup and Recovery Procedures

This document provides comprehensive procedures for backing up and recovering the Reddit Sentiment Analysis Pipeline in production environments.

## Table of Contents

1. [Backup Strategy](#backup-strategy)
2. [Automated Backup System](#automated-backup-system)
3. [Manual Backup Procedures](#manual-backup-procedures)
4. [Recovery Procedures](#recovery-procedures)
5. [Backup Verification](#backup-verification)
6. [Disaster Recovery](#disaster-recovery)
7. [Backup Monitoring](#backup-monitoring)
8. [Troubleshooting](#troubleshooting)

## Backup Strategy

### Backup Components

The backup system protects the following critical components:

1. **Application Data**
   - SQLite database (`reddit_sentiment.db`)
   - CSV output files
   - Processed data files

2. **Configuration Files**
   - Environment configuration (`production.env`)
   - Logging configuration (`logging.conf`)
   - Monitoring configuration (`monitoring.yml`)

3. **Application Code**
   - Python application files
   - Custom scripts and utilities
   - Systemd service definitions

4. **Logs and Metrics**
   - Application logs
   - Error logs
   - Metrics history (optional)

### Backup Types

#### Full Backup
- **Frequency**: Daily at 2:00 AM
- **Retention**: 30 days
- **Content**: All application data, configuration, and logs
- **Storage**: Local compressed archives

#### Incremental Backup
- **Frequency**: Every 6 hours
- **Retention**: 7 days
- **Content**: Changed files since last backup
- **Storage**: Local compressed diffs

#### Configuration Backup
- **Frequency**: On every configuration change
- **Retention**: 90 days
- **Content**: Configuration files only
- **Storage**: Version-controlled and local copies

### Backup Retention Policy

| Backup Type | Frequency | Retention | Storage Location |
|-------------|-----------|-----------|------------------|
| Full | Daily | 30 days | `/home/cayir/cicd_project/backups/daily/` |
| Incremental | 6 hours | 7 days | `/home/cayir/cicd_project/backups/incremental/` |
| Configuration | On change | 90 days | `/home/cayir/cicd_project/backups/config/` |
| Database | Hourly | 24 hours | `/home/cayir/cicd_project/backups/database/` |

## Automated Backup System

### Backup Manager Script

The `backup_manager.py` script provides comprehensive backup functionality:

```bash
# Create a full backup
python3 scripts/backup_manager.py create

# Create an incremental backup
python3 scripts/backup_manager.py create --type incremental

# List available backups
python3 scripts/backup_manager.py list

# Verify backup integrity
python3 scripts/backup_manager.py verify backup_20240528_120000.tar.gz

# Restore from backup
python3 scripts/backup_manager.py restore backup_20240528_120000.tar.gz

# Clean up old backups
python3 scripts/backup_manager.py cleanup
```

### Automated Backup Schedule

Automated backups are configured via cron jobs:

```bash
# View current backup schedule
crontab -l

# Example cron configuration
0 2 * * * /home/cayir/cicd_project/venv/bin/python /home/cayir/cicd_project/scripts/backup_manager.py create >> /home/cayir/cicd_project/logs/backup.log 2>&1
0 */6 * * * /home/cayir/cicd_project/venv/bin/python /home/cayir/cicd_project/scripts/backup_manager.py create --type incremental >> /home/cayir/cicd_project/logs/backup.log 2>&1
0 3 * * 0 /home/cayir/cicd_project/venv/bin/python /home/cayir/cicd_project/scripts/backup_manager.py cleanup >> /home/cayir/cicd_project/logs/backup.log 2>&1
```

### Backup Configuration

Backup behavior is configured in `config/production.env`:

```bash
# Backup settings
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_COMPRESSION=gzip
BACKUP_ENCRYPTION=true
BACKUP_REMOTE_SYNC=false
BACKUP_NOTIFICATION=true
BACKUP_RETENTION_DAYS=30
```

## Manual Backup Procedures

### Creating Manual Backups

#### Quick Database Backup

```bash
# Create database backup
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db ".backup /home/cayir/cicd_project/backups/manual/reddit_sentiment_$(date +%Y%m%d_%H%M%S).db"

# Verify backup
sqlite3 /home/cayir/cicd_project/backups/manual/reddit_sentiment_$(date +%Y%m%d_%H%M%S).db "PRAGMA integrity_check;"
```

#### Configuration Backup

```bash
# Create configuration backup
tar -czf /home/cayir/cicd_project/backups/manual/config_$(date +%Y%m%d_%H%M%S).tar.gz \
    -C /home/cayir/cicd_project \
    config/ \
    systemd/ \
    monitoring/alerting_rules.yml \
    monitoring/prometheus_config.yml
```

#### Full System Backup

```bash
# Create complete system backup
tar -czf /home/cayir/cicd_project/backups/manual/full_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    -C /home/cayir/cicd_project \
    --exclude='backups' \
    --exclude='logs/*.log.*' \
    --exclude='venv' \
    --exclude='__pycache__' \
    .

# Verify backup size and content
tar -tzvf /home/cayir/cicd_project/backups/manual/full_backup_$(date +%Y%m%d_%H%M%S).tar.gz | head -20
```

### Pre-Maintenance Backup

Before performing system maintenance:

```bash
# Stop services
sudo systemctl stop reddit-sentiment-pipeline.timer
sudo systemctl stop reddit-sentiment-pipeline.service

# Wait for processes to complete
sleep 30

# Create pre-maintenance backup
python3 scripts/backup_manager.py create --name "pre-maintenance-$(date +%Y%m%d)" --type full

# Verify backup
python3 scripts/backup_manager.py verify "pre-maintenance-$(date +%Y%m%d).tar.gz"
```

## Recovery Procedures

### Database Recovery

#### Simple Database Restore

```bash
# Stop the service
sudo systemctl stop reddit-sentiment-pipeline.service

# Backup current database (if corrupted)
mv /home/cayir/cicd_project/data/reddit_sentiment.db /home/cayir/cicd_project/data/reddit_sentiment.db.corrupted

# Restore from backup
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db ".restore /home/cayir/cicd_project/backups/daily/latest_database.db"

# Verify integrity
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "PRAGMA integrity_check;"

# Restart service
sudo systemctl start reddit-sentiment-pipeline.service
```

#### Database Recovery from Full Backup

```bash
# Extract database from full backup
tar -xzf /home/cayir/cicd_project/backups/daily/backup_20240528_020000.tar.gz \
    -C /tmp \
    data/reddit_sentiment.db

# Stop service
sudo systemctl stop reddit-sentiment-pipeline.service

# Replace database
cp /tmp/data/reddit_sentiment.db /home/cayir/cicd_project/data/

# Set permissions
chown cayir:cayir /home/cayir/cicd_project/data/reddit_sentiment.db
chmod 644 /home/cayir/cicd_project/data/reddit_sentiment.db

# Restart service
sudo systemctl start reddit-sentiment-pipeline.service
```

### Configuration Recovery

#### Restore Configuration Files

```bash
# Extract configuration from backup
tar -xzf /home/cayir/cicd_project/backups/config/config_20240528_120000.tar.gz \
    -C /home/cayir/cicd_project \
    config/

# Verify configuration
python3 -c "
import configparser
config = configparser.ConfigParser()
config.read('/home/cayir/cicd_project/config/production.env')
print('Configuration restored successfully')
"

# Restart services to apply configuration
sudo systemctl restart reddit-sentiment-pipeline.service
sudo systemctl restart reddit-sentiment-monitor.service
```

#### Systemd Service Recovery

```bash
# Extract systemd files from backup
tar -xzf /home/cayir/cicd_project/backups/daily/backup_20240528_020000.tar.gz \
    -C /tmp \
    systemd/

# Copy systemd files
sudo cp /tmp/systemd/*.service /etc/systemd/system/
sudo cp /tmp/systemd/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Re-enable services
sudo systemctl enable reddit-sentiment-pipeline.service
sudo systemctl enable reddit-sentiment-pipeline.timer
sudo systemctl enable reddit-sentiment-monitor.service
```

### Full System Recovery

#### Complete System Restore

```bash
# Stop all services
sudo systemctl stop reddit-sentiment-pipeline.timer
sudo systemctl stop reddit-sentiment-pipeline.service
sudo systemctl stop reddit-sentiment-monitor.service

# Backup current state (if needed)
mv /home/cayir/cicd_project /home/cayir/cicd_project.backup.$(date +%Y%m%d_%H%M%S)

# Create application directory
mkdir -p /home/cayir/cicd_project
cd /home/cayir/cicd_project

# Restore from backup
tar -xzf /path/to/backup/backup_20240528_020000.tar.gz -C /home/cayir/cicd_project

# Set permissions
chown -R cayir:cayir /home/cayir/cicd_project
chmod +x /home/cayir/cicd_project/scripts/*.sh

# Restore systemd files
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Start services
sudo systemctl start reddit-sentiment-pipeline.service
sudo systemctl start reddit-sentiment-monitor.service
sudo systemctl start reddit-sentiment-pipeline.timer

# Verify functionality
curl http://localhost:8001/health
```

### Point-in-Time Recovery

For recovering to a specific point in time:

```bash
# List available backups with timestamps
python3 scripts/backup_manager.py list --detailed

# Choose appropriate backup based on timestamp
# Example: Restore to state from 6 hours ago
BACKUP_FILE="backup_20240528_140000.tar.gz"

# Stop services
sudo systemctl stop reddit-sentiment-pipeline.timer
sudo systemctl stop reddit-sentiment-pipeline.service

# Restore specific backup
python3 scripts/backup_manager.py restore "$BACKUP_FILE"

# Verify restoration
python3 scripts/backup_manager.py verify-restore

# Start services
sudo systemctl start reddit-sentiment-pipeline.service
sudo systemctl start reddit-sentiment-pipeline.timer
```

## Backup Verification

### Automated Verification

The backup system automatically verifies:

1. **Backup Integrity**: Archive can be opened and extracted
2. **Database Integrity**: SQLite database passes integrity checks
3. **File Completeness**: All expected files are present
4. **Configuration Validity**: Configuration files are parseable

```bash
# Run comprehensive backup verification
python3 scripts/backup_manager.py verify --comprehensive backup_20240528_020000.tar.gz
```

### Manual Verification

#### Database Verification

```bash
# Extract and test database
tar -xzf backup_20240528_020000.tar.gz data/reddit_sentiment.db -O | \
sqlite3 /tmp/test_restore.db ".restore /dev/stdin"

# Check database integrity
sqlite3 /tmp/test_restore.db "PRAGMA integrity_check;"

# Check table structure
sqlite3 /tmp/test_restore.db ".schema"

# Check data count
sqlite3 /tmp/test_restore.db "SELECT COUNT(*) FROM posts;"

# Cleanup
rm /tmp/test_restore.db
```

#### Configuration Verification

```bash
# Extract and validate configuration
tar -xzf backup_20240528_020000.tar.gz config/ -C /tmp/

# Validate environment file
python3 -c "
import configparser
config = configparser.ConfigParser()
config.read('/tmp/config/production.env')
print('Environment configuration is valid')
"

# Validate logging configuration
python3 -c "
import logging.config
logging.config.fileConfig('/tmp/config/logging.conf')
print('Logging configuration is valid')
"

# Cleanup
rm -rf /tmp/config/
```

### Backup Testing Schedule

Regular backup testing schedule:

- **Daily**: Automated verification of latest backup
- **Weekly**: Manual restore test to staging environment
- **Monthly**: Full disaster recovery simulation
- **Quarterly**: Recovery time objective (RTO) testing

## Disaster Recovery

### Disaster Recovery Plan

#### Recovery Time Objectives (RTO)

| Scenario | Target RTO | Maximum Acceptable Data Loss |
|----------|------------|------------------------------|
| Database corruption | 30 minutes | 1 hour |
| Configuration loss | 15 minutes | None |
| Complete system failure | 2 hours | 6 hours |
| Hardware failure | 4 hours | 1 day |

#### Recovery Point Objectives (RPO)

- **Critical Data**: 1 hour (hourly database backups)
- **Configuration**: Immediate (change-triggered backups)
- **Application Code**: 1 day (daily full backups)
- **Logs**: 6 hours (included in incremental backups)

### Disaster Recovery Procedures

#### Scenario 1: Database Corruption

```bash
# 1. Detect corruption
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "PRAGMA integrity_check;"

# 2. Stop service immediately
sudo systemctl stop reddit-sentiment-pipeline.service

# 3. Restore from latest backup
python3 scripts/backup_manager.py restore-database latest

# 4. Verify restoration
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "PRAGMA integrity_check;"

# 5. Restart service
sudo systemctl start reddit-sentiment-pipeline.service

# 6. Verify functionality
curl http://localhost:8001/health/database
```

#### Scenario 2: Complete Server Failure

```bash
# 1. Provision new server
# 2. Install base system dependencies
# 3. Restore application from backup

# Create user and directories
sudo useradd -m -s /bin/bash cayir
sudo mkdir -p /home/cayir/cicd_project

# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv sqlite3

# Restore from remote backup (if available)
scp backup-server:/backups/reddit-sentiment/latest.tar.gz /tmp/
tar -xzf /tmp/latest.tar.gz -C /home/cayir/cicd_project

# Set permissions
sudo chown -R cayir:cayir /home/cayir/cicd_project

# Reinstall Python dependencies
cd /home/cayir/cicd_project
python3 -m venv venv
source venv/bin/activate
pip install -r apps/collector/requirements.txt

# Configure systemd
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable reddit-sentiment-pipeline.service reddit-sentiment-pipeline.timer

# Start services
sudo systemctl start reddit-sentiment-pipeline.service
sudo systemctl start reddit-sentiment-pipeline.timer

# Verify functionality
curl http://localhost:8001/health
```

### Remote Backup Configuration

For disaster recovery, consider setting up remote backups:

```bash
# Configure remote backup sync (example)
# Add to backup_manager.py or separate script

# Sync to remote server
rsync -avz --delete \
    /home/cayir/cicd_project/backups/ \
    backup-server:/remote/backups/reddit-sentiment/

# Sync to cloud storage (AWS S3 example)
aws s3 sync /home/cayir/cicd_project/backups/ \
    s3://company-backups/reddit-sentiment/ \
    --delete --storage-class STANDARD_IA
```

## Backup Monitoring

### Backup Health Checks

Monitor backup system health:

```bash
# Check backup service status
systemctl status backup-manager.timer
systemctl status backup-manager.service

# Check recent backup logs
tail -50 /home/cayir/cicd_project/logs/backup.log

# Verify latest backup exists and is recent
find /home/cayir/cicd_project/backups/daily/ -name "*.tar.gz" -mtime -1 -ls
```

### Backup Alerts

Configure alerts for backup failures:

1. **Missing Backup**: No backup created in 25 hours
2. **Backup Failure**: Backup process exits with error
3. **Verification Failure**: Backup fails integrity checks
4. **Storage Full**: Backup directory approaching capacity

### Backup Metrics

Track backup system metrics:

- Backup creation time
- Backup file size
- Verification success rate
- Storage utilization
- Recovery test success rate

## Troubleshooting

### Common Backup Issues

#### Backup Creation Fails

**Symptoms**: Backup script exits with error

**Troubleshooting**:
```bash
# Check disk space
df -h /home/cayir/cicd_project/backups/

# Check permissions
ls -la /home/cayir/cicd_project/backups/

# Run backup manually with verbose output
python3 scripts/backup_manager.py create --verbose

# Check for file locks
lsof +D /home/cayir/cicd_project/data/
```

**Resolution**:
- Free up disk space
- Fix file permissions
- Stop services if database is locked
- Check backup script logs

#### Backup Verification Fails

**Symptoms**: Verification reports corruption or missing files

**Troubleshooting**:
```bash
# Test archive integrity
tar -tzf backup_20240528_020000.tar.gz > /dev/null

# Check database file in backup
tar -xzf backup_20240528_020000.tar.gz data/reddit_sentiment.db -O | \
sqlite3 :memory: ".restore /dev/stdin" ".tables"

# Compare backup with original
tar -tzf backup_20240528_020000.tar.gz | sort > /tmp/backup_files
find /home/cayir/cicd_project -type f | sort > /tmp/original_files
diff /tmp/backup_files /tmp/original_files
```

**Resolution**:
- Recreate backup if corruption detected
- Investigate source of corruption
- Update backup exclusion patterns

#### Recovery Fails

**Symptoms**: Restore process fails or restored system doesn't work

**Troubleshooting**:
```bash
# Check restore logs
python3 scripts/backup_manager.py restore backup.tar.gz --verbose

# Verify extracted files
ls -la /home/cayir/cicd_project/

# Check file permissions
find /home/cayir/cicd_project -type f -not -perm 644 -ls
find /home/cayir/cicd_project -type d -not -perm 755 -ls

# Test database after restore
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "PRAGMA integrity_check;"
```

**Resolution**:
- Fix file permissions after restore
- Manually configure missing components
- Use different backup if current one is corrupted

### Recovery Testing

#### Automated Recovery Test

```bash
# Create test script for regular recovery testing
cat > /home/cayir/cicd_project/scripts/test_recovery.sh << 'EOF'
#!/bin/bash
# Recovery test script

set -e

echo "Starting recovery test..."

# Create test environment
TEST_DIR="/tmp/recovery_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEST_DIR"

# Extract latest backup
LATEST_BACKUP=$(ls -t /home/cayir/cicd_project/backups/daily/*.tar.gz | head -1)
tar -xzf "$LATEST_BACKUP" -C "$TEST_DIR"

# Test database
sqlite3 "$TEST_DIR/data/reddit_sentiment.db" "PRAGMA integrity_check;"

# Test configuration
python3 -c "
import sys, configparser
sys.path.append('$TEST_DIR')
config = configparser.ConfigParser()
config.read('$TEST_DIR/config/production.env')
print('Configuration test passed')
"

# Cleanup
rm -rf "$TEST_DIR"

echo "Recovery test completed successfully"
EOF

chmod +x /home/cayir/cicd_project/scripts/test_recovery.sh
```

#### Schedule Recovery Tests

```bash
# Add to cron for weekly recovery testing
echo "0 4 * * 1 /home/cayir/cicd_project/scripts/test_recovery.sh >> /home/cayir/cicd_project/logs/recovery_test.log 2>&1" | crontab -
```

---

**Document Version**: 1.0  
**Last Updated**: May 28, 2025  
**Maintained By**: DevOps Team  
**Review Schedule**: Quarterly
