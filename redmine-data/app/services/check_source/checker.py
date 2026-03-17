"""Lớp checker source chính.

Module này cung cấp SourceChecker class để kiểm tra và cập nhật sources:
- Source checking: Kiểm tra các sources có cần cập nhật không
- Priority checking: Ưu tiên check các sources quan trọng (outdated, failed)
- Resync sources: Re-sync các sources đã outdated hoặc failed
- Batch processing: Xử lý nhiều sources cùng lúc với limits
- Cancellation support: Hỗ trợ cancel job execution đang chạy

Hỗ trợ check cho Redmine issues và wiki pages, tự động phát hiện và sync các sources đã thay đổi.
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, case
from redminelib import Redmine

from app.database import SessionLocal
from app.models import Source
from app.config import settings
from app.services.redmine import RedmineSync
from app.services.check_source.issue_checker import check_issue_source
from app.services.check_source.wiki_checker import check_wiki_source
from app.services.check_source.resync_handler import resync_source

logger = logging.getLogger(__name__)


class SourceChecker:
    """Kiểm tra xem Redmine sources có cần được đồng bộ lại không.
    
    Class này kiểm tra các sources trong database để xem chúng có cần được
    sync lại từ Redmine không. So sánh updated_on trong database với
    updated_on trong Redmine để phát hiện sources đã outdated.
    
    Attributes:
        redmine: Redmine client instance
        redmine_sync: RedmineSync instance để thực hiện sync nếu cần
    """
    
    def __init__(self):
        """Khởi tạo SourceChecker với Redmine client và sync handler."""
        self.redmine = Redmine(
            settings.redmine_url,
            key=settings.redmine_api_key
        )
        self.redmine_sync = RedmineSync()
    
    def check_sources(self, limit: int = 1000, project_id: str = None, execution_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Kiểm tra các Redmine sources để xem có cần sync lại không.
        
        Hàm này query các sources chưa được kiểm tra trong 7 ngày (hoặc
        outdated > 30 ngày) và so sánh với Redmine để phát hiện updates.
        
        Logic query:
        - Sources chưa bao giờ được kiểm tra (last_sync_at = NULL)
        - Sources được kiểm tra > 7 ngày trước và không outdated
        - Sources outdated nhưng được kiểm tra > 30 ngày trước (recheck)
        
        Args:
            limit: Số lượng sources tối đa để kiểm tra (mặc định: 1000).
                Phải là số nguyên dương
            project_id: Project identifier để filter sources (tùy chọn).
                Nếu None, kiểm tra tất cả projects
            execution_id: ID của JobExecution để check cancellation (tùy chọn)
        
        Returns:
            Dict[str, Any]: Dictionary chứa kết quả:
                - checked: Số lượng sources đã kiểm tra (int)
                - outdated: Số lượng sources đã outdated (int)
                - up_to_date: Số lượng sources vẫn còn up-to-date (int)
                - failed: Số lượng sources kiểm tra thất bại (int)
                - errors: Danh sách error messages (List[str])
        
        Raises:
            ValueError: Nếu limit <= 0
            JobCancelledException: Nếu execution bị cancel trong quá trình check
        
        Note:
            - Chỉ kiểm tra redmine_issue và redmine_wiki sources
            - Sources được sắp xếp: non-outdated trước, sau đó theo last_sync_at (cũ nhất trước)
            - Progress được log mỗi 10 sources
            - Sources thất bại được đánh dấu sync_status='failed'
        """
        db = SessionLocal()
        result = {
            'checked': 0,
            'outdated': 0,
            'up_to_date': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Xác thực limit (mặc định là 1000, nhưng có thể ghi đè)
            if limit <= 0:
                raise ValueError("Limit must be positive integer")
            
            # Tính toán các ngày cutoff (sử dụng timezone local của server)
            cutoff_date = datetime.now() - timedelta(days=7)
            outdated_recheck_date = datetime.now() - timedelta(days=30)  # Kiểm tra lại sources outdated sau 30 ngày
            
            # Query sources với logic thông minh:
            # 1. Sources chưa bao giờ được kiểm tra (last_sync_at là NULL)
            # 2. Sources được kiểm tra > 7 ngày trước và không outdated
            # 3. Sources outdated nhưng được kiểm tra > 30 ngày trước (kiểm tra lại)
            query = db.query(Source).filter(
                or_(
                    Source.source_type == 'redmine_issue',
                    Source.source_type == 'redmine_wiki'
                )
            ).filter(
                or_(
                    # Sources chưa bao giờ được kiểm tra
                    Source.last_sync_at.is_(None),
                    # Sources được kiểm tra > 7 ngày trước và không outdated
                    and_(
                        Source.last_sync_at < cutoff_date,
                        Source.sync_status != 'outdated'
                    ),
                    # Sources outdated nhưng được kiểm tra > 30 ngày trước (kiểm tra lại)
                    and_(
                        Source.sync_status == 'outdated',
                        Source.last_sync_at < outdated_recheck_date
                    )
                )
            )
            
            if project_id:
                query = query.filter(Source.project_key == project_id)
            
            # Sắp xếp: non-outdated trước, sau đó theo last_sync_at (cũ nhất trước)
            query = query.order_by(
                case(
                    (Source.sync_status == 'outdated', 1),
                    else_=0
                ),
                Source.last_sync_at.asc().nullsfirst()
            )
            
            query = query.limit(limit)
            
            sources = query.all()
            logger.info(f"Checking {len(sources)} sources (not updated in 7 days or outdated > 30 days) for updates")
            
            # Import locally để tránh circular import
            from app.services.job_executor.executor import JobExecutor, JobCancelledException
            
            # Kiểm tra cancellation trước khi bắt đầu loop
            if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                logger.info(f"Source check cancelled before starting (execution {execution_id})")
                raise JobCancelledException("Job execution was cancelled")
            
            for source in sources:
                # Kiểm tra cancellation trước mỗi source
                if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                    logger.info(f"Source check cancelled during processing at source {source.id} (execution {execution_id})")
                    raise JobCancelledException("Job execution was cancelled during source check")
                
                try:
                    if source.source_type == 'redmine_issue':
                        check_result = check_issue_source(
                            source, self.redmine, self.redmine_sync, db, cutoff_date
                        )
                    elif source.source_type == 'redmine_wiki':
                        check_result = check_wiki_source(
                            source, self.redmine, self.redmine_sync, db, cutoff_date
                        )
                    else:
                        logger.warning(f"Unknown source type: {source.source_type}")
                        result['failed'] += 1
                        continue
                    
                    # Cập nhật kết quả dựa trên check_result
                    if check_result['status'] == 'outdated':
                        result['outdated'] += 1
                    elif check_result['status'] == 'up_to_date':
                        result['up_to_date'] += 1
                    else:  # failed
                        result['failed'] += 1
                        result['errors'].append(f"Source {source.id}: {check_result.get('error', 'Unknown error')}")
                        # Cập nhật trạng thái source khi có lỗi
                        try:
                            source.sync_status = 'failed'
                            source.error_message = check_result.get('error', 'Unknown error')[:500]
                            source.last_sync_at = datetime.now()
                            db.commit()
                        except Exception as commit_error:
                            logger.error(f"Failed to update source status on error: {commit_error}")
                            db.rollback()
                    
                    result['checked'] += 1
                    
                    if result['checked'] % 10 == 0:
                        logger.info(
                            f"Checked {result['checked']}/{len(sources)} sources "
                            f"(outdated: {result['outdated']}, up-to-date: {result['up_to_date']}, "
                            f"failed: {result['failed']})"
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to check source {source.id}: {e}", exc_info=True)
                        # Cập nhật trạng thái source khi có lỗi
                    try:
                        source.sync_status = 'failed'
                        source.error_message = str(e)[:500]
                        source.last_sync_at = datetime.now()
                        db.commit()
                    except Exception as commit_error:
                        logger.error(f"Failed to update source status on error: {commit_error}")
                        db.rollback()
                    
                    result['failed'] += 1
                    result['errors'].append(f"Source {source.id}: {str(e)}")
            
            logger.info(f"Source check completed: {result}")
            return result
            
        except JobCancelledException:
            # Re-raise cancellation exception để JobExecutor xử lý
            raise
        except Exception as e:
            logger.error(f"Source check failed: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()
    
    def check_single_source(self, source_id: str) -> Dict[str, Any]:
        """Kiểm tra một source cụ thể để xem có cần sync lại không.
        
        Hàm này kiểm tra một source đơn lẻ (phải là redmine_issue) bằng cách
        so sánh updated_on trong database với updated_on trong Redmine.
        
        Args:
            source_id: UUID của source cần kiểm tra (string)
        
        Returns:
            Dict[str, Any]: Dictionary chứa kết quả:
                - success: True nếu kiểm tra thành công, False nếu có lỗi (bool)
                - outdated: True nếu source đã outdated, False nếu không (bool, nếu success=True)
                - was_outdated: True nếu source đã outdated trước đó (bool, nếu success=True)
                - message: Thông báo kết quả (str, nếu success=True)
                - error: Error message nếu có lỗi (str, nếu success=False)
        
        Note:
            - Chỉ hỗ trợ redmine_issue sources
            - Issue ID được extract từ external_id (format: "redmine_issue_{id}")
            - Sử dụng check_issue_source() để thực hiện kiểm tra
            - Cutoff date là 7 ngày trước
        """
        db = SessionLocal()
        try:
            from uuid import UUID
            
            source = db.query(Source).filter(Source.id == UUID(source_id)).first()
            if not source:
                return {
                    'success': False,
                    'error': 'Source not found'
                }
            
            if source.source_type != 'redmine_issue':
                return {
                    'success': False,
                    'error': 'Source is not a Redmine issue'
                }
            
            # Trích xuất issue_id từ external_id
            if not source.external_id or not source.external_id.startswith('redmine_issue_'):
                return {
                    'success': False,
                    'error': 'Invalid external_id format'
                }
            
            issue_id = int(source.external_id.replace('redmine_issue_', ''))
            
            # Sử dụng issue checker
            cutoff_date = datetime.now() - timedelta(days=7)
            check_result = check_issue_source(
                source, self.redmine, self.redmine_sync, db, cutoff_date
            )
            
            if check_result['status'] == 'failed':
                return {
                    'success': False,
                    'error': check_result.get('error', 'Unknown error')
                }
            
            was_outdated = source.sync_status == 'outdated'
            return {
                'success': True,
                'outdated': check_result['status'] == 'outdated',
                'was_outdated': was_outdated,
                'message': 'Source is up to date' if check_result['status'] == 'up_to_date' else 'Source marked as outdated'
            }
                
        except Exception as e:
            logger.error(f"Failed to check source {source_id}: {e}", exc_info=True)
            db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            db.close()
    
    def resync_source(self, source_id: str) -> Dict[str, Any]:
        """Đồng bộ lại một source từ Redmine.
        
        Hàm này thực hiện sync lại một source cụ thể từ Redmine, bất kể
        trạng thái hiện tại. Sử dụng resync_handler để xử lý.
        
        Args:
            source_id: UUID của source cần đồng bộ lại (string)
        
        Returns:
            Dict[str, Any]: Dictionary chứa kết quả sync từ resync_handler:
                - status: Trạng thái sync ('success', 'failed')
                - processed: Số lượng items đã xử lý (int)
                - created: Số lượng items đã tạo (int)
                - updated: Số lượng items đã cập nhật (int)
                - failed: Số lượng items thất bại (int)
                - errors: Danh sách error messages (List[str])
        
        Note:
            - Wrapper function gọi resync_handler.resync_source()
            - Source sẽ được sync lại hoàn toàn (tạo lại chunks/embeddings)
        """
        return resync_source(source_id, self.redmine, self.redmine_sync)

