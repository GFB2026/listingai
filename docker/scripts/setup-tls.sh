#!/usr/bin/env bash
# setup-tls.sh — Provision and configure TLS certificates for ListingAI.
#
# This script handles the full lifecycle:
#   1. Bootstrap: creates a temporary self-signed cert so nginx can start
#   2. Certbot: obtains a real Let's Encrypt certificate
#   3. Symlinks: wires the cert into the path nginx expects
#   4. Reload: tells nginx to pick up the real cert
#   5. Auto-renewal: installs a cron job for ongoing renewal
#
# Usage:
#   ./setup-tls.sh <domain> [email]
#
# Examples:
#   ./setup-tls.sh app.listingai.com
#   ./setup-tls.sh app.listingai.com admin@listingai.com
#
# Requirements:
#   - Docker and Docker Compose v2 installed
#   - DNS A record for <domain> pointing to this server
#   - Ports 80 and 443 open in the firewall
#   - Run from the repository root (/opt/listingai)
#
# Idempotent: safe to run multiple times. Skips steps that are already done.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILES="-f $PROJECT_ROOT/docker/docker-compose.yml -f $PROJECT_ROOT/docker/docker-compose.prod.yml"
COMPOSE_CMD="docker compose $COMPOSE_FILES"

# Where certbot stores certs inside the nginx-ssl volume.
# nginx container mounts nginx-ssl at /etc/nginx/ssl, so:
#   /etc/letsencrypt/live/<domain>/fullchain.pem  (certbot container)
#   =  /etc/nginx/ssl/live/<domain>/fullchain.pem  (nginx container)
#
# nginx.conf expects:
#   /etc/nginx/ssl/fullchain.pem
#   /etc/nginx/ssl/privkey.pem
#
# We bridge the gap with symlinks inside the volume.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log()   { echo -e "${GREEN}[setup-tls]${NC} $*"; }
warn()  { echo -e "${YELLOW}[setup-tls]${NC} $*"; }
error() { echo -e "${RED}[setup-tls]${NC} $*" >&2; }
die()   { error "$@"; exit 1; }

usage() {
    echo "Usage: $0 <domain> [email]"
    echo ""
    echo "Arguments:"
    echo "  domain   The fully qualified domain name (e.g., app.listingai.com)"
    echo "  email    Contact email for Let's Encrypt (default: admin@<domain>)"
    echo ""
    echo "Examples:"
    echo "  $0 app.listingai.com"
    echo "  $0 app.listingai.com admin@listingai.com"
    exit 1
}

