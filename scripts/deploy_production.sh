#!/bin/bash

# Reddit Sentiment Pipeline - Production Deployment Script
# This script automates the deployment to /home/cayir/cicd_project

set -euo pipefail

# Configuration
DEPLOY_USER="cayir"
DEPLOY_PATH="/home/${DEPLOY_USER}/cicd_project"
SERVICE_NAME="reddit-sentiment-pipeline"
GITHUB_REPO="https://github.com/your-org/reddit-sentiment-pipeline.git"
DOCKER_IMAGE="reddit-sentiment-pipeline"
DOCKER_TAG="${DOCKER_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as correct user
check_user() {
    if [[ "$(whoami)" != "$DEPLOY_USER" ]]; then
        log_error "This script must be run as user '$DEPLOY_USER'"
        exit 1
    fi
}

# Create deployment directory structure
setup_directories() {
    log_info "Setting up deployment directories..."
    
    mkdir -p "$DEPLOY_PATH"/{data,logs,config,backups}
    
    # Set proper permissions
    chmod 755 "$DEPLOY_PATH"
    chmod 750 "$DEPLOY_PATH"/{data,logs,config,backups}
    
    log_info "Directory structure created successfully"
}

# Clone or update repository
deploy_code() {
    log_info "Deploying application code..."
    
    if [[ -d "$DEPLOY_PATH/.git" ]]; then
        log_info "Updating existing repository..."
        cd "$DEPLOY_PATH"
        git fetch origin
        git reset --hard origin/main
        git clean -fd
    else
        log_info "Cloning repository..."
        git clone "$GITHUB_REPO" "$DEPLOY_PATH"
        cd "$DEPLOY_PATH"
    fi
    
    # Get current commit hash for tracking
    COMMIT_HASH=$(git rev-parse --short HEAD)
    echo "$COMMIT_HASH" > "$DEPLOY_PATH/.deployment_version"
    
    log_info "Code deployment completed (commit: $COMMIT_HASH)"
}

# Setup Python virtual environment
setup_python_env() {
    log_info "Setting up Python environment..."
    
    cd "$DEPLOY_PATH"
    
    # Remove existing venv if it exists
    if [[ -d "venv" ]]; then
        rm -rf venv
    fi
    
    # Create new virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip and install dependencies
    pip install --upgrade pip
    pip install -r apps/collector/requirements.txt
    
    log_info "Python environment setup completed"
}

# Build Docker image
build_docker_image() {
    log_info "Building Docker image..."
    
    cd "$DEPLOY_PATH"
    
    # Build the image
    docker build -t "${DOCKER_IMAGE}:${DOCKER_TAG}" .
    
    # Tag as latest
    docker tag "${DOCKER_IMAGE}:${DOCKER_TAG}" "${DOCKER_IMAGE}:latest"
    
    log_info "Docker image built successfully"
}

# Setup configuration files
setup_configuration() {
    log_info "Setting up configuration files..."
    
    # Copy environment template if .env doesn't exist
    if [[ ! -f "$DEPLOY_PATH/.env" ]]; then
        cp "$DEPLOY_PATH/.env.example" "$DEPLOY_PATH/.env"
        log_warn "Please edit $DEPLOY_PATH/.env with your configuration"
    fi
    
    # Setup logrotate configuration
    cat > "$DEPLOY_PATH/config/logrotate.conf" << 'EOF'
/home/cayir/cicd_project/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 cayir cayir
    postrotate
        # Restart the service if it's running
        systemctl is-active reddit-sentiment-pipeline >/dev/null 2>&1 && systemctl reload reddit-sentiment-pipeline || true
    endscript
}
EOF

    log_info "Configuration setup completed"
}

# Setup systemd service
setup_systemd_service() {
    log_info "Setting up systemd service..."
    
    # Create systemd service file
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Reddit Sentiment Analysis Pipeline
After=network.target
Wants=network.target

[Service]
Type=oneshot
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${DEPLOY_PATH}
Environment=PATH=${DEPLOY_PATH}/venv/bin
EnvironmentFile=${DEPLOY_PATH}/.env
ExecStart=${DEPLOY_PATH}/venv/bin/python -m apps.collector.collector
StandardOutput=append:${DEPLOY_PATH}/logs/pipeline.log
StandardError=append:${DEPLOY_PATH}/logs/pipeline-error.log
TimeoutSec=1800
Restart=no

[Install]
WantedBy=multi-user.target
EOF

    # Create systemd timer for scheduled execution
    sudo tee /etc/systemd/system/${SERVICE_NAME}.timer > /dev/null << EOF
[Unit]
Description=Run Reddit Sentiment Pipeline every 3 hours
Requires=${SERVICE_NAME}.service

[Timer]
OnBootSec=10min
OnUnitActiveSec=3h
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Reload systemd and enable services
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}.timer
    sudo systemctl start ${SERVICE_NAME}.timer
    
    log_info "Systemd service setup completed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Create monitoring script
    cat > "$DEPLOY_PATH/scripts/health_check.sh" << 'EOF'
