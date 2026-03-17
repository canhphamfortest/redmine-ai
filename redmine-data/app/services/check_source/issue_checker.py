"""Checker source issue.

Module này cung cấp function để kiểm tra Redmine issue sources:
- check_issue_source: Kiểm tra xem issue source có cần cập nhật không
- Content comparison: So sánh content hash để phát hiện thay đổi
- Status update: Cập nhật sync_status trong database

Sử dụng SHA1 hash để phát hiện thay đổi nội dung issue (description, comments, attachments).
"""
import logging
import time
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from redminelib import Redmine

from app.models import Source
from app.services.redmine import RedmineSync, safe_attr
from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiting: độ trễ giữa các lời gọi Redmine API (tính bằng giây)
REDMINE_API_DELAY = float(getattr(settings, 'redmine_api_delay', 0.2))


def check_issue_source(
    source: Source,
    redmine: Redmine,
    redmine_sync: RedmineSync,
    db: Session,
    cutoff_date: datetime
) -> dict:
    """Kiểm tra một Redmine issue source để xem có cần sync lại không.
    
    Hàm này so sánh content hash của issue trong database với content hash
    trong Redmine để phát hiện updates. Nếu hash khác nhau, đánh dấu source
    là outdated. Nếu giống nhau, cập nhật last_sync_at.
    
    Quy trình:
    1. Extract issue_id từ external_id
    2. Lấy issue từ Redmine API
    3. Build issue content và tính hash
    4. So sánh với hash trong database
    5. Cập nhật sync_status và last_sync_at
    
    Args:
        source: Source object cần kiểm tra (phải là redmine_issue)
        redmine: Redmine client instance
        redmine_sync: RedmineSync instance để build issue content
        db: Database session
        cutoff_date: Ngày cutoff để kiểm tra race condition (datetime)
    
    Returns:
        dict: Dictionary chứa kết quả:
            - status: 'outdated' | 'up_to_date' | 'failed' (str)
            - error: Error message nếu status='failed' (str, optional)
    
    Note:
        - External ID format: "redmine_issue_{issue_id}"
        - Rate limiting được áp dụng trước khi gọi Redmine API
        - Race condition được xử lý bằng cách refresh source và kiểm tra last_sync_at
        - Nếu source vừa được resync (last_sync_at > cutoff_date), trả về 'up_to_date'
        - Content hash được tính từ issue content (description, comments, attachments)
    """
    try:
        # Trích xuất issue_id từ external_id (định dạng: "redmine_issue_{issue_id}")
        if not source.external_id or not source.external_id.startswith('redmine_issue_'):
            logger.warning(f"Invalid external_id format: {source.external_id}")
            return {'status': 'failed', 'error': 'Invalid external_id format'}
        
        issue_id = int(source.external_id.replace('redmine_issue_', ''))
        
        # Rate limiting: độ trễ trước khi gọi API
        time.sleep(REDMINE_API_DELAY)
        
        # Lấy issue hiện tại từ Redmine
        issue = redmine.issue.get(
            issue_id,
            include=['children', 'attachments', 'relations', 'changesets', 'journals', 'watchers']
        )
        
        # Xây dựng content và tính hash
        content = redmine_sync._build_issue_content(issue)
        new_hash = hashlib.sha1(content.encode()).hexdigest()
        
        # So sánh với hash đã lưu
        if source.sha1_content != new_hash:
            # Content đã thay đổi - đánh dấu là outdated (không cập nhật sha1_content cho đến khi resync)
            # Refresh source để tránh race condition với resync đồng thời
            db.refresh(source)
            # Kiểm tra lại last_sync_at để tránh race condition
            if source.last_sync_at and source.last_sync_at > cutoff_date:
                # Source vừa được resync, bỏ qua
                logger.debug(f"Source {source.id} (issue {issue_id}) was just resynced, skipping")
                return {'status': 'up_to_date'}
            else:
                source.sync_status = 'outdated'
                source.last_sync_at = datetime.now()  # Cập nhật để tránh kiểm tra lại ngay lập tức
                db.commit()
                logger.info(f"Source {source.id} (issue {issue_id}) marked as outdated")
                return {'status': 'outdated'}
        else:
            # Content giống nhau - cập nhật last_sync_at và sync_status nếu cần
            was_outdated = source.sync_status == 'outdated'
            if was_outdated:
                source.sync_status = 'success'
            source.last_sync_at = datetime.now()  # Cập nhật để tránh kiểm tra lại
            db.commit()
            if was_outdated:
                logger.info(f"Source {source.id} (issue {issue_id}) is now up to date (was outdated)")
            else:
                logger.debug(f"Source {source.id} (issue {issue_id}) is up to date")
            return {'status': 'up_to_date'}
            
    except Exception as e:
        logger.error(f"Failed to check issue source {source.id}: {e}", exc_info=True)
        return {'status': 'failed', 'error': str(e)}

