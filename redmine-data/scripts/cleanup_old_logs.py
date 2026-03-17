#!/usr/bin/env python3
"""
Script để dọn dẹp các file log cũ hơn 3 tháng (90 ngày)

Sử dụng:
    python scripts/cleanup_old_logs.py [--days 90] [--dry-run]

Options:
    --days: Số ngày retention (mặc định: 90)
    --dry-run: Chỉ hiển thị files sẽ bị xóa, không thực sự xóa
"""

import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_old_logs(log_dir: str, retention_days: int = 90, dry_run: bool = False):
    """
    Xóa các file log cũ hơn retention_days
    
    Args:
        log_dir: Thư mục chứa logs
        retention_days: Số ngày giữ lại logs (mặc định: 90)
        dry_run: Nếu True, chỉ hiển thị files sẽ bị xóa
    """
    log_path = Path(log_dir)
    
    if not log_path.exists():
        logger.warning(f"Log directory không tồn tại: {log_dir}")
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    logger.info(f"Đang tìm log files cũ hơn {retention_days} ngày (trước {cutoff_date.strftime('%Y-%m-%d')})")
    
    total_size = 0
    deleted_count = 0
    
    # Tìm tất cả các file .log trong thư mục và subdirectories
    for log_file in log_path.rglob("*.log*"):
        if log_file.is_file():
            # Lấy thời gian modified của file
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_mtime < cutoff_date:
                file_size = log_file.stat().st_size
                total_size += file_size
                
                size_mb = file_size / (1024 * 1024)
                logger.info(f"{'[DRY RUN] ' if dry_run else ''}Xóa: {log_file.relative_to(log_path)} ({size_mb:.2f} MB, modified: {file_mtime.strftime('%Y-%m-%d')})")
                
                if not dry_run:
                    try:
                        log_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Lỗi khi xóa {log_file}: {e}")
                else:
                    deleted_count += 1
    
    total_size_mb = total_size / (1024 * 1024)
    
    if deleted_count > 0:
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Đã xóa {deleted_count} files, tiết kiệm {total_size_mb:.2f} MB")
    else:
        logger.info(f"Không có file log nào cũ hơn {retention_days} ngày")


def main():
    parser = argparse.ArgumentParser(description="Dọn dẹp log files cũ")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Số ngày retention (mặc định: 90)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ hiển thị files sẽ bị xóa, không thực sự xóa"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Thư mục chứa logs (mặc định: logs)"
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("BẮT ĐẦU DỌN DẸP LOG FILES")
    logger.info(f"Thư mục: {args.log_dir}")
    logger.info(f"Retention: {args.days} ngày")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("="*80)
    
    cleanup_old_logs(args.log_dir, args.days, args.dry_run)
    
    logger.info("="*80)
    logger.info("HOÀN THÀNH")
    logger.info("="*80)


if __name__ == "__main__":
    main()
