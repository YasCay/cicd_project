# Production Deployment Guide

## Reddit Sentiment Analysis Pipeline - Production Deployment

This document provides comprehensive instructions for deploying the Reddit Sentiment Analysis Pipeline to a production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Production Environment Setup](#production-environment-setup)
3. [Deployment Process](#deployment-process)
4. [Configuration Management](#configuration-management)
5. [Service Management](#service-management)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Backup and Recovery](#backup-and-recovery)
8. [Security Considerations](#security-considerations)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or newer / CentOS 8+ / RHEL 8+
- **CPU**: Minimum 2 cores, Recommended 4+ cores
- **Memory**: Minimum 4GB RAM, Recommended 8GB+ RAM
- **Storage**: Minimum 50GB available disk space
- **Network**: Stable internet connection for Reddit API access

### Required Software

- Python 3.8 or newer
- Git
- systemd (for service management)
- nginx (for reverse proxy)
- Prometheus (for monitoring)
- Grafana (for dashboards)

### External Dependencies

- Reddit API credentials (client ID and secret)
- SMTP server for email alerts (optional)
- Slack webhook URL for notifications (optional)

## Production Environment Setup

### Automated Setup

The production environment can be set up automatically using the provided script:

```bash
# Navigate to project directory
cd /home/yasar/cicd_project

# Make setup script executable
chmod +x scripts/setup_production_env.sh

# Run the automated setup
sudo ./scripts/setup_production_env.sh
```

### Manual Setup Steps

If you prefer manual setup or need to troubleshoot the automated process:

#### 1. Create Production User

```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash cayir
sudo usermod -aG systemd-journal cayir

# Set up user environment
sudo -u cayir mkdir -p /home/cayir/cicd_project
sudo chown -R cayir:cayir /home/cayir/cicd_project
```

#### 2. Install System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git nginx prometheus grafana
sudo systemctl enable nginx prometheus grafana-server
sudo systemctl start nginx prometheus grafana-server
```

#### 3. Set up Python Environment

```bash
# Switch to application user
sudo -u cayir -i

# Create Python virtual environment
cd /home/cayir/cicd_project
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r apps/collector/requirements.txt
```

#### 4. Configure Environment Variables

```bash
# Copy production environment template
cp config/production.env.template config/production.env

# Edit configuration file
nano config/production.env

# Set Reddit API credentials
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

## Deployment Process

### 1. Clone and Setup Repository

```bash
# Clone the repository
git clone https://github.com/your-org/reddit-sentiment-pipeline.git /home/cayir/cicd_project
cd /home/cayir/cicd_project

# Checkout production branch
git checkout production

# Set up directory structure
mkdir -p logs data backups config
```

### 2. Install and Configure Services

```bash
# Copy systemd service files
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable reddit-sentiment-pipeline.service
sudo systemctl enable reddit-sentiment-pipeline.timer
sudo systemctl enable reddit-sentiment-monitor.service
```

### 3. Configure Monitoring

```bash
# Copy Prometheus configuration
sudo cp monitoring/prometheus_config.yml /etc/prometheus/prometheus.yml
sudo cp monitoring/alerting_rules.yml /etc/prometheus/

# Restart Prometheus
sudo systemctl restart prometheus

# Import Grafana dashboard
# Access Grafana at http://localhost:3000 (admin/admin)
# Import monitoring/health_dashboard.json
```

### 4. Set up nginx Reverse Proxy

```bash
# Create nginx configuration
sudo tee /etc/nginx/sites-available/reddit-sentiment-pipeline << EOF
server {
    listen 80;
    server_name production-server.local;

    location /metrics {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /health {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location / {
        return 404;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/reddit-sentiment-pipeline /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Configuration Management

### Environment Configuration

The application uses environment-specific configuration files:

- `config/production.env` - Production environment variables
- `config/logging.conf` - Logging configuration
- `config/monitoring.yml` - Monitoring and alerting setup

### Security Configuration

```bash
# Set appropriate file permissions
chmod 600 config/production.env
chmod 644 config/logging.conf config/monitoring.yml

# Create SSL certificates (if needed)
sudo mkdir -p /home/cayir/cicd_project/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /home/cayir/cicd_project/ssl/key.pem \
    -out /home/cayir/cicd_project/ssl/cert.pem
```

### Database Configuration

```bash
# Initialize database directory
mkdir -p /home/cayir/cicd_project/data
touch /home/cayir/cicd_project/data/reddit_sentiment.db

# Set permissions
chmod 644 /home/cayir/cicd_project/data/reddit_sentiment.db
```

## Service Management

### Starting Services

```bash
# Start the main pipeline service
sudo systemctl start reddit-sentiment-pipeline.service

# Start the timer for scheduled execution
sudo systemctl start reddit-sentiment-pipeline.timer

# Start the monitoring service
sudo systemctl start reddit-sentiment-monitor.service
```

### Checking Service Status

```bash
# Check service status
sudo systemctl status reddit-sentiment-pipeline.service
sudo systemctl status reddit-sentiment-pipeline.timer
sudo systemctl status reddit-sentiment-monitor.service

# View service logs
sudo journalctl -u reddit-sentiment-pipeline.service -f
sudo journalctl -u reddit-sentiment-monitor.service -f
```

### Service Management Commands

```bash
# Stop services
sudo systemctl stop reddit-sentiment-pipeline.service
sudo systemctl stop reddit-sentiment-pipeline.timer
sudo systemctl stop reddit-sentiment-monitor.service

# Restart services
sudo systemctl restart reddit-sentiment-pipeline.service
sudo systemctl restart reddit-sentiment-monitor.service

# Disable services
sudo systemctl disable reddit-sentiment-pipeline.service
sudo systemctl disable reddit-sentiment-pipeline.timer
sudo systemctl disable reddit-sentiment-monitor.service
```

## Monitoring and Alerting

### Accessing Monitoring Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Application Metrics**: http://localhost:8000/metrics
- **Health Checks**: http://localhost:8001/health

### Alert Configuration

Alerts are configured in `monitoring/alerting_rules.yml` and include:

- Service availability
- Resource usage (CPU, memory, disk)
- Application-specific metrics
- Error rates and failures

### Custom Metrics

The application exposes custom metrics:

- `posts_processed_total` - Total Reddit posts processed
- `sentiment_analysis_duration_seconds` - Sentiment analysis performance
- `reddit_api_requests_total` - Reddit API usage
- `duplicates_found_total` - Deduplication effectiveness

## Backup and Recovery

### Automated Backups

Backups are automatically created using the backup manager:

```bash
# Manual backup creation
python3 scripts/backup_manager.py create

# Restore from backup
python3 scripts/backup_manager.py restore backup_20240528_120000.tar.gz

# Verify backup integrity
python3 scripts/backup_manager.py verify backup_20240528_120000.tar.gz
```

### Backup Schedule

- **Daily backups**: Created at 2:00 AM
- **Retention**: 30 days
- **Location**: `/home/cayir/cicd_project/backups/`
- **Compression**: gzip enabled

### Recovery Procedures

In case of system failure:

1. Stop all services
2. Restore from latest backup
3. Verify configuration files
4. Restart services
5. Validate functionality

## Security Considerations

### File Permissions

```bash
# Set secure permissions
chmod 750 /home/cayir/cicd_project
chmod 600 config/production.env
chmod 644 config/*.conf config/*.yml
chmod 755 scripts/*.sh
chmod 644 scripts/*.py
```

### Network Security

```bash
# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 3000/tcp  # Grafana
sudo ufw allow 9090/tcp  # Prometheus
```

### Service Security

Services run with minimal privileges:

- Non-root user execution
- Resource limits configured
- Network access restricted
- File system access limited

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service logs
sudo journalctl -u reddit-sentiment-pipeline.service -n 50

# Verify configuration
python3 -m apps.collector.collector --validate-config

# Check permissions
ls -la /home/cayir/cicd_project/
```

#### High Resource Usage

```bash
# Monitor resource usage
htop
iostat -x 1
free -h

# Check application metrics
curl http://localhost:8000/metrics | grep -E "(cpu|memory|disk)"
```

#### Reddit API Issues

```bash
# Test API connectivity
python3 -c "
import os
os.chdir('/home/cayir/cicd_project')
from apps.collector.collector import test_reddit_connection
test_reddit_connection()
"
```

### Log Analysis

```bash
# Application logs
tail -f /home/cayir/cicd_project/logs/reddit_sentiment_pipeline.log

# System logs
sudo journalctl -f | grep reddit-sentiment

# Error logs
tail -f /home/cayir/cicd_project/logs/reddit_sentiment_errors.log
```

## Maintenance

### Regular Maintenance Tasks

#### Daily

- Check service status
- Monitor resource usage
- Review error logs
- Verify backup completion

#### Weekly

- Review performance metrics
- Clean up old log files
- Update system packages
- Test backup restoration

#### Monthly

- Security updates
- Configuration review
- Performance optimization
- Disaster recovery testing

### Update Procedures

```bash
# Stop services
sudo systemctl stop reddit-sentiment-pipeline.timer
sudo systemctl stop reddit-sentiment-pipeline.service

# Backup current deployment
python3 scripts/backup_manager.py create pre-update-backup

# Update code
git pull origin production

# Update dependencies
source venv/bin/activate
pip install --upgrade -r apps/collector/requirements.txt

# Restart services
sudo systemctl start reddit-sentiment-pipeline.service
sudo systemctl start reddit-sentiment-pipeline.timer

# Verify functionality
curl http://localhost:8001/health
```

### Performance Optimization

#### Database Optimization

```bash
# Vacuum SQLite database
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "VACUUM;"

# Analyze database
sqlite3 /home/cayir/cicd_project/data/reddit_sentiment.db "ANALYZE;"
```

#### Log Rotation

```bash
# Configure logrotate
sudo tee /etc/logrotate.d/reddit-sentiment-pipeline << EOF
/home/cayir/cicd_project/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

## Support and Documentation

For additional support:

- **Project Repository**: https://github.com/your-org/reddit-sentiment-pipeline
- **Issue Tracker**: https://github.com/your-org/reddit-sentiment-pipeline/issues
- **Documentation**: `/home/yasar/cicd_project/docs/`
- **Monitoring Runbook**: [monitoring-runbook.md](monitoring-runbook.md)
- **Backup Guide**: [backup-recovery.md](backup-recovery.md)

---

**Last Updated**: May 28, 2025  
**Version**: 1.0.0  
**Maintainer**: Production DevOps Team
