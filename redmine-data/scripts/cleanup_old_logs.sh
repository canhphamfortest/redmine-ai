#!/bin/bash
# Script để dọn dẹp log files cũ hơn 90 ngày
# Có thể chạy thủ công hoặc setup trong cron

# Cấu hình
LOG_DIR="${LOG_DIR:-./logs}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"
DRY_RUN="${DRY_RUN:-false}"

echo "=========================================="
echo "Cleanup Old Log Files"
echo "=========================================="
echo "Log directory: $LOG_DIR"
echo "Retention: $RETENTION_DAYS days"
echo "Dry run: $DRY_RUN"
echo "=========================================="

# Tìm và xóa log files cũ hơn RETENTION_DAYS
if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY RUN] Files sẽ bị xóa:"
    find "$LOG_DIR" -type f -name "*.log*" -mtime +$RETENTION_DAYS -ls
else
    echo "Đang xóa log files cũ hơn $RETENTION_DAYS ngày..."
    DELETED_COUNT=$(find "$LOG_DIR" -type f -name "*.log*" -mtime +$RETENTION_DAYS -delete -print | wc -l)
    echo "Đã xóa $DELETED_COUNT files"
fi

echo "=========================================="
echo "Hoàn thành"
echo "=========================================="
