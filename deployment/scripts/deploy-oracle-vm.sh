#!/bin/bash

# ScrapeSavee Oracle VM Deployment Script
# Run this script on your Oracle Cloud Always Free VM

set -e

echo "🚀 Starting ScrapeSavee Oracle VM Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "This script should not be run as root"
   exit 1
fi

# Update system
log_info "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
log_info "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    log_success "Docker installed successfully"
else
    log_info "Docker already installed"
fi

# Install Docker Compose
log_info "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_success "Docker Compose installed successfully"
else
    log_info "Docker Compose already installed"
fi

# Install Nginx and Certbot
log_info "Installing Nginx and Certbot..."
sudo apt install -y nginx certbot python3-certbot-nginx

# Create application directory
APP_DIR="/opt/scrapesavee"
log_info "Creating application directory: $APP_DIR"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone repository (if not already present)
if [ ! -d "$APP_DIR/.git" ]; then
    log_info "Cloning repository..."
    cd $APP_DIR
    git clone https://github.com/yourusername/scrapesavee.git .
else
    log_info "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull
fi

# Check if .env file exists
if [ ! -f "$APP_DIR/.env" ]; then
    log_warning "Environment file not found!"
    log_info "Please create .env file with your configuration:"
    echo ""
    echo "Required variables:"
    echo "  - DATABASE_URL (Neon PostgreSQL)"
    echo "  - AMQP_URL (CloudAMQP RabbitMQ)"  
    echo "  - R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME"
    echo "  - SECRET_KEY (32+ character random string)"
    echo "  - DOMAIN (your domain name)"
    echo ""
    log_info "Copy from .env.example and edit:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
required_vars=("DATABASE_URL" "AMQP_URL" "R2_ENDPOINT_URL" "R2_ACCESS_KEY_ID" "R2_SECRET_ACCESS_KEY" "R2_BUCKET_NAME" "SECRET_KEY" "DOMAIN")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        log_error "Required environment variable $var is not set"
        exit 1
    fi
done

# Update Nginx configuration with actual domain
log_info "Configuring Nginx..."
sudo sed -i "s/your-domain.com/$DOMAIN/g" deployment/nginx/sites/scrapesavee.conf

# Build and start services
log_info "Building Docker images..."
docker-compose -f docker-compose.prod.yml build

log_info "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
log_info "Waiting for services to start..."
sleep 30

# Check service health
log_info "Checking service health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_success "Worker API is healthy"
else
    log_error "Worker API health check failed"
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    log_success "Admin UI is healthy"
else
    log_error "Admin UI health check failed"
fi

# Setup SSL certificate
log_info "Setting up SSL certificate..."
if [ "$DOMAIN" != "your-domain.com" ]; then
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    log_success "SSL certificate configured"
else
    log_warning "Domain not configured, skipping SSL setup"
fi

# Setup firewall
log_info "Configuring firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# Setup log rotation
log_info "Setting up log rotation..."
sudo tee /etc/logrotate.d/scrapesavee > /dev/null <<EOF
/opt/scrapesavee/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/scrapesavee/docker-compose.prod.yml restart worker-api
    endscript
}
EOF

# Setup automatic updates
log_info "Setting up automatic updates..."
sudo tee /etc/cron.d/scrapesavee-update > /dev/null <<EOF
# Update ScrapeSavee daily at 2 AM
0 2 * * * $USER cd $APP_DIR && git pull && docker-compose -f docker-compose.prod.yml up -d --build
EOF

# Final status
echo ""
log_success "🎉 ScrapeSavee deployment completed!"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "🔗 Access Points:"
if [ "$DOMAIN" != "your-domain.com" ]; then
    echo "  🎨 Admin Dashboard: https://$DOMAIN"
    echo "  🔧 API Documentation: https://$DOMAIN/api/docs"
    echo "  ❤️  Health Check: https://$DOMAIN/api/health"
else
    echo "  🎨 Admin Dashboard: http://$(curl -s ifconfig.me)"
    echo "  🔧 API Documentation: http://$(curl -s ifconfig.me)/api/docs"
    echo "  ❤️  Health Check: http://$(curl -s ifconfig.me)/api/health"
fi
echo ""
echo "📋 Management Commands:"
echo "  View logs: docker-compose -f $APP_DIR/docker-compose.prod.yml logs -f"
echo "  Restart: docker-compose -f $APP_DIR/docker-compose.prod.yml restart"
echo "  Update: cd $APP_DIR && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "🔐 Default Login:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  ⚠️  Change this immediately in production!"
echo ""

log_success "Deployment completed successfully! 🚀"

