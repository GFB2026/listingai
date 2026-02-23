#!/bin/sh
# Database backup script — runs daily via the backup container.
# Keeps 7 days of daily backups + 4 weekly backups.

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
DAILY_DIR="$BACKUP_DIR/daily"
WEEKLY_DIR="$BACKUP_DIR/weekly"

mkdir -p "$DAILY_DIR" "$WEEKLY_DIR"

BACKUP_FILE="$DAILY_DIR/listingai_$DATE.sql.gz"

echo "[$(date)] Starting database backup..."

# Create compressed backup
pg_dump --no-owner --no-acl --clean --if-exists | gzip > "$BACKUP_FILE"

FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date)] Backup created: $BACKUP_FILE ($FILESIZE)"

# Weekly backup on Sundays (day 7)
if [ "$DAY_OF_WEEK" = "7" ]; then
    cp "$BACKUP_FILE" "$WEEKLY_DIR/listingai_weekly_$DATE.sql.gz"
    echo "[$(date)] Weekly backup saved"
fi

# Rotate daily backups: keep last 7 days
find "$DAILY_DIR" -name "*.sql.gz" -mtime +7 -delete 2>/dev/null || true

# Rotate weekly backups: keep last 4 weeks
find "$WEEKLY_DIR" -name "*.sql.gz" -mtime +28 -delete 2>/dev/null || true

echo "[$(date)] Backup complete. Remaining backups:"
echo "  Daily: $(ls -1 "$DAILY_DIR"/*.sql.gz 2>/dev/null | wc -l) files"
echo "  Weekly: $(ls -1 "$WEEKLY_DIR"/*.sql.gz 2>/dev/null | wc -l) files"
