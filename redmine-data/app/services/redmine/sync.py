"""Điều phối sync Redmine chính.

Module này cung cấp RedmineSync class - orchestrator chính cho Redmine synchronization:
- Project sync: Đồng bộ toàn bộ project (issues và wiki pages)
- Issue sync: Đồng bộ issues với filters và incremental support
- Wiki sync: Đồng bộ wiki pages với incremental support
- Rate limiting: Quản lý rate limiting để tránh overload Redmine API
- Cancellation support: Hỗ trợ cancel job execution đang chạy

Sử dụng các handlers (IssueSyncHandler, WikiSyncHandler) để thực hiện sync operations.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from uuid import UUID
from redminelib import Redmine
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Source
from app.config import settings
from app.services.redmine.utils import safe_attr, sanitize_string
from app.services.redmine.content_builder import ContentBuilder
from app.services.redmine.attachment_handler import AttachmentHandler
from app.services.redmine.issue_sync import IssueSyncHandler
from app.services.redmine.wiki_sync import WikiSyncHandler

logger = logging.getLogger(__name__)

# Rate limiting: độ trễ giữa các lời gọi Redmine API (tính bằng giây)
REDMINE_API_DELAY = float(getattr(settings, 'redmine_api_delay', 0.2))


class RedmineSync:
    """Đồng bộ dữ liệu từ Redmine"""
    
    def __init__(self):
        if not settings.redmine_url or not settings.redmine_api_key:
            raise ValueError("Redmine URL and API key not configured")
        
        base_url = settings.redmine_url
        # Khởi tạo Redmine với xác thực API key
        self.redmine = Redmine(
            base_url,
            key=settings.redmine_api_key
        )
        logger.info(f"Redmine client initialized with URL: {base_url}, API key: {settings.redmine_api_key[:10]}...")
        
        # Khởi tạo handlers
        self.content_builder = ContentBuilder(self.redmine)
        self.attachment_handler = AttachmentHandler(self.redmine)
        self.issue_sync_handler = IssueSyncHandler(self.content_builder, self.attachment_handler)
        self.wiki_sync_handler = WikiSyncHandler(self.redmine, self.content_builder)
    
    def sync_project(
        self,
        project_id: str,
        incremental: bool = True,
        filters: Dict[str, Any] = None,
        execution_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Đồng bộ tất cả issues từ một Redmine project
        
        Args:
            project_id: Redmine project identifier
            incremental: Chỉ đồng bộ các issues đã cập nhật kể từ lần sync cuối
            filters: Bộ lọc bổ sung (status, tracker, etc.)
            execution_id: ID của JobExecution để check cancellation (tùy chọn)
        
        Returns:
            {
                'processed': int,
                'created': int,
                'updated': int,
                'failed': int,
                'errors': List[str]
            }
        
        Raises:
            JobCancelledException: Nếu execution bị cancel trong quá trình sync
        """
        # Import locally để tránh circular import
        from app.services.job_executor.executor import JobExecutor, JobCancelledException
        
        db = SessionLocal()
        
        try:
            result = {
                'processed': 0,
                'created': 0,
                'updated': 0,
                'failed': 0,
                'errors': []
            }
            
            # Kiểm tra cancellation trước khi bắt đầu
            if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                logger.info(f"Sync cancelled before starting for execution {execution_id}")
                raise JobCancelledException("Job execution was cancelled")
            
            # Xây dựng bộ lọc query
            query_filters = self._build_query_filters(project_id, filters, incremental, db)
            
            # Lấy issues (trước tiên lấy danh sách issue IDs)
            logger.info(f"Fetching issues from project {project_id} with filters: {query_filters}")
            issues_list = self.redmine.issue.filter(**query_filters)
            
            # Thu thập issue IDs trước
            issue_ids = [issue.id for issue in issues_list]
            logger.info(f"Found {len(issue_ids)} issues to sync")
            
            # Xử lý từng issue, check cancellation định kỳ
            for issue_id in issue_ids:
                # Kiểm tra cancellation trước mỗi issue
                if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                    logger.info(f"Sync cancelled during processing at issue {issue_id} (execution {execution_id})")
                    raise JobCancelledException("Job execution was cancelled during sync")
                
                self._process_single_issue(issue_id, project_id, result)
            
            logger.info(f"Sync completed: {result}")
            
            return result
            
        except JobCancelledException:
            # Re-raise cancellation exception để JobExecutor xử lý
            raise
        except Exception as e:
            logger.error(f"Project sync failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def _build_query_filters(
        self,
        project_id: str,
        filters: Optional[Dict[str, Any]],
        incremental: bool,
        db: Session
    ) -> Dict[str, Any]:
        """Xây dựng bộ lọc query để lấy issues từ Redmine API.
        
        Hàm này tạo dictionary filters để truyền vào Redmine API filter().
        Hỗ trợ incremental sync bằng cách thêm filter updated_on dựa trên
        thời gian sync cuối cùng.
        
        Args:
            project_id: Redmine project identifier (string)
            filters: Dictionary filters bổ sung (status_id, tracker_id, etc.)
            incremental: Có sử dụng incremental sync không (bool).
                Nếu True, chỉ lấy issues đã cập nhật kể từ lần sync cuối
            db: Database session để query thời gian sync cuối
        
        Returns:
            Dict[str, Any]: Dictionary filters cho Redmine API, bao gồm:
                - project_id: Project identifier
                - status_id: Status filter (mặc định '*' để lấy tất cả status, bao gồm closed)
                - tracker_id: Tracker filter (nếu có trong filters)
                - updated_on: Date filter cho incremental sync (nếu incremental=True)
        """
        query_filters = {'project_id': project_id}
        
        # Mặc định lấy tất cả status (bao gồm cả closed issues)
        # Chỉ override nếu filters có chỉ định status_id cụ thể
        if filters and filters.get('status_id'):
            query_filters['status_id'] = filters['status_id']
        else:
            # Sử dụng '*' để lấy tất cả status (open và closed)
            query_filters['status_id'] = '*'
        
        if filters:
            if filters.get('tracker_id'):
                query_filters['tracker_id'] = filters['tracker_id']
        
        # Lấy thời gian sync cuối cùng cho incremental sync
        if incremental:
            last_sync = self._get_last_sync_time(project_id, db)
            if last_sync:
                query_filters['updated_on'] = f">={last_sync.strftime('%Y-%m-%d')}"
        
        return query_filters
    
    def _get_last_sync_time(self, project_id: str, db: Session):
        """Lấy thời gian sync cuối cùng cho một project để thực hiện incremental sync.
        
        Hàm này query database để tìm thời gian updated_at mới nhất của các sources
        thuộc project này. Sử dụng để filter chỉ lấy issues đã cập nhật kể từ
        lần sync cuối.
        
        Args:
            project_id: Redmine project identifier (string)
            db: Database session
        
        Returns:
            datetime | None: Thời gian sync cuối cùng (updated_at) nếu có,
                None nếu chưa có sync nào cho project này
        """
        last_sync = db.query(Source.updated_at)\
            .filter(Source.source_type == 'redmine_issue')\
            .filter(Source.project_key == project_id)\
            .order_by(Source.updated_at.desc())\
            .first()
        
        return last_sync[0] if last_sync else None
    
    def _process_single_issue(
        self,
        issue_id: int,
        project_id: str,
        result: Dict[str, Any]
    ) -> None:
        """Xử lý sync một issue đơn lẻ với error handling đầy đủ.
        
        Hàm này xử lý sync một issue với các bước:
        1. Lấy hoặc chuẩn bị source record
        2. Rate limiting (delay trước khi gọi API)
        3. Lấy issue từ Redmine API với tất cả dữ liệu liên quan
        4. Sync issue (tạo/update source, chunks, embeddings)
        5. Cập nhật sync status và result statistics
        
        Args:
            issue_id: ID của issue cần sync (int)
            project_id: Redmine project identifier (string)
            result: Dictionary chứa statistics (processed, failed, errors) - sẽ được modify
        
        Note:
            - Sử dụng session riêng cho mỗi issue để tránh transaction conflicts
            - Rate limiting được áp dụng trước mỗi API call
            - Lỗi được log và ghi vào result['errors']
            - Progress được log mỗi 10 issues
        """
        issue_db = SessionLocal()
        try:
            source = self._get_source_for_issue(issue_id, issue_db)
            
            try:
                # Rate limiting: độ trễ trước khi gọi API
                time.sleep(REDMINE_API_DELAY)
                
                # Lấy issue với tất cả dữ liệu liên quan
                issue = self.redmine.issue.get(
                    issue_id,
                    include=['children', 'attachments', 'relations', 'changesets', 'journals', 'watchers']
                )
                
                # Đồng bộ issue (sẽ tạo source nếu chưa tồn tại)
                source = self.issue_sync_handler.sync_issue(issue, project_id, issue_db)
                
                # Cập nhật sync status của source khi thành công
                if source:
                    source.sync_status = 'success'
                    source.error_message = None
                    source.retry_count = 0
                
                issue_db.commit()
                result['processed'] += 1
                
                if result['processed'] % 10 == 0:
                    logger.info(f"Processed {result['processed']} issues")
                    
            except Exception as e:
                self._handle_issue_sync_error(issue_id, source, e, issue_db, result)
                
        except Exception as e:
            # Exception handler ngoài cùng cho các lỗi không mong đợi
            logger.error(f"Unexpected error processing issue {issue_id}: {e}", exc_info=True)
            try:
                issue_db.rollback()
            except:
                pass
            result['failed'] += 1
            result['errors'].append(f"Issue {issue_id}: {str(e)}")
        finally:
            issue_db.close()
    
    def _get_source_for_issue(self, issue_id: int, db: Session):
        """Lấy hoặc chuẩn bị source record cho issue.
        
        Hàm này tìm source record đã tồn tại cho issue, hoặc trả về None nếu
        chưa có. Nếu source tồn tại, sẽ cập nhật sync_status thành 'pending'
        để đánh dấu đang xử lý.
        
        Args:
            issue_id: ID của issue (int)
            db: Database session
        
        Returns:
            Source | None: Source object nếu tìm thấy, None nếu chưa có
        
        Note:
            - External ID format: "redmine_issue_{issue_id}"
            - Sync status được set thành 'pending' nếu source tồn tại
        """
        external_id = f"redmine_issue_{issue_id}"
        source = db.query(Source).filter(
            Source.source_type == 'redmine_issue',
            Source.external_id == external_id
        ).first()
        
        # Cập nhật sync status của source thành processing
        if source:
            source.sync_status = 'pending'
            db.flush()
        
        return source
    
    def _handle_issue_sync_error(
        self,
        issue_id: int,
        source,
        error: Exception,
        db: Session,
        result: Dict[str, Any]
    ) -> None:
        """Xử lý lỗi trong quá trình sync issue và cập nhật statistics.
        
        Hàm này cập nhật source record với thông tin lỗi và cập nhật result
        statistics. Error message được giới hạn độ dài để tránh database issues.
        
        Args:
            issue_id: ID của issue bị lỗi (int)
            source: Source object (có thể None nếu chưa tạo)
            error: Exception object chứa thông tin lỗi
            db: Database session
            result: Dictionary chứa statistics (sẽ được modify)
        
        Note:
            - Sync status được set thành 'failed'
            - Error message được giới hạn 1000 ký tự
            - Retry count được tăng lên
            - Lỗi được log với full traceback
        """
        if source:
            source.sync_status = 'failed'
            source.error_message = sanitize_string(str(error)[:1000])  # Giới hạn độ dài error message và loại bỏ null bytes
            source.retry_count = (source.retry_count or 0) + 1
        db.commit()
        
        logger.error(f"Failed to sync issue {issue_id}: {error}", exc_info=True)
        result['failed'] += 1
        result['errors'].append(f"Issue {issue_id}: {str(error)}")
    
    def sync_single_issue(self, issue_id: int) -> Dict[str, Any]:
        """Đồng bộ một issue"""
        db = SessionLocal()
        
        try:
            # Rate limiting: độ trễ trước khi gọi API
            time.sleep(REDMINE_API_DELAY)
            
            # Bao gồm tất cả dữ liệu liên quan: children, attachments, relations, changesets, journals, watchers
            issue = self.redmine.issue.get(
                issue_id, 
                include=['children', 'attachments', 'relations', 'changesets', 'journals', 'watchers']
            )
            
            # Lấy project_id từ issue
            project_id = None
            if hasattr(issue, 'project'):
                project_id = (
                    safe_attr(issue.project, 'identifier')
                    or safe_attr(issue.project, 'name')
                    or str(safe_attr(issue.project, 'id'))
                )
            
            self.issue_sync_handler.sync_issue(issue, project_id or 'unknown', db)
            db.commit()
            
            return {
                'status': 'success',
                'issue_id': issue_id
            }
            
        except Exception as e:
            logger.error(f"Failed to sync issue {issue_id}: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def sync_wiki_page(
        self,
        project_id: str,
        wiki_page_title: str,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """Đồng bộ một wiki page"""
        db = SessionLocal()
        
        try:
            # Rate limiting: độ trễ trước khi gọi API
            time.sleep(REDMINE_API_DELAY)
            
            # Lấy wiki page
            if version:
                wiki_page = self.redmine.wiki_page.get(wiki_page_title, project_id=project_id, version=version)
            else:
                wiki_page = self.redmine.wiki_page.get(wiki_page_title, project_id=project_id)
            
            self.wiki_sync_handler.sync_wiki_page(wiki_page, project_id, db)
            db.commit()
            
            return {
                'status': 'success',
                'project_id': project_id,
                'wiki_page': wiki_page_title,
                'version': version or wiki_page.version if hasattr(wiki_page, 'version') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to sync wiki page {wiki_page_title} from project {project_id}: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def sync_project_wiki(
        self,
        project_id: str,
        incremental: bool = True
    ) -> Dict[str, Any]:
        """Đồng bộ tất cả wiki pages từ một Redmine project"""
        db = SessionLocal()
        
        try:
            result = {
                'processed': 0,
                'created': 0,
                'updated': 0,
                'failed': 0,
                'errors': []
            }
            
            # Rate limiting: độ trễ trước khi gọi API
            time.sleep(REDMINE_API_DELAY)
            
            # Lấy project
            project = self.redmine.project.get(project_id)
            
            # Rate limiting: độ trễ trước khi gọi API
            time.sleep(REDMINE_API_DELAY)
            
            # Lấy tất cả wiki pages
            wiki_page_titles = self._find_all_wiki_pages(project_id)
            
            # Lấy thời gian sync cuối cùng cho incremental sync
            last_sync = None
            if incremental:
                last_sync = db.query(Source.updated_at)\
                    .filter(Source.source_type == 'redmine_wiki')\
                    .filter(Source.project_key == project_id)\
                    .order_by(Source.updated_at.desc())\
                    .first()
            
            logger.info(f"Found {len(wiki_page_titles)} wiki pages in project {project_id}: {wiki_page_titles}")
            
            # Xử lý từng wiki page
            for page_title in wiki_page_titles:
                self._process_wiki_page(page_title, project_id, incremental, last_sync, result, db)
            
            # Commit tất cả các pages thành công
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Failed to commit transaction: {e}")
                db.rollback()
                raise
            
            logger.info(f"Wiki sync completed: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Project wiki sync failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    
    def _find_all_wiki_pages(self, project_id: str) -> List[str]:
        """Tìm tất cả wiki pages cho một project, bao gồm Start page"""
        wiki_page_titles = []
        found_start_page = False
        
        try:
            wiki_pages = self.redmine.wiki_page.filter(project_id=project_id)
            # Chuyển đổi thành list để lấy tất cả titles
            for page in wiki_pages:
                if hasattr(page, 'title'):
                    wiki_page_titles.append(page.title)
                    # Kiểm tra xem đây có phải là Start page không
                    if page.title.lower() in ['start', 'home', 'welcome']:
                        found_start_page = True
                elif isinstance(page, dict):
                    title = page.get('title')
                    if title:
                        wiki_page_titles.append(title)
                        if title.lower() in ['start', 'home', 'welcome']:
                            found_start_page = True
            
            # Ghi log tất cả pages tìm được để debug
            logger.info(f"Found wiki page titles from filter: {wiki_page_titles}")
            
            # Thử tìm Start page nếu không tìm thấy trong filter
            if not found_start_page:
                found_start_page = self._find_start_page(project_id, wiki_page_titles)
            
        except Exception as e:
            logger.warning(f"Could not list wiki pages for project {project_id}: {e}")
            wiki_page_titles = []
            
            # Ngay cả khi filter thất bại, thử lấy Start page trực tiếp
            try:
                time.sleep(REDMINE_API_DELAY)
                start_page = self.redmine.wiki_page.get('Start', project_id=project_id)
                if start_page and hasattr(start_page, 'title'):
                    wiki_page_titles.append(start_page.title)
                    logger.info(f"Got Start page directly: {start_page.title}")
            except Exception as e2:
                logger.debug(f"Could not get Start page directly: {e2}")
        
        return wiki_page_titles
    
    def _find_start_page(self, project_id: str, wiki_page_titles: List[str]) -> bool:
        """Tìm Start page bằng các phương pháp khác nhau"""
        # Thử các tên ứng viên
        start_page_candidates = ['Start', 'Home', 'Wiki', 'Welcome']
        for start_page_name in start_page_candidates:
            try:
                time.sleep(REDMINE_API_DELAY)
                start_page = self.redmine.wiki_page.get(start_page_name, project_id=project_id)
                if start_page and hasattr(start_page, 'title'):
                    if start_page.title not in wiki_page_titles:
                        logger.info(f"Found Start page '{start_page.title}' that wasn't in filter results, adding it")
                        wiki_page_titles.insert(0, start_page.title)
                        return True
            except Exception as e:
                logger.debug(f"Start page candidate '{start_page_name}' not found: {e}")
                continue
        
        # Thử empty string (một số instance Redmine sử dụng điều này)
        try:
            time.sleep(REDMINE_API_DELAY)
            start_page = self.redmine.wiki_page.get('', project_id=project_id)
            if start_page and hasattr(start_page, 'title'):
                if start_page.title not in wiki_page_titles:
                    logger.info(f"Found Start page via empty title: '{start_page.title}'")
                    wiki_page_titles.insert(0, start_page.title)
                    return True
        except Exception as e:
            logger.debug(f"Could not get Start page via empty title: {e}")
            # Thử một lần nữa với 'Start' rõ ràng
            try:
                time.sleep(REDMINE_API_DELAY)
                start_page = self.redmine.wiki_page.get('Start', project_id=project_id)
                if start_page and hasattr(start_page, 'title'):
                    if start_page.title not in wiki_page_titles:
                        logger.info(f"Found Start page explicitly: '{start_page.title}'")
                        wiki_page_titles.insert(0, start_page.title)
                        return True
            except Exception as e2:
                logger.warning(f"Could not find Start page for project {project_id}: {e2}")
        
        return False
    
    def _process_wiki_page(
        self,
        page_title: str,
        project_id: str,
        incremental: bool,
        last_sync,
        result: Dict[str, Any],
        db: Session
    ) -> None:
        """Xử lý một wiki page"""
        try:
            savepoint = db.begin_nested()
            try:
                # Rate limiting: độ trễ trước khi gọi API
                time.sleep(REDMINE_API_DELAY)
                
                # Lấy full page với tất cả dữ liệu
                full_page = self.redmine.wiki_page.get(page_title, project_id=project_id)
                
                # Kiểm tra xem có nên bỏ qua page này không (incremental sync)
                if self._should_skip_wiki_page(full_page, incremental, last_sync, page_title):
                    savepoint.commit()
                    return
                
                self.wiki_sync_handler.sync_wiki_page(full_page, project_id, db)
                savepoint.commit()
                result['processed'] += 1
                if result['processed'] % 10 == 0:
                    logger.info(f"Processed {result['processed']} wiki pages")
            except Exception as e:
                savepoint.rollback()
                logger.error(f"Failed to sync wiki page {page_title}: {e}", exc_info=True)
                result['failed'] += 1
                result['errors'].append(f"Wiki page {page_title}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error processing wiki page {page_title}: {e}", exc_info=True)
            result['failed'] += 1
            result['errors'].append(f"Wiki page {page_title}: {str(e)}")
            try:
                db.rollback()
            except:
                pass
    
    def _should_skip_wiki_page(self, full_page, incremental: bool, last_sync, page_title: str) -> bool:
        """Kiểm tra xem wiki page có nên bỏ qua trong incremental sync không.
        
        Hàm này kiểm tra xem wiki page có được cập nhật sau lần sync cuối không.
        Nếu incremental=True và page không được cập nhật, sẽ bỏ qua để tối ưu
        hiệu suất.
        
        Args:
            full_page: Wiki page object từ Redmine API
            incremental: Có sử dụng incremental sync không (bool)
            last_sync: Tuple chứa thời gian sync cuối (từ database query)
            page_title: Tên của wiki page (string, để logging)
        
        Returns:
            bool: True nếu nên bỏ qua page (không cập nhật), False nếu nên sync
        
        Note:
            - Chỉ kiểm tra nếu incremental=True và last_sync có giá trị
            - So sánh updated_on của page với last_sync[0]
        """
        if not incremental or not last_sync:
            return False
        
        if hasattr(full_page, 'updated_on') and full_page.updated_on:
            if full_page.updated_on < last_sync[0]:
                logger.info(f"Skipping unchanged wiki page: {page_title}")
                return True
        
        return False
    
    def _build_issue_content(self, issue) -> str:
        """Xây dựng nội dung có thể tìm kiếm từ issue (wrapper method để tương thích ngược).
        
        Args:
            issue: Redmine issue object
        
        Returns:
            str: Nội dung text đã được format từ issue
        """
        return self.content_builder.build_issue_content(issue)
    
    def _build_wiki_content(self, wiki_page) -> str:
        """Xây dựng nội dung có thể tìm kiếm từ wiki page (wrapper method để tương thích ngược).
        
        Args:
            wiki_page: Redmine wiki page object
        
        Returns:
            str: Nội dung text đã được format từ wiki page
        """
        return self.content_builder.build_wiki_content(wiki_page)

