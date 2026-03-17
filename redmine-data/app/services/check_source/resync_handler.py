"""Handler đồng bộ lại cho sources.

Module này cung cấp function để re-synchronize sources:
- resync_source: Re-sync một source cụ thể (issue hoặc wiki page)
- Source type detection: Tự động phát hiện source type và gọi handler phù hợp
- Error handling: Xử lý lỗi và cập nhật sync status

Hỗ trợ re-sync cho cả Redmine issues và wiki pages.
"""
import logging
import time
from datetime import datetime
from sqlalchemy.orm import Session
from redminelib import Redmine
from uuid import UUID

from app.database import SessionLocal
from app.models import Source
from app.services.redmine import RedmineSync
from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiting: độ trễ giữa các lời gọi Redmine API (tính bằng giây)
REDMINE_API_DELAY = float(getattr(settings, 'redmine_api_delay', 0.2))


def resync_source(
    source_id: str,
    redmine: Redmine,
    redmine_sync: RedmineSync
) -> dict:
    """Đồng bộ lại một source từ Redmine, bất kể trạng thái hiện tại.
    
    Hàm này thực hiện sync lại hoàn toàn một source (issue hoặc wiki page)
    từ Redmine. Khác với check, hàm này luôn sync lại, tạo lại chunks và
    embeddings nếu cần.
    
    Quy trình:
    1. Lấy source từ database
    2. Xác định loại source (issue hoặc wiki)
    3. Extract ID từ external_id
    4. Lấy data từ Redmine API
    5. Sync lại bằng IssueSyncHandler hoặc WikiSyncHandler
    6. Cập nhật sync_status và last_sync_at
    
    Args:
        source_id: UUID của source cần đồng bộ lại (string)
        redmine: Redmine client instance
        redmine_sync: RedmineSync instance (không được sử dụng trực tiếp)
    
    Returns:
        dict: Dictionary chứa kết quả:
            - success: True nếu sync thành công, False nếu có lỗi (bool)
            - message: Thông báo kết quả (str, nếu success=True)
            - error: Error message nếu có lỗi (str, nếu success=False)
    
    Note:
        - Hỗ trợ redmine_issue và redmine_wiki sources
        - Tạo database session mới và đóng sau khi xong
        - Rate limiting được áp dụng trước khi gọi Redmine API
        - Sync status luôn được cập nhật thành 'success' sau khi sync thành công
        - last_sync_at luôn được cập nhật, kể cả khi content không thay đổi
        - Chunks và embeddings được tạo lại nếu content thay đổi
    """
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == UUID(source_id)).first()
        if not source:
            return {
                'success': False,
                'error': 'Source not found'
            }
        
        if source.source_type == 'redmine_issue':
            # Trích xuất issue_id và project_id từ source
            if not source.external_id or not source.external_id.startswith('redmine_issue_'):
                return {
                    'success': False,
                    'error': 'Invalid external_id format'
                }
            
            issue_id = int(source.external_id.replace('redmine_issue_', ''))
            project_id = source.project_key or str(source.project_id) if source.project_id else None
            
            if not project_id:
                return {
                    'success': False,
                    'error': 'Project ID not found'
                }
            
            # Rate limiting: độ trễ trước khi gọi API
            time.sleep(REDMINE_API_DELAY)
            
            # Lấy issue từ Redmine
            issue = redmine.issue.get(
                issue_id,
                include=['children', 'attachments', 'relations', 'changesets', 'journals', 'watchers']
            )
            
            # Đồng bộ lại issue sử dụng issue sync handler
            from app.services.redmine.issue_sync import IssueSyncHandler
            from app.services.redmine.content_builder import ContentBuilder
            from app.services.redmine.attachment_handler import AttachmentHandler
            
            content_builder = ContentBuilder(redmine)
            attachment_handler = AttachmentHandler(redmine)
            issue_sync_handler = IssueSyncHandler(content_builder, attachment_handler)
            
            updated_source = issue_sync_handler.sync_issue(issue, project_id, db)
            
            if updated_source:
                # Luôn cập nhật sync status và last_sync_at khi resync (kể cả khi content không thay đổi)
                updated_source.sync_status = 'success'
                updated_source.last_sync_at = datetime.now()  # Luôn cập nhật khi resync
                db.commit()
                
                return {
                    'success': True,
                    'message': f'Source re-synced successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to re-sync source'
                }
        
        elif source.source_type == 'redmine_wiki':
            # Trích xuất project_id và page_title từ source
            if not source.external_id or not source.external_id.startswith('redmine_wiki_'):
                return {
                    'success': False,
                    'error': 'Invalid external_id format'
                }
            
            # Parse: redmine_wiki_{project_id}_{page_title}
            parts = source.external_id.replace('redmine_wiki_', '').split('_', 1)
            if len(parts) != 2:
                return {
                    'success': False,
                    'error': 'Invalid wiki external_id format'
                }
            
            wiki_project_id = parts[0]
            wiki_page_title = parts[1]
            
            # Rate limiting: độ trễ trước khi gọi API
            time.sleep(REDMINE_API_DELAY)
            
            # Lấy wiki page từ Redmine
            wiki_page = redmine.wiki_page.get(wiki_page_title, project_id=wiki_project_id)
            
            # Đồng bộ lại wiki page sử dụng wiki sync handler
            from app.services.redmine.wiki_sync import WikiSyncHandler
            from app.services.redmine.content_builder import ContentBuilder
            
            content_builder = ContentBuilder(redmine)
            wiki_sync_handler = WikiSyncHandler(redmine, content_builder)
            
            wiki_sync_handler.sync_wiki_page(wiki_page, wiki_project_id, db)
            
            # Luôn cập nhật sync status và last_sync_at khi resync (kể cả khi content không thay đổi)
            source.sync_status = 'success'
            source.last_sync_at = datetime.now()  # Luôn cập nhật khi resync
            db.commit()
            
            return {
                'success': True,
                'message': f'Source re-synced successfully'
            }
        
        else:
            return {
                'success': False,
                'error': 'Source type not supported for resync'
            }
            
    except Exception as e:
        logger.error(f"Failed to re-sync source {source_id}: {e}", exc_info=True)
        db.rollback()
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        db.close()

