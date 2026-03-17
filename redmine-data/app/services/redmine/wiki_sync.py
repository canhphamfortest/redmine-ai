"""Handler đồng bộ wiki cho Redmine.

Module này cung cấp WikiSyncHandler class để đồng bộ Redmine wiki pages:
- Wiki synchronization: Đồng bộ wiki page data từ Redmine API
- Content hashing: Phát hiện thay đổi bằng SHA1 hash
- Chunk creation: Tạo chunks cho wiki content (embedding do job riêng xử lý)
- Source management: Quản lý Source records trong database

Xử lý workflow từ fetch wiki data đến tạo chunks, còn việc tạo embedding
được thực hiện bởi job embedding riêng.
"""
import logging
import hashlib
import time
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from redminelib import Redmine

from app.models import Source, Chunk, Embedding, SourceRedmineWiki
from app.services.chunker import chunker
from app.config import settings
from app.services.redmine.utils import safe_attr, sanitize_string
from app.services.redmine.content_builder import ContentBuilder

logger = logging.getLogger(__name__)

# Rate limiting: độ trễ giữa các lời gọi Redmine API (tính bằng giây)
REDMINE_API_DELAY = float(getattr(settings, 'redmine_api_delay', 0.2))


class WikiSyncHandler:
    """Xử lý đồng bộ các Redmine wiki pages với database và vector store.
    
    Class này xử lý toàn bộ quy trình sync một wiki page:
    - Tạo/update source record
    - Tạo SourceRedmineWiki metadata
    - Tạo chunks và embeddings
    - Xử lý content changes
    
    Attributes:
        redmine: Redmine client instance
        content_builder: ContentBuilder instance để build wiki content
    """
    
    def __init__(self, redmine: Redmine, content_builder: ContentBuilder):
        """Khởi tạo WikiSyncHandler.
        
        Args:
            redmine: Redmine client instance
            content_builder: ContentBuilder instance để build wiki content
        """
        self.redmine = redmine
        self.content_builder = content_builder
    
    def sync_wiki_page(self, wiki_page, project_id: str, db: Session) -> None:
        """Đồng bộ một Redmine wiki page vào database và vector store.
        
        Quy trình sync:
        1. Tạo external_id từ project_id và wiki title
        2. Lấy hoặc tạo source record
        3. Build wiki content và tính hash
        4. Kiểm tra content có thay đổi không
        5. Nếu không thay đổi và có chunks, skip
        6. Nếu thay đổi hoặc thiếu chunks, xóa cũ và tạo mới
        
        Args:
            wiki_page: Redmine wiki page object từ redminelib
            project_id: Redmine project identifier (string)
            db: Database session
        
        Note:
            - External ID format: "redmine_wiki_{project_id}_{wiki_page.title}"
            - Content hash được so sánh với sha1_content để phát hiện thay đổi
            - Nếu content không thay đổi và có chunks, sẽ skip để tối ưu
            - Chunks và embeddings cũ được xóa trước khi tạo mới
            - Rate limiting được áp dụng khi gọi Redmine API
        """
        
        # Xây dựng external_id
        external_id = f"redmine_wiki_{project_id}_{wiki_page.title}"
        
        # Kiểm tra xem source có tồn tại không
        source = db.query(Source).filter(
            Source.source_type == 'redmine_wiki',
            Source.external_id == external_id
        ).first()
        
        # Xây dựng wiki content
        content = self.content_builder.build_wiki_content(wiki_page)
        content_hash = hashlib.sha1(content.encode()).hexdigest()
        
        is_new = False
        
        if not source:
            # Tạo source mới
            # Rate limiting: độ trễ trước khi gọi API
            if project_id:
                time.sleep(REDMINE_API_DELAY)
            project = self.redmine.project.get(project_id) if project_id else None
            project_identifier = (
                safe_attr(project, 'identifier')
                or safe_attr(project, 'name')
                or project_id
            )
            
            source = Source(
                source_type='redmine_wiki',
                external_id=external_id,
                external_url=f"{settings.redmine_url}/projects/{project_id}/wiki/{sanitize_string(wiki_page.title)}",
                project_key=sanitize_string(project_identifier),
                language='en'
            )
            db.add(source)
            db.flush()
            is_new = True
            
            # Tạo metadata đặc thù cho Redmine
            author = wiki_page.author if hasattr(wiki_page, 'author') else None
            
            redmine_wiki = SourceRedmineWiki(
                source_id=source.id,
                wiki_version=safe_attr(wiki_page, 'version'),
                parent_page_title=sanitize_string(safe_attr(wiki_page, 'parent', {}).get('title') if hasattr(wiki_page, 'parent') else None),
                author_id=safe_attr(author, 'id'),
                author_name=sanitize_string(safe_attr(author, 'name')),
                comments=sanitize_string(safe_attr(wiki_page, 'comments')),
                redmine_project_id=safe_attr(project, 'id') if project else None,
                redmine_project_name=sanitize_string(safe_attr(project, 'name') if project else None)
            )
            db.add(redmine_wiki)
        
        # Thu thập các chunks hiện có cho source này
        existing_chunks = db.query(Chunk).filter(Chunk.source_id == source.id).all()
        previous_hash = source.sha1_content
        
        # Kiểm tra xem content có thay đổi không
        content_changed = previous_hash != content_hash
        if not content_changed and existing_chunks:
            # Content không thay đổi
            logger.info(f"Wiki page {wiki_page.title} unchanged, skipping")
            source.updated_at = datetime.now()
            return
        
        source.sha1_content = content_hash
        
        # Xóa các chunks/embeddings cũ nếu có
        if existing_chunks:
            old_chunks = existing_chunks
            for chunk in old_chunks:
                db.query(Embedding).filter(Embedding.chunk_id == chunk.id).delete()
                db.delete(chunk)
            db.flush()
            logger.info(f"Deleted {len(old_chunks)} old chunks and embeddings for wiki page {wiki_page.title}")
        
        # Tạo chunks
        # Trích xuất wiki metadata
        author = wiki_page.author if hasattr(wiki_page, 'author') else None
        # Rate limiting: độ trễ trước khi gọi API
        if project_id:
            time.sleep(REDMINE_API_DELAY)
        project = self.redmine.project.get(project_id) if project_id else None
        
        wiki_data = {
            'title': sanitize_string(wiki_page.title if hasattr(wiki_page, 'title') else ''),
            'text': sanitize_string(wiki_page.text if hasattr(wiki_page, 'text') else ''),
            'version': safe_attr(wiki_page, 'version'),
            'author': {
                'id': safe_attr(author, 'id'),
                'name': sanitize_string(safe_attr(author, 'name'))
            },
            'project': {
                'id': safe_attr(project, 'id'),
                'name': sanitize_string(safe_attr(project, 'name')),
                'identifier': sanitize_string(safe_attr(project, 'identifier'))
            },
            'comments': sanitize_string(safe_attr(wiki_page, 'comments')),
            'created_on': wiki_page.created_on.isoformat() if hasattr(wiki_page, 'created_on') and wiki_page.created_on else None,
            'updated_on': wiki_page.updated_on.isoformat() if hasattr(wiki_page, 'updated_on') and wiki_page.updated_on else None,
            'parent': {
                'title': sanitize_string(safe_attr(wiki_page.parent, 'title'))
            } if hasattr(wiki_page, 'parent') and wiki_page.parent else None
        }
        
        chunks_data = chunker.chunk_redmine_wiki(wiki_data)
        # Lưu chunks, đánh dấu pending để job embedding xử lý
        for chunk_data in chunks_data:
            chunk = Chunk(
                source_id=source.id,
                status="pending",
                **chunk_data
            )
            db.add(chunk)
        
        # Chỉ cập nhật last_sync_at khi content thực sự thay đổi
        if content_changed:
            source.last_sync_at = datetime.now()
        source.updated_at = datetime.now()
        logger.info(f"Wiki page {wiki_page.title} synced: {len(chunks_data)} chunks")