#!/bin/bash

# Health check script for Reddit Sentiment Pipeline
DEPLOY_PATH="/home/cayir/cicd_project"
LOG_FILE="$DEPLOY_PATH/logs/health_check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Check if service ran recently (within last 4 hours)
if systemctl is-active reddit-sentiment-pipeline.timer >/dev/null 2>&1; then
    echo "[$TIMESTAMP] Timer is active" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] ERROR: Timer is not active" >> "$LOG_FILE"
    exit 1
fi

# Check log file for recent activity
if [[ -f "$DEPLOY_PATH/logs/pipeline.log" ]]; then
    LAST_RUN=$(stat -c %Y "$DEPLOY_PATH/logs/pipeline.log" 2>/dev/null || echo 0)
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_RUN))
    
    # 4 hours = 14400 seconds
    if [[ $TIME_DIFF -lt 14400 ]]; then
        echo "[$TIMESTAMP] Pipeline ran recently (${TIME_DIFF}s ago)" >> "$LOG_FILE"
    else
        echo "[$TIMESTAMP] WARNING: Pipeline hasn't run in ${TIME_DIFF}s" >> "$LOG_FILE"
    fi
else
    echo "[$TIMESTAMP] WARNING: No pipeline log found" >> "$LOG_FILE"
fi
EOF

    chmod +x "$DEPLOY_PATH/scripts/health_check.sh"
    
    # Setup cron job for health checks
    (crontab -l 2>/dev/null; echo "*/30 * * * * $DEPLOY_PATH/scripts/health_check.sh") | crontab -
    
    log_info "Monitoring setup completed"
}

# Create backup script
setup_backup() {
    log_info "Setting up backup system..."
    
    cat > "$DEPLOY_PATH/scripts/backup.sh" << 'EOF'
#!/bin/bash

DEPLOY_PATH="/home/cayir/cicd_project"
BACKUP_PATH="$DEPLOY_PATH/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Create backup
mkdir -p "$BACKUP_PATH"

# Backup data directory
if [[ -d "$DEPLOY_PATH/data" ]]; then
    tar -czf "$BACKUP_PATH/data_backup_$TIMESTAMP.tar.gz" -C "$DEPLOY_PATH" data/
fi

# Backup configuration
tar -czf "$BACKUP_PATH/config_backup_$TIMESTAMP.tar.gz" -C "$DEPLOY_PATH" .env config/

# Keep only last 7 days of backups
find "$BACKUP_PATH" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
EOF

    chmod +x "$DEPLOY_PATH/scripts/backup.sh"
    
    # Setup daily backup cron job
    (crontab -l 2>/dev/null; echo "0 2 * * * $DEPLOY_PATH/scripts/backup.sh") | crontab -
    
    log_info "Backup system setup completed"
}

# Run tests
run_tests() {
    log_info "Running test suite..."
    
    cd "$DEPLOY_PATH"
    source venv/bin/activate
    
    # Install test dependencies
    pip install pytest pytest-cov
    
    # Run tests
    python -m pytest tests/ -v --cov=apps/collector --cov-report=term-missing
    
    log_info "Tests completed successfully"
}

# Main deployment function
main() {
    log_info "Starting Reddit Sentiment Pipeline deployment..."
    
    check_user
    setup_directories
    deploy_code
    setup_python_env
    build_docker_image
    setup_configuration
    setup_systemd_service
    setup_monitoring
    setup_backup
    run_tests
    
    log_info "Deployment completed successfully!"
    log_info "Service status: $(systemctl is-active ${SERVICE_NAME}.timer)"
    log_info "Next run: $(systemctl list-timers ${SERVICE_NAME}.timer --no-pager | tail -n +2)"
    
    echo
    log_info "Important notes:"
    echo "  1. Edit $DEPLOY_PATH/.env with your Reddit API credentials"
    echo "  2. Monitor logs at $DEPLOY_PATH/logs/"
    echo "  3. Check service status with: systemctl status ${SERVICE_NAME}.timer"
    echo "  4. Manual run: systemctl start ${SERVICE_NAME}.service"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "update")
        deploy_code
        setup_python_env
        build_docker_image
        sudo systemctl restart ${SERVICE_NAME}.timer
        log_info "Update completed successfully!"
        ;;
    "status")
        echo "Service Status: $(systemctl is-active ${SERVICE_NAME}.timer)"
        echo "Last Run: $(journalctl -u ${SERVICE_NAME}.service --no-pager -n 1 --output=short-iso)"
        echo "Next Run: $(systemctl list-timers ${SERVICE_NAME}.timer --no-pager | tail -n +2)"
        ;;
    "logs")
        journalctl -u ${SERVICE_NAME}.service -f
        ;;
    *)
        echo "Usage: $0 {deploy|update|status|logs}"
        echo "  deploy  - Full deployment"
        echo "  update  - Update code and restart"
        echo "  status  - Show service status"
        echo "  logs    - Follow service logs"
        exit 1
        ;;
esac
