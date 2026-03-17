"""Checker source wiki.

Module này cung cấp function để kiểm tra Redmine wiki page sources:
- check_wiki_source: Kiểm tra xem wiki source có cần cập nhật không
- Content comparison: So sánh content hash để phát hiện thay đổi
- Status update: Cập nhật sync_status trong database

Sử dụng SHA1 hash để phát hiện thay đổi nội dung wiki page.
"""
import logging
import time
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from redminelib import Redmine

from app.models import Source
from app.services.redmine import RedmineSync
from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiting: độ trễ giữa các lời gọi Redmine API (tính bằng giây)
REDMINE_API_DELAY = float(getattr(settings, 'redmine_api_delay', 0.2))


def check_wiki_source(
    source: Source,
    redmine: Redmine,
    redmine_sync: RedmineSync,
    db: Session,
    cutoff_date: datetime
) -> dict:
    """Kiểm tra một Redmine wiki source để xem có cần sync lại không.
    
    Hàm này so sánh content hash của wiki page trong database với content hash
    trong Redmine để phát hiện updates. Nếu hash khác nhau, đánh dấu source
    là outdated. Nếu giống nhau, cập nhật last_sync_at.
    
    Quy trình:
    1. Parse project_id và page_title từ external_id
    2. Lấy wiki page từ Redmine API
    3. Build wiki content và tính hash
    4. So sánh với hash trong database
    5. Cập nhật sync_status và last_sync_at
    
    Args:
        source: Source object cần kiểm tra (phải là redmine_wiki)
        redmine: Redmine client instance
        redmine_sync: RedmineSync instance để build wiki content
        db: Database session
        cutoff_date: Ngày cutoff để kiểm tra race condition (datetime)
    
    Returns:
        dict: Dictionary chứa kết quả:
            - status: 'outdated' | 'up_to_date' | 'failed' (str)
            - error: Error message nếu status='failed' (str, optional)
    
    Note:
        - External ID format: "redmine_wiki_{project_id}_{page_title}"
        - Rate limiting được áp dụng trước khi gọi Redmine API
        - Race condition được xử lý bằng cách refresh source và kiểm tra last_sync_at
        - Nếu source vừa được resync (last_sync_at > cutoff_date), trả về 'up_to_date'
        - Content hash được tính từ wiki page text content
    """
    try:
        # Trích xuất project_id và page_title từ external_id (định dạng: "redmine_wiki_{project_id}_{page_title}")
        if not source.external_id or not source.external_id.startswith('redmine_wiki_'):
            logger.warning(f"Invalid external_id format: {source.external_id}")
            return {'status': 'failed', 'error': 'Invalid external_id format'}
        
        # Parse: redmine_wiki_{project_id}_{page_title}
        parts = source.external_id.replace('redmine_wiki_', '').split('_', 1)
        if len(parts) != 2:
            logger.warning(f"Invalid wiki external_id format: {source.external_id}")
            return {'status': 'failed', 'error': 'Invalid wiki external_id format'}
        
        wiki_project_id = parts[0]
        wiki_page_title = parts[1]
        
        # Rate limiting: độ trễ trước khi gọi API
        time.sleep(REDMINE_API_DELAY)
        
        # Lấy wiki page hiện tại từ Redmine
        wiki_page = redmine.wiki_page.get(wiki_page_title, project_id=wiki_project_id)
        
        # Xây dựng content và tính hash
        content = redmine_sync._build_wiki_content(wiki_page)
        new_hash = hashlib.sha1(content.encode()).hexdigest()
        
        # So sánh với hash đã lưu
        if source.sha1_content != new_hash:
            # Content đã thay đổi - đánh dấu là outdated (không cập nhật sha1_content cho đến khi resync)
            # Refresh source để tránh race condition với resync đồng thời
            db.refresh(source)
            # Kiểm tra lại last_sync_at để tránh race condition
            if source.last_sync_at and source.last_sync_at > cutoff_date:
                # Source vừa được resync, bỏ qua
                logger.debug(f"Source {source.id} (wiki {wiki_project_id}/{wiki_page_title}) was just resynced, skipping")
                return {'status': 'up_to_date'}
            else:
                source.sync_status = 'outdated'
                source.last_sync_at = datetime.now()  # Cập nhật để tránh kiểm tra lại ngay lập tức
                db.commit()
                logger.info(f"Source {source.id} (wiki {wiki_project_id}/{wiki_page_title}) marked as outdated")
                return {'status': 'outdated'}
        else:
            # Content giống nhau - cập nhật last_sync_at và sync_status nếu cần
            was_outdated = source.sync_status == 'outdated'
            if was_outdated:
                source.sync_status = 'success'
            source.last_sync_at = datetime.now()  # Cập nhật để tránh kiểm tra lại
            db.commit()
            if was_outdated:
                logger.info(f"Source {source.id} (wiki {wiki_project_id}/{wiki_page_title}) is now up to date (was outdated)")
            else:
                logger.debug(f"Source {source.id} (wiki {wiki_project_id}/{wiki_page_title}) is up to date")
            return {'status': 'up_to_date'}
            
    except Exception as e:
        logger.error(f"Failed to check wiki source {source.id}: {e}", exc_info=True)
        return {'status': 'failed', 'error': str(e)}

