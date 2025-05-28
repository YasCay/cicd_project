#!/bin/bash

# Reddit Sentiment Pipeline - Production Environment Setup Script
# This script sets up the complete production environment for the sentiment analysis pipeline

set -euo pipefail

# Configuration
DEPLOY_USER="cayir"
DEPLOY_PATH="/home/${DEPLOY_USER}/cicd_project"
SERVICE_NAME="reddit-sentiment-pipeline"
PYTHON_VERSION="3.9"
VENV_PATH="${DEPLOY_PATH}/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Error handling
trap 'log_error "Script failed at line $LINENO"' ERR

# Check if running as root for initial setup
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root for initial system setup"
        log_info "Usage: sudo $0"
        exit 1
    fi
}

# Setup user environment
setup_user_environment() {
    log_info "Setting up user environment for $DEPLOY_USER..."
    
    # Create user if doesn't exist
    if ! id "$DEPLOY_USER" &>/dev/null; then
        log_info "Creating user $DEPLOY_USER..."
        useradd -m -s /bin/bash "$DEPLOY_USER"
        usermod -aG docker "$DEPLOY_USER" 2>/dev/null || true
    fi
    
    # Create deployment directory structure
    log_info "Creating deployment directory structure..."
    sudo -u "$DEPLOY_USER" mkdir -p "$DEPLOY_PATH"/{data,logs,config,backups,scripts,systemd,monitoring}
    
    # Set proper permissions
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_PATH"
    chmod 755 "$DEPLOY_PATH"
    chmod 750 "$DEPLOY_PATH"/{data,logs,config,backups}
    chmod 755 "$DEPLOY_PATH"/{scripts,systemd,monitoring}
    
    log_info "User environment setup completed"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update package lists
    apt-get update
    
    # Install essential packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        unzip \
        cron \
        logrotate \
        htop \
        jq \
        sqlite3 \
        supervisor \
        nginx \
        certbot \
        python3-certbot-nginx
    
    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        log_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        systemctl enable docker
        systemctl start docker
    fi
    
    # Install Docker Compose if not present
    if ! command -v docker-compose &> /dev/null; then
        log_info "Installing Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    log_info "System dependencies installed"
}

# Setup Python environment
setup_python_environment() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment as deploy user
    sudo -u "$DEPLOY_USER" python3 -m venv "$VENV_PATH"
    
    # Upgrade pip and install basic packages
    sudo -u "$DEPLOY_USER" "$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel
    
    # Install application dependencies
    if [[ -f "$DEPLOY_PATH/apps/collector/requirements.txt" ]]; then
        sudo -u "$DEPLOY_USER" "$VENV_PATH/bin/pip" install -r "$DEPLOY_PATH/apps/collector/requirements.txt"
    fi
    
    log_info "Python environment setup completed"
}

# Configure systemd services
configure_systemd() {
    log_info "Configuring systemd services..."
    
    # Copy systemd service files
    if [[ -d "$DEPLOY_PATH/systemd" ]]; then
        cp "$DEPLOY_PATH/systemd"/*.service /etc/systemd/system/
        cp "$DEPLOY_PATH/systemd"/*.timer /etc/systemd/system/ 2>/dev/null || true
        
        # Reload systemd daemon
        systemctl daemon-reload
        
        # Enable services (but don't start yet)
        systemctl enable "${SERVICE_NAME}.service" 2>/dev/null || true
        systemctl enable "${SERVICE_NAME}.timer" 2>/dev/null || true
        systemctl enable "${SERVICE_NAME}-monitor.service" 2>/dev/null || true
        
        log_info "Systemd services configured"
    else
        log_warn "Systemd directory not found, skipping service configuration"
    fi
}

# Setup monitoring infrastructure
setup_monitoring() {
    log_info "Setting up monitoring infrastructure..."
    
    # Create monitoring directories
    mkdir -p /var/log/reddit-sentiment-pipeline
    mkdir -p /opt/monitoring/{prometheus,grafana,alertmanager}
    
    # Set permissions for monitoring
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /var/log/reddit-sentiment-pipeline
    chown -R "$DEPLOY_USER:$DEPLOY_USER" /opt/monitoring
    
    # Setup log rotation
    cat > /etc/logrotate.d/reddit-sentiment-pipeline << EOF
/var/log/reddit-sentiment-pipeline/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $DEPLOY_USER $DEPLOY_USER
    postrotate
        /bin/systemctl reload ${SERVICE_NAME}.service >/dev/null 2>&1 || true
    endscript
}
EOF
    
    log_info "Monitoring infrastructure setup completed"
}

# Setup backup cron jobs
setup_backup_cron() {
    log_info "Setting up backup cron jobs..."
    
    # Create backup cron job for deploy user
    sudo -u "$DEPLOY_USER" crontab -l > /tmp/crontab.tmp 2>/dev/null || echo "" > /tmp/crontab.tmp
    
    # Add backup job if not already present
    if ! grep -q "backup_manager.py" /tmp/crontab.tmp; then
        echo "0 2 * * * cd $DEPLOY_PATH && python3 scripts/backup_manager.py --daily" >> /tmp/crontab.tmp
        echo "0 3 * * 0 cd $DEPLOY_PATH && python3 scripts/backup_manager.py --weekly" >> /tmp/crontab.tmp
        echo "*/10 * * * * cd $DEPLOY_PATH && python3 scripts/health_check.py" >> /tmp/crontab.tmp
        
        sudo -u "$DEPLOY_USER" crontab /tmp/crontab.tmp
    fi
    
    rm -f /tmp/crontab.tmp
    
    log_info "Backup cron jobs configured"
}

