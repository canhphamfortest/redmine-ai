"""Handler đồng bộ issue cho Redmine.

Module này cung cấp IssueSyncHandler class để đồng bộ Redmine issues:
- Issue synchronization: Đồng bộ issue data từ Redmine API
- Content hashing: Phát hiện thay đổi bằng SHA1 hash
- Chunk management: Tạo và cập nhật chunks (embedding được tạo bởi job riêng)
- Source management: Quản lý Source records trong database

Xử lý workflow từ fetch issue data đến tạo chunks, còn việc tạo embedding
được thực hiện bởi job embedding riêng.
"""
import logging
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Source, Chunk, Embedding, SourceRedmineIssue
from app.services.chunker import chunker
from app.config import settings
from app.services.redmine.utils import safe_attr, sanitize_string
from app.services.redmine.content_builder import ContentBuilder
from app.services.redmine.attachment_handler import AttachmentHandler

logger = logging.getLogger(__name__)


class IssueSyncHandler:
    """Xử lý đồng bộ các Redmine issues với database và vector store.
    
    Class này xử lý toàn bộ quy trình sync một Redmine issue:
    - Tạo/update source record
    - Đồng bộ metadata
    - Tạo chunks và embeddings
    - Xử lý content changes và incremental updates
    
    Attributes:
        content_builder: ContentBuilder instance để build issue content
        attachment_handler: AttachmentHandler instance để xử lý attachments
    """
    
    def __init__(self, content_builder: ContentBuilder, attachment_handler: AttachmentHandler):
        """Khởi tạo IssueSyncHandler.
        
        Args:
            content_builder: ContentBuilder instance để build issue content
            attachment_handler: AttachmentHandler instance để xử lý attachments
        """
        self.content_builder = content_builder
        self.attachment_handler = attachment_handler
    
    def sync_issue(self, issue, project_id: str, db: Session) -> Optional[Source]:
        """Đồng bộ một Redmine issue vào database và vector store.
        
        Quy trình sync:
        1. Build issue content và tính hash
        2. Lấy hoặc tạo source record
        3. Đồng bộ Redmine issue metadata
        4. Kiểm tra chunks và embeddings hiện có
        5. Quyết định có cần tạo lại chunks/embeddings không
        6. Tạo lại nếu cần (source mới, content thay đổi, hoặc thiếu chunks/embeddings)
        
        Args:
            issue: Redmine issue object từ redminelib
            project_id: Redmine project identifier (string)
            db: Database session
        
        Returns:
            Source | None: Source object đã được sync, None nếu có lỗi
        
        Note:
            - Chunks và embeddings chỉ được tạo lại khi cần thiết
            - Content hash được sử dụng để phát hiện thay đổi
            - Metadata luôn được cập nhật mỗi lần sync
        """
        # Xây dựng nội dung issue và hash
        content = self.content_builder.build_issue_content(issue)
        content_hash = hashlib.sha1(content.encode()).hexdigest()
        
        # Bước 1: Lấy hoặc tạo source
        source, is_new_source, content_changed = self._get_or_create_source(
            issue, project_id, content_hash, db
        )
        
        # Bước 2: Đồng bộ metadata Redmine issue
        self._sync_redmine_issue_metadata(issue, source, db)
        
        # Bước 3: Kiểm tra chunks hiện có
        existing_chunks = db.query(Chunk).filter(Chunk.source_id == source.id).all()
        has_chunks = self._has_chunks(existing_chunks)
        
        # Bước 4: Quyết định xem có cần tạo lại chunks không
        needs_recreate = is_new_source or content_changed or not has_chunks
        
        # Bước 5: Xử lý trường hợp không cần tạo lại
        if not needs_recreate:
            needs_recreate = self._handle_no_recreation_needed(
                existing_chunks, source, issue.id, db
            )
        
        # Bước 6: Tạo lại chunks nếu cần (embedding được tạo bởi job riêng)
        if needs_recreate:
            self._recreate_chunks(
                issue, source, existing_chunks, content_hash, is_new_source, content_changed, db
            )
        
        return source
    
    def _get_or_create_source(
        self,
        issue,
        project_id: str,
        content_hash: str,
        db: Session
    ) -> Tuple[Source, bool, bool]:
        """Lấy source hiện có hoặc tạo source mới cho issue.
        
        Hàm này kiểm tra xem source đã tồn tại chưa dựa trên external_id.
        Nếu chưa có, sẽ tạo mới. Nếu có, sẽ kiểm tra xem content có thay đổi không.
        
        Args:
            issue: Redmine issue object
            project_id: Redmine project identifier (string)
            content_hash: SHA1 hash của issue content (string)
            db: Database session
        
        Returns:
            Tuple[Source, bool, bool]: Tuple chứa:
                - source: Source object (mới hoặc đã tồn tại)
                - is_new_source: True nếu source mới được tạo, False nếu đã tồn tại
                - content_changed: True nếu content hash khác với hash cũ, False nếu không
        
        Note:
            - External ID format: "redmine_issue_{issue.id}"
            - Content changed được xác định bằng cách so sánh content_hash với sha1_content
        """
        external_id = f"redmine_issue_{issue.id}"
        source = db.query(Source).filter(
            Source.source_type == 'redmine_issue',
            Source.external_id == external_id
        ).first()
        
        if not source:
            new_source = self._create_new_source(issue, project_id, external_id, content_hash, db)
            return new_source, True, False
        
        updated_source = self._update_existing_source(source, issue, project_id, content_hash)
        content_changed = self._check_content_changed(source, content_hash, issue.id)
        return updated_source, False, content_changed
    
    def _create_new_source(
        self,
        issue,
        project_id: str,
        external_id: str,
        content_hash: str,
        db: Session
    ) -> Source:
        """Tạo source record mới cho Redmine issue.
        
        Hàm này tạo Source object mới với đầy đủ thông tin từ issue.
        Source được tạo với sync_status='success' và last_sync_at=now.
        
        Args:
            issue: Redmine issue object
            project_id: Redmine project identifier (string)
            external_id: External ID format "redmine_issue_{issue.id}" (string)
            content_hash: SHA1 hash của issue content (string)
            db: Database session
        
        Returns:
            Source: Source object mới đã được add vào database
        
        Note:
            - External URL được tạo từ settings.redmine_url
            - Project key được lấy từ issue.project nếu có, fallback về project_id
            - Language mặc định là 'en'
        """
        project_identifier = None
        project_id_int = None
        if hasattr(issue, 'project'):
            project_identifier = (
                safe_attr(issue.project, 'identifier')
                or safe_attr(issue.project, 'name')
                or safe_attr(issue.project, 'id')
            )
            project_id_int = safe_attr(issue.project, 'id')
        
        source = Source(
            source_type='redmine_issue',
            external_id=external_id,
            external_url=f"{settings.redmine_url}/issues/{issue.id}",
            project_key=sanitize_string(project_identifier or project_id),
            project_id=project_id_int,
            language='en',
            sha1_content=content_hash,
            sync_status='success',
            last_sync_at=datetime.now()
        )
        db.add(source)
        db.flush()
        logger.info(f"Created new source for issue {issue.id}")
        return source
    
    def _update_existing_source(
        self,
        source: Source,
        issue,
        project_id: str,
        content_hash: str
    ) -> Source:
        """Cập nhật source hiện có với content hash và project info mới.
        
        Hàm này cập nhật source với content_hash mới và bổ sung project_id
        nếu thiếu. Không commit database, chỉ update object.
        
        Args:
            source: Source object cần cập nhật
            issue: Redmine issue object
            project_id: Redmine project identifier (string)
            content_hash: SHA1 hash của issue content mới (string)
        
        Returns:
            Source: Source object đã được cập nhật (same object)
        
        Note:
            - Chỉ cập nhật project_id nếu source.project_id chưa có
            - Chỉ cập nhật project_key nếu source.project_key chưa có
            - Content hash luôn được cập nhật
        """
        # Cập nhật project_id nếu thiếu
        if not source.project_id and hasattr(issue, 'project'):
            project_id_int = safe_attr(issue.project, 'id')
            if project_id_int:
                source.project_id = project_id_int
        if not source.project_key:
            source.project_key = sanitize_string(project_id)
        
        source.sha1_content = content_hash
        return source
    
    def _check_content_changed(self, source: Source, content_hash: str, issue_id: int) -> bool:
        """Kiểm tra xem issue content có thay đổi không bằng cách so sánh hash.
        
        Hàm này so sánh content_hash mới với sha1_content hiện tại của source.
        Nếu khác nhau, có nghĩa là content đã thay đổi và cần tạo lại chunks.
        
        Args:
            source: Source object chứa sha1_content cũ
            content_hash: SHA1 hash của content mới (string)
            issue_id: ID của issue (int, để logging)
        
        Returns:
            bool: True nếu content đã thay đổi, False nếu không
        
        Note:
            - So sánh trực tiếp hai hash strings
            - Log hash đầu 8 ký tự để debug
            - Hash khác nhau có nghĩa là content (description, comments, attachments) đã thay đổi
        """
        previous_hash = source.sha1_content
        if previous_hash != content_hash:
            prev_hash_display = previous_hash[:8] if previous_hash else "None"
            logger.info(f"Issue {issue_id} content changed (hash: {prev_hash_display} -> {content_hash[:8]})")
            return True
        else:
            logger.debug(f"Issue {issue_id} content unchanged")
            return False
    
    def _sync_redmine_issue_metadata(self, issue, source: Source, db: Session) -> None:
        """Đồng bộ metadata của Redmine issue vào bảng SourceRedmineIssue.
        
        Hàm này thu thập tất cả metadata từ issue (tracker, status, priority,
        author, assignee, dates, etc.) và lưu vào SourceRedmineIssue. Nếu
        record chưa tồn tại, sẽ tạo mới. Nếu đã có, sẽ cập nhật.
        
        Args:
            issue: Redmine issue object
            source: Source object liên kết với issue
            db: Database session
        
        Note:
            - Metadata được sync mỗi lần sync issue
            - Bao gồm: tracker, status, priority, author, assignee, category,
              fixed_version, dates, hours, parent_issue_id
            - Sử dụng _create_redmine_issue_metadata() hoặc _update_redmine_issue_metadata()
        """
        redmine_issue = db.query(SourceRedmineIssue).filter(
            SourceRedmineIssue.source_id == source.id
        ).first()
        
        # Thu thập metadata issue
        tracker = issue.tracker if hasattr(issue, 'tracker') else None
        status = issue.status if hasattr(issue, 'status') else None
        priority = issue.priority if hasattr(issue, 'priority') else None
        author = issue.author if hasattr(issue, 'author') else None
        assignee = issue.assigned_to if hasattr(issue, 'assigned_to') else None
        category = issue.category if hasattr(issue, 'category') else None
        fixed_version = issue.fixed_version if hasattr(issue, 'fixed_version') else None
        
        if not redmine_issue:
            self._create_redmine_issue_metadata(
                source, issue, tracker, status, priority, author, assignee, category, fixed_version, db
            )
        else:
            self._update_redmine_issue_metadata(
                redmine_issue, issue, tracker, status, priority, author, assignee, category, fixed_version
            )
    
    def _create_redmine_issue_metadata(
        self,
        source: Source,
        issue,
        tracker,
        status,
        priority,
        author,
        assignee,
        category,
        fixed_version,
        db: Session
    ) -> None:
        """Tạo SourceRedmineIssue record mới với metadata từ issue.
        
        Hàm này tạo SourceRedmineIssue object mới với tất cả metadata được
        extract từ Redmine issue object. Sử dụng safe_attr() để tránh lỗi
        khi attributes không tồn tại.
        
        Args:
            source: Source object liên kết
            issue: Redmine issue object
            tracker: Tracker object từ issue (có thể None)
            status: Status object từ issue (có thể None)
            priority: Priority object từ issue (có thể None)
            author: Author object từ issue (có thể None)
            assignee: AssignedTo object từ issue (có thể None)
            category: Category object từ issue (có thể None)
            fixed_version: FixedVersion object từ issue (có thể None)
            db: Database session
        
        Note:
            - Tất cả metadata được extract an toàn bằng safe_attr()
            - Parent issue ID được lấy từ issue.parent nếu có
            - Record được add vào database nhưng chưa commit
        """
        logger.info(f"Creating source_redmine_issue for issue {issue.id}")
        redmine_issue = SourceRedmineIssue(
            source_id=source.id,
            tracker_id=safe_attr(tracker, 'id'),
            tracker_name=sanitize_string(safe_attr(tracker, 'name')),
            status_id=safe_attr(status, 'id'),
            status_name=sanitize_string(safe_attr(status, 'name')),
            status_is_closed=safe_attr(status, 'is_closed') if status else None,
            priority_id=safe_attr(priority, 'id'),
            priority_name=sanitize_string(safe_attr(priority, 'name')),
            category_id=safe_attr(category, 'id'),
            category_name=sanitize_string(safe_attr(category, 'name')),
            author_id=safe_attr(author, 'id'),
            author_name=sanitize_string(safe_attr(author, 'name')),
            assigned_to_id=safe_attr(assignee, 'id'),
            assigned_to_name=sanitize_string(safe_attr(assignee, 'name')),
            fixed_version_id=safe_attr(fixed_version, 'id'),
            fixed_version_name=sanitize_string(safe_attr(fixed_version, 'name')),
            parent_issue_id=safe_attr(issue.parent, 'id') if hasattr(issue, 'parent') and issue.parent else None,
            estimated_hours=safe_attr(issue, 'estimated_hours'),
            done_ratio=safe_attr(issue, 'done_ratio'),
            start_date=safe_attr(issue, 'start_date'),
            due_date=safe_attr(issue, 'due_date'),
            closed_on=safe_attr(issue, 'closed_on'),
        )
        db.add(redmine_issue)
    
    def _update_redmine_issue_metadata(
        self,
        redmine_issue: SourceRedmineIssue,
        issue,
        tracker,
        status,
        priority,
        author,
        assignee,
        category,
        fixed_version
    ) -> None:
        """Cập nhật SourceRedmineIssue hiện có với metadata mới từ issue.
        
        Hàm này cập nhật tất cả các fields trong SourceRedmineIssue với giá trị
        mới từ issue. Kiểm tra và log các thay đổi quan trọng (status, assignee,
        priority, tracker) để tracking.
        
        Args:
            redmine_issue: SourceRedmineIssue object cần cập nhật
            issue: Redmine issue object chứa metadata mới
            tracker: Tracker object từ issue (có thể None)
            status: Status object từ issue (có thể None)
            priority: Priority object từ issue (có thể None)
            author: Author object từ issue (có thể None)
            assignee: AssignedTo object từ issue (có thể None)
            category: Category object từ issue (có thể None)
            fixed_version: FixedVersion object từ issue (có thể None)
        
        Note:
            - Luôn cập nhật tất cả fields để đảm bảo metadata là hiện tại
            - Log thay đổi cho các fields quan trọng (status, assignee, priority, tracker)
            - Sử dụng safe_attr() để extract values an toàn
        """
        # Lấy giá trị hiện tại để so sánh
        new_status_id = safe_attr(status, 'id')
        new_assigned_to_id = safe_attr(assignee, 'id')
        new_priority_id = safe_attr(priority, 'id')
        new_tracker_id = safe_attr(tracker, 'id')
        
        # Kiểm tra xem các trường metadata quan trọng có thay đổi không (để logging)
        metadata_changed = (
            (redmine_issue.status_id or None) != (new_status_id or None) or
            (redmine_issue.assigned_to_id or None) != (new_assigned_to_id or None) or
            (redmine_issue.priority_id or None) != (new_priority_id or None) or
            (redmine_issue.tracker_id or None) != (new_tracker_id or None)
        )
        
        if metadata_changed:
            logger.info(f"Metadata changed for issue {issue.id}: status={new_status_id}, assignee={new_assigned_to_id}, priority={new_priority_id}")
        
        # Luôn cập nhật tất cả các trường để đảm bảo metadata là hiện tại
        redmine_issue.tracker_id = new_tracker_id
        redmine_issue.tracker_name = sanitize_string(safe_attr(tracker, 'name'))
        redmine_issue.status_id = new_status_id
        redmine_issue.status_name = sanitize_string(safe_attr(status, 'name'))
        redmine_issue.status_is_closed = safe_attr(status, 'is_closed') if status else None
        redmine_issue.priority_id = new_priority_id
        redmine_issue.priority_name = sanitize_string(safe_attr(priority, 'name'))
        redmine_issue.category_id = safe_attr(category, 'id')
        redmine_issue.category_name = sanitize_string(safe_attr(category, 'name'))
        redmine_issue.author_id = safe_attr(author, 'id')
        redmine_issue.author_name = sanitize_string(safe_attr(author, 'name'))
        redmine_issue.assigned_to_id = new_assigned_to_id
        redmine_issue.assigned_to_name = sanitize_string(safe_attr(assignee, 'name'))
        redmine_issue.fixed_version_id = safe_attr(fixed_version, 'id')
        redmine_issue.fixed_version_name = sanitize_string(safe_attr(fixed_version, 'name'))
        redmine_issue.parent_issue_id = safe_attr(issue.parent, 'id') if hasattr(issue, 'parent') and issue.parent else None
        redmine_issue.estimated_hours = safe_attr(issue, 'estimated_hours')
        redmine_issue.done_ratio = safe_attr(issue, 'done_ratio')
        redmine_issue.start_date = safe_attr(issue, 'start_date')
        redmine_issue.due_date = safe_attr(issue, 'due_date')
        redmine_issue.closed_on = safe_attr(issue, 'closed_on')
    
    def _has_chunks(self, existing_chunks: List[Chunk]) -> bool:
        """Kiểm tra xem source đã có chunks hay chưa.
        
        Args:
            existing_chunks: Danh sách chunks hiện có cho source (List[Chunk])
        
        Returns:
            bool: True nếu có ít nhất một chunk, False nếu không
        """
        return len(existing_chunks) > 0
    
    def _handle_no_recreation_needed(
        self,
        existing_chunks: List[Chunk],
        source: Source,
        issue_id: int,
        db: Session
    ) -> bool:
        """Xử lý trường hợp không cần tạo lại chunks - sửa các vấn đề nhỏ.
        
        Hàm này kiểm tra và sửa các vấn đề nhỏ mà không cần recreate toàn bộ:
        - Kiểm tra có metadata chunk không (nếu thiếu, cần recreate)
        - Sửa ordinals nếu không tuần tự
        - Cập nhật quality_score nếu thiếu
        
        Args:
            existing_chunks: Danh sách chunks hiện có (List[Chunk])
            source: Source object
            issue_id: ID của issue (int, để logging)
            db: Database session
        
        Returns:
            bool: True nếu vẫn cần recreate sau khi kiểm tra, False nếu không
        
        Note:
            - Nếu thiếu metadata chunk, trả về True (cần recreate)
            - Ordinals được sửa nếu không tuần tự (0, 1, 2, ...)
            - Quality scores được tính lại nếu thiếu
            - Nếu có vấn đề lớn, trả về True để trigger recreate
        """
        # Kiểm tra xem metadata chunk có tồn tại không
        has_metadata_chunk = any(c.chunk_type == 'issue_metadata' for c in existing_chunks)
        if not has_metadata_chunk:
            logger.info(f"Issue {issue_id} missing metadata chunk, will recreate")
            return True
        
        needs_update = False
        updated_count = 0
        
        # Sửa ordinals nếu cần
        if len(existing_chunks) > 1:
            ordinals = [c.ordinal for c in existing_chunks]
            if all(o == 0 for o in ordinals) or sorted(ordinals) != list(range(len(existing_chunks))):
                for i, chunk in enumerate(sorted(existing_chunks, key=lambda x: x.created_at)):
                    if chunk.ordinal != i:
                        chunk.ordinal = i
                        needs_update = True
                        updated_count += 1
        
        # Đảm bảo chunk chưa có embedding được đánh dấu pending để job embedding xử lý
        for chunk in existing_chunks:
            embedding = db.query(Embedding).filter(Embedding.chunk_id == chunk.id).first()
            if not embedding and chunk.status != 'failed':
                chunk.status = 'pending'
                needs_update = True
                updated_count += 1
        
        if needs_update:
            logger.info(f"Issue {issue_id} updated: fixed {updated_count} chunks")
        else:
            logger.debug(f"Issue {issue_id} unchanged, skipping")
        
        # Cập nhật sync status nhưng không cập nhật last_sync_at nếu content không thay đổi
        source.sync_status = 'success'
        source.error_message = None
        source.updated_at = datetime.now()
        db.flush()
        
        return False
    
    def _recreate_chunks(
        self,
        issue,
        source: Source,
        existing_chunks: List[Chunk],
        content_hash: str,
        is_new_source: bool,
        content_changed: bool,
        db: Session
    ) -> None:
        """Tạo lại chunks cho issue từ đầu.
        
        Hàm này thực hiện quy trình recreate hoàn toàn:
        1. Xóa tất cả chunks và embeddings cũ
        2. Build issue data dictionary
        3. Chunk issue thành các chunks
        4. Lưu chunks vào database (embedding sẽ được tạo bởi job riêng)
        5. Cập nhật source sync status
        
        Args:
            issue: Redmine issue object
            source: Source object
            existing_chunks: Danh sách chunks cũ cần xóa (List[Chunk])
            content_hash: SHA1 hash của content mới (string)
            is_new_source: True nếu source mới được tạo, False nếu đã tồn tại
            content_changed: True nếu content đã thay đổi, False nếu không
            db: Database session
        
        Note:
            - Chunks và embeddings cũ được xóa trước khi tạo mới
            - Embeddings được xóa trước chunks (do foreign key constraint)
            - Source hash được cập nhật với content_hash mới
            - last_sync_at chỉ được cập nhật nếu content_changed=True
        """
        logger.info(f"{'Creating' if is_new_source else 'Updating'} chunks for issue {issue.id}")
        
        # Xóa chunks/embeddings cũ nếu có
        if existing_chunks:
            for chunk in existing_chunks:
                # Xóa embedding trước (do foreign key)
                db.query(Embedding).filter(Embedding.chunk_id == chunk.id).delete()
                # Xóa chunk
                db.delete(chunk)
            db.flush()
            logger.info(f"Deleted {len(existing_chunks)} old chunks and embeddings for issue {issue.id}")
        
        # Cập nhật source hash
        source.sha1_content = content_hash
        
        # Tạo chunks - xây dựng dữ liệu issue
        issue_data = self._build_issue_data(issue)
        chunks_data = chunker.chunk_redmine_issue(issue_data)
        
        # Lưu chunks (embedding được tạo bởi job embedding)
        created_chunks = self._save_chunks(source, chunks_data, issue.id, db)
        
        # Cập nhật sync status và last_sync_at sau khi sync thành công
        source.sync_status = 'success'
        source.error_message = None
        if content_changed:
            source.last_sync_at = datetime.now()
        source.updated_at = datetime.now()
        
        logger.info(
            f"Issue {issue.id} synced: {created_chunks} chunks queued for embedding"
        )
    
    def _save_chunks(
        self,
        source: Source,
        chunks_data: List[Dict[str, Any]],
        issue_id: int,
        db: Session
    ) -> int:
        """Lưu chunks vào database, đánh dấu status pending để job embedding xử lý.
        
        Args:
            source: Source object liên kết
            chunks_data: Danh sách chunk data dictionaries (List[Dict])
            issue_id: ID của issue (int, để logging)
            db: Database session
        
        Returns:
            int: Số lượng chunks đã lưu
        """
        created_chunks = 0
        
        for chunk_data in chunks_data:
            chunk = Chunk(
                source_id=source.id,
                status="pending",
                **chunk_data
            )
            db.add(chunk)
            created_chunks += 1
        
        db.flush()
        return created_chunks
    
    def _build_issue_data(self, issue) -> dict:
        """Xây dựng dictionary dữ liệu issue để chunking.
        
        Hàm này extract tất cả thông tin từ Redmine issue object và format
        thành dictionary structure mà chunk_redmine_issue() có thể xử lý.
        Bao gồm metadata, description, journals, attachments, và các thông tin khác.
        
        Args:
            issue: Redmine issue object từ redminelib
        
        Returns:
            dict: Dictionary chứa tất cả dữ liệu issue:
                - id, title
                - tracker, status, priority (dict với id, name)
                - author, assignee (dict với id, name)
                - project (dict với id, name, identifier)
                - category, fixed_version
                - dates (created_on, updated_on, start_date, due_date, closed_on)
                - hours (estimated_hours, spent_hours)
                - done_ratio
                - description
                - journals (comments)
                - attachments (với content nếu là text file)
                - children, relations, watchers
                - custom_fields
        
        Note:
            - Sử dụng safe_attr() để extract values an toàn
            - Attachments được process bằng attachment_handler
            - Dates được convert sang ISO format nếu có
            - Journals chỉ lấy những có notes
        """
        tracker = issue.tracker if hasattr(issue, 'tracker') else None
        status = issue.status if hasattr(issue, 'status') else None
        priority = issue.priority if hasattr(issue, 'priority') else None
        author = issue.author if hasattr(issue, 'author') else None
        assignee = issue.assigned_to if hasattr(issue, 'assigned_to') else None
        project = issue.project if hasattr(issue, 'project') else None
        category = issue.category if hasattr(issue, 'category') else None
        fixed_version = issue.fixed_version if hasattr(issue, 'fixed_version') else None
        
        issue_data = {
            'id': issue.id if hasattr(issue, 'id') else None,
            'title': sanitize_string(issue.subject if hasattr(issue, 'subject') else ''),
            'tracker': {
                'id': safe_attr(tracker, 'id'),
                'name': sanitize_string(safe_attr(tracker, 'name'))
            },
            'status': {
                'id': safe_attr(status, 'id'),
                'name': sanitize_string(safe_attr(status, 'name'))
            },
            'priority': {
                'id': safe_attr(priority, 'id'),
                'name': sanitize_string(safe_attr(priority, 'name'))
            },
            'description': sanitize_string(issue.description if hasattr(issue, 'description') else ''),
            'author': {
                'id': safe_attr(author, 'id'),
                'name': sanitize_string(safe_attr(author, 'name'))
            },
            'assignee': {
                'id': safe_attr(assignee, 'id'),
                'name': sanitize_string(safe_attr(assignee, 'name'))
            },
            'project': {
                'id': safe_attr(project, 'id'),
                'name': sanitize_string(safe_attr(project, 'name')),
                'identifier': sanitize_string(safe_attr(project, 'identifier'))
            },
            'category': {
                'id': safe_attr(category, 'id'),
                'name': sanitize_string(safe_attr(category, 'name'))
            } if category else None,
            'fixed_version': {
                'id': safe_attr(fixed_version, 'id'),
                'name': sanitize_string(safe_attr(fixed_version, 'name'))
            } if fixed_version else None,
            'created_on': issue.created_on.isoformat() if hasattr(issue, 'created_on') and issue.created_on else None,
            'updated_on': issue.updated_on.isoformat() if hasattr(issue, 'updated_on') and issue.updated_on else None,
            'start_date': issue.start_date.isoformat() if hasattr(issue, 'start_date') and issue.start_date else None,
            'due_date': issue.due_date.isoformat() if hasattr(issue, 'due_date') and issue.due_date else None,
            'done_ratio': issue.done_ratio if hasattr(issue, 'done_ratio') else None,
            'estimated_hours': issue.estimated_hours if hasattr(issue, 'estimated_hours') else None,
            'spent_hours': issue.spent_hours if hasattr(issue, 'spent_hours') else None,
            'journals': [],
            'attachments': [],
            'relations': [],
            'children': [],
            'watchers': [],
            'custom_fields': []
        }
        
        # Thêm journals (comments)
        if hasattr(issue, 'journals'):
            for journal in issue.journals:
                if hasattr(journal, 'notes') and journal.notes:
                    issue_data['journals'].append({
                        'id': journal.id,
                        'notes': sanitize_string(journal.notes),
                        'user': {
                            'id': journal.user.id if hasattr(journal, 'user') else None,
                            'name': sanitize_string(journal.user.name if hasattr(journal, 'user') and hasattr(journal.user, 'name') else None)
                        },
                        'created_on': journal.created_on if hasattr(journal, 'created_on') else None,
                        'private_notes': getattr(journal, 'private_notes', False)
                    })
        
        # Thêm attachments sử dụng attachment handler
        issue_data['attachments'] = self.attachment_handler.process_attachments(issue)
        
        # Thêm relations (related issues)
        if hasattr(issue, 'relations'):
            for relation in issue.relations:
                issue_data['relations'].append({
                    'id': safe_attr(relation, 'id'),
                    'issue_id': safe_attr(relation, 'issue_id'),
                    'issue_to_id': safe_attr(relation, 'issue_to_id'),
                    'relation_type': safe_attr(relation, 'relation_type')
                })
        
        # Thêm children (sub-issues)
        if hasattr(issue, 'children'):
            for child in issue.children:
                issue_data['children'].append({
                    'id': safe_attr(child, 'id'),
                    'subject': sanitize_string(safe_attr(child, 'subject')),
                    'tracker': {
                        'id': safe_attr(child.tracker, 'id') if hasattr(child, 'tracker') else None,
                        'name': sanitize_string(safe_attr(child.tracker, 'name') if hasattr(child, 'tracker') else None)
                    },
                    'status': {
                        'id': safe_attr(child.status, 'id') if hasattr(child, 'status') else None,
                        'name': sanitize_string(safe_attr(child.status, 'name') if hasattr(child, 'status') else None)
                    }
                })
        
        # Thêm watchers
        if hasattr(issue, 'watchers'):
            for watcher in issue.watchers:
                issue_data['watchers'].append({
                    'id': safe_attr(watcher, 'id'),
                    'name': sanitize_string(safe_attr(watcher, 'name'))
                })
        
        # Thêm custom fields
        if hasattr(issue, 'custom_fields'):
            for custom_field in issue.custom_fields:
                # Custom field value có thể là string hoặc list
                value = safe_attr(custom_field, 'value')
                if isinstance(value, str):
                    value = sanitize_string(value)
                elif isinstance(value, list):
                    value = [sanitize_string(v) if isinstance(v, str) else v for v in value]
                
                issue_data['custom_fields'].append({
                    'id': safe_attr(custom_field, 'id'),
                    'name': sanitize_string(safe_attr(custom_field, 'name')),
                    'value': value,
                    'multiple': getattr(custom_field, 'multiple', False)
                })
        
        return issue_data

