#!/bin/bash
# Manual cleanup script for old log files
# This script removes log files older than specified days

set -e

# Configuration
LOG_DIR="${LOG_DIR:-/app/logs}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DRY_RUN="${DRY_RUN:-false}"

echo "============================================"
echo "Log Cleanup Script"
echo "============================================"
echo "Log directory: $LOG_DIR"
echo "Retention: $RETENTION_DAYS days"
echo "Dry run: $DRY_RUN"
echo "============================================"

# Find and delete old log files
if [ "$DRY_RUN" = "true" ]; then
    echo "DRY RUN - Files that would be deleted:"
    find "$LOG_DIR" -type f -name "*.log.*" -mtime +$RETENTION_DAYS -ls
    
    # Calculate space that would be freed
    TOTAL_SIZE=$(find "$LOG_DIR" -type f -name "*.log.*" -mtime +$RETENTION_DAYS -exec du -cb {} + | tail -1 | cut -f1)
    TOTAL_MB=$((TOTAL_SIZE / 1024 / 1024))
    echo "============================================"
    echo "Total space that would be freed: ${TOTAL_MB} MB"
else
    echo "Deleting files older than $RETENTION_DAYS days..."
    find "$LOG_DIR" -type f -name "*.log.*" -mtime +$RETENTION_DAYS -delete
    echo "Cleanup completed!"
fi

echo "============================================"

# Show current log directory size
echo "Current log directory size:"
du -sh "$LOG_DIR"
echo "============================================"