# Setup nginx reverse proxy (optional)
setup_nginx() {
    log_info "Setting up nginx reverse proxy..."
    
    # Create nginx configuration for metrics endpoint
    cat > /etc/nginx/sites-available/reddit-sentiment-pipeline << EOF
server {
    listen 80;
    server_name localhost;
    
    location /metrics {
        proxy_pass http://localhost:8000/metrics;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location / {
        return 404;
    }
}
EOF
    
    # Enable the site
    ln -sf /etc/nginx/sites-available/reddit-sentiment-pipeline /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    nginx -t && systemctl reload nginx
    
    log_info "Nginx reverse proxy configured"
}

# Setup firewall rules
setup_firewall() {
    log_info "Setting up firewall rules..."
    
    # Install ufw if not present
    apt-get install -y ufw
    
    # Configure basic firewall rules
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS for monitoring endpoints
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow metrics port (restrict to specific IPs in production)
    ufw allow 8000/tcp
    
    # Enable firewall
    ufw --force enable
    
    log_info "Firewall configured"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."
    
    local validation_errors=0
    
    # Check user exists
    if ! id "$DEPLOY_USER" &>/dev/null; then
        log_error "User $DEPLOY_USER not found"
        ((validation_errors++))
    fi
    
    # Check directory structure
    for dir in data logs config backups scripts; do
        if [[ ! -d "$DEPLOY_PATH/$dir" ]]; then
            log_error "Directory $DEPLOY_PATH/$dir not found"
            ((validation_errors++))
        fi
    done
    
    # Check Python environment
    if [[ ! -f "$VENV_PATH/bin/python" ]]; then
        log_error "Python virtual environment not found"
        ((validation_errors++))
    fi
    
    # Check systemd services
    if ! systemctl list-unit-files | grep -q "${SERVICE_NAME}.service"; then
        log_warn "Systemd service not found (may be normal if systemd files not copied yet)"
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed"
        ((validation_errors++))
    fi
    
    if [[ $validation_errors -eq 0 ]]; then
        log_info "Installation validation passed"
        return 0
    else
        log_error "Installation validation failed with $validation_errors errors"
        return 1
    fi
}

# Print post-installation instructions
print_post_install_instructions() {
    log_info "Production environment setup completed!"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 POST-INSTALLATION STEPS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "1. Deploy application code:"
    echo "   sudo -u $DEPLOY_USER /home/yasar/cicd_project/scripts/deploy_production.sh"
    echo
    echo "2. Configure Reddit API credentials:"
    echo "   sudo -u $DEPLOY_USER nano $DEPLOY_PATH/config/production.env"
    echo
    echo "3. Start systemd services:"
    echo "   systemctl start ${SERVICE_NAME}.service"
    echo "   systemctl start ${SERVICE_NAME}.timer"
    echo
    echo "4. Check service status:"
    echo "   systemctl status ${SERVICE_NAME}.service"
    echo "   journalctl -u ${SERVICE_NAME}.service -f"
    echo
    echo "5. View monitoring endpoints:"
    echo "   curl http://localhost:8000/metrics"
    echo "   curl http://localhost:8000/health"
    echo
    echo "6. Monitor logs:"
    echo "   tail -f /var/log/reddit-sentiment-pipeline/application.log"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    log_info "Starting production environment setup..."
    
    check_root
    setup_user_environment
    install_dependencies
    setup_python_environment
    configure_systemd
    setup_monitoring
    setup_backup_cron
    setup_nginx
    setup_firewall
    
    if validate_installation; then
        print_post_install_instructions
        log_info "Production environment setup completed successfully!"
        exit 0
    else
        log_error "Production environment setup failed validation"
        exit 1
    fi
}

# Run main function
main "$@"