# Run a command inside a running container via docker compose exec.
# Falls back to docker compose run if the container is not running.
compose_exec() {
    local service="$1"
    shift
    if $COMPOSE_CMD ps --status running "$service" 2>/dev/null | grep -q "$service"; then
        $COMPOSE_CMD exec "$service" "$@"
    else
        $COMPOSE_CMD run --rm "$service" "$@"
    fi
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

if [ $# -lt 1 ]; then
    usage
fi

DOMAIN="$1"
EMAIL="${2:-admin@$DOMAIN}"

# Basic domain validation
if ! echo "$DOMAIN" | grep -qP '^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'; then
    die "Invalid domain name: $DOMAIN"
fi

log "Domain:  $DOMAIN"
log "Email:   $EMAIL"
log "Project: $PROJECT_ROOT"
echo ""

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

log "Running pre-flight checks..."

# Docker
command -v docker >/dev/null 2>&1 || die "Docker is not installed. Install it first: https://docs.docker.com/engine/install/"

# Docker Compose v2
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is not available. Install it first."

# Compose files exist
[ -f "$PROJECT_ROOT/docker/docker-compose.yml" ] || die "Missing docker/docker-compose.yml — run this from the repo root."
[ -f "$PROJECT_ROOT/docker/docker-compose.prod.yml" ] || die "Missing docker/docker-compose.prod.yml — run this from the repo root."

log "Pre-flight checks passed."
echo ""

# ---------------------------------------------------------------------------
# Step 1: Create docker volumes if they don't exist
# ---------------------------------------------------------------------------

log "Ensuring Docker volumes exist..."

# The volumes are defined in docker-compose.prod.yml and will be created
# automatically, but we ensure the compose project is initialized.
$COMPOSE_CMD create --no-start certbot 2>/dev/null || true

log "Docker volumes ready."
echo ""

# ---------------------------------------------------------------------------
# Step 2: Bootstrap — self-signed certificate for nginx startup
# ---------------------------------------------------------------------------
# nginx refuses to start if its ssl_certificate files don't exist.
# We generate a throwaway self-signed cert so the stack can boot.
# It gets replaced by the real cert in Step 3.

log "Checking for existing certificates..."

# Check if a real Let's Encrypt cert already exists for this domain
CERT_EXISTS=false
if $COMPOSE_CMD run --rm --entrypoint "" certbot \
    test -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" 2>/dev/null; then
    CERT_EXISTS=true
    log "Let's Encrypt certificate already exists for $DOMAIN."
fi

if [ "$CERT_EXISTS" = false ]; then
    log "No certificate found. Creating temporary self-signed certificate..."

    $COMPOSE_CMD run --rm --entrypoint "" certbot sh -c "
        mkdir -p /etc/letsencrypt/live/$DOMAIN
        # Generate self-signed cert (valid 1 day — just for bootstrapping)
        openssl req -x509 -nodes -newkey rsa:2048 \
            -days 1 \
            -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
            -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
            -subj '/CN=$DOMAIN' \
            2>/dev/null
        echo 'Self-signed bootstrap certificate created.'
    "
fi

# ---------------------------------------------------------------------------
# Step 3: Create symlinks so nginx can find the certs
# ---------------------------------------------------------------------------
# nginx.conf expects:   /etc/nginx/ssl/fullchain.pem
# Volume maps:          nginx-ssl  ->  /etc/nginx/ssl  (nginx)
#                       nginx-ssl  ->  /etc/letsencrypt (certbot)
# So we symlink:        /etc/letsencrypt/fullchain.pem -> live/<domain>/fullchain.pem
# Which nginx sees as:  /etc/nginx/ssl/fullchain.pem   -> (same file)

log "Creating symlinks for nginx..."

$COMPOSE_CMD run --rm --entrypoint "" certbot sh -c "
    ln -sf /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/letsencrypt/fullchain.pem
    ln -sf /etc/letsencrypt/live/$DOMAIN/privkey.pem   /etc/letsencrypt/privkey.pem
    echo 'Symlinks created.'
"

log "Symlinks ready."
echo ""

# ---------------------------------------------------------------------------
# Step 4: Start nginx (with bootstrap or real cert)
# ---------------------------------------------------------------------------

log "Starting nginx..."

$COMPOSE_CMD up -d nginx

# Wait for nginx to be healthy
log "Waiting for nginx to become healthy..."
RETRIES=0
MAX_RETRIES=30
while [ $RETRIES -lt $MAX_RETRIES ]; do
    if $COMPOSE_CMD ps --status running nginx 2>/dev/null | grep -q nginx; then
        # Check if the container's health check passes
        HEALTH=$($COMPOSE_CMD ps --format json nginx 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1 || echo "")
        if echo "$HEALTH" | grep -qi "healthy"; then
            break
        fi
    fi
    RETRIES=$((RETRIES + 1))
    sleep 2
done

if [ $RETRIES -ge $MAX_RETRIES ]; then
    warn "Nginx health check did not pass within 60 seconds."
    warn "This may be OK if the backend/frontend are not yet running."
    warn "Continuing with certificate provisioning..."
fi

echo ""

# ---------------------------------------------------------------------------
# Step 5: Obtain the real Let's Encrypt certificate
# ---------------------------------------------------------------------------

if [ "$CERT_EXISTS" = true ]; then
    log "Certificate already exists — skipping certbot. Use 'certbot renew' to renew."
else
    log "Requesting Let's Encrypt certificate for $DOMAIN..."
    log "(This requires DNS to be pointing to this server and port 80 to be open.)"
    echo ""

    # Use webroot mode — nginx is running and serving /.well-known/acme-challenge/
    # from the certbot-webroot volume.
    $COMPOSE_CMD run --rm certbot certbot certonly \
        --webroot \
        -w /var/www/certbot \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        --force-renewal \
        || die "Certbot failed. Check that DNS is configured and port 80 is open."

    log "Certificate obtained successfully."
    echo ""

    # Update symlinks to point to the real cert
    log "Updating symlinks to real certificate..."
    $COMPOSE_CMD run --rm --entrypoint "" certbot sh -c "
        ln -sf /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/letsencrypt/fullchain.pem
        ln -sf /etc/letsencrypt/live/$DOMAIN/privkey.pem   /etc/letsencrypt/privkey.pem
    "
fi

# ---------------------------------------------------------------------------
# Step 6: Reload nginx with the real certificate
# ---------------------------------------------------------------------------

log "Reloading nginx to pick up the certificate..."

$COMPOSE_CMD exec nginx nginx -s reload 2>/dev/null \
    || warn "Could not reload nginx — you may need to restart it manually."

echo ""

# ---------------------------------------------------------------------------
# Step 7: Start the certbot renewal sidecar
# ---------------------------------------------------------------------------

log "Starting certbot renewal sidecar container..."

$COMPOSE_CMD up -d certbot

echo ""

# ---------------------------------------------------------------------------
# Step 8: Install host-level cron job for renewal + nginx reload
# ---------------------------------------------------------------------------
# The certbot container handles renewal internally (every 12h), but
# nginx needs a reload after renewal to pick up the new cert.
# We add a cron job on the host that triggers the reload.

CRON_MARKER="# listingai-tls-renewal"
CRON_CMD="0 0 */60 * * cd $PROJECT_ROOT && $COMPOSE_CMD exec -T certbot certbot renew --webroot -w /var/www/certbot --quiet && $COMPOSE_CMD exec -T nginx nginx -s reload $CRON_MARKER"

log "Configuring auto-renewal cron job..."

if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
    log "Cron job already installed — skipping."
else
    # Append to existing crontab (or create new one)
    (crontab -l 2>/dev/null || true; echo "$CRON_CMD") | crontab -
    log "Cron job installed: renew every 60 days + reload nginx."
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo "============================================================"
echo ""
log "TLS setup complete for $DOMAIN"
echo ""
echo "  Certificate:  /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
echo "  Private key:  /etc/letsencrypt/live/$DOMAIN/privkey.pem"
echo ""
echo "  Nginx sees:   /etc/nginx/ssl/fullchain.pem (symlink)"
echo "                /etc/nginx/ssl/privkey.pem   (symlink)"
echo ""
echo "  Auto-renewal: certbot sidecar (every 12h) + cron (every 60d)"
echo ""
echo "  Verify:       curl -vI https://$DOMAIN/health/live"
echo "  Renew now:    $COMPOSE_CMD exec certbot certbot renew"
echo "  View cert:    $COMPOSE_CMD run --rm --entrypoint '' certbot \\"
echo "                  openssl x509 -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem -noout -dates"
echo ""
echo "============================================================"
