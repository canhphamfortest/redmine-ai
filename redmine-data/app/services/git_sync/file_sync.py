"""Logic đồng bộ file.

Module này cung cấp FileSyncHandler class để đồng bộ individual files:
- File synchronization: Đồng bộ một file từ Git repository
- Content hashing: Phát hiện thay đổi bằng SHA1 hash
- Chunking: Chia file thành chunks (text hoặc code)
- Embedding: Tạo embeddings cho chunks

Tự động phát hiện file type và sử dụng chunking strategy phù hợp.
"""
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from git import Repo
from sqlalchemy.orm import Session

from app.models import Source, Chunk, Embedding, SourceGitFile
from app.services.chunker import chunker
from app.services.embedder import embedder
from app.services.git_sync.detectors import detect_file_type, detect_language

logger = logging.getLogger(__name__)


class FileSyncHandler:
    """Xử lý đồng bộ các file riêng lẻ từ Git repository vào database.
    
    Class này xử lý việc sync một file từ Git repository:
    - Tạo/update source record
    - Tạo SourceGitFile metadata
    - Chunk file (code hoặc text)
    - Tạo embeddings
    - Lưu vào database
    
    Note:
        - Tự động phát hiện file type (code vs text)
        - Sử dụng code chunker cho code files, text chunker cho text files
    """
    
    def sync_file(
        self,
        file_path: Path,
        repo: Repo,
        repo_url: str,
        db: Session
    ):
        """Đồng bộ một file từ Git repository vào database và vector store.
        
        Quy trình:
        1. Lấy thông tin commit cho file
        2. Tạo external_id từ file path
        3. Lấy hoặc tạo source record
        4. Đọc file content và tính hash
        5. Kiểm tra content có thay đổi không
        6. Nếu thay đổi hoặc mới, xóa chunks cũ và tạo mới
        7. Chunk file (code hoặc text tùy loại)
        8. Tạo embeddings và lưu vào database
        
        Args:
            file_path: Đường dẫn tuyệt đối đến file (Path)
            repo: GitPython Repo object
            repo_url: URL của repository (string)
            db: Database session
        
        Note:
            - External ID được tạo từ MD5 hash của relative path
            - Content hash được so sánh để phát hiện thay đổi
            - Nếu content không thay đổi và có chunks, sẽ skip
            - Code files sử dụng chunk_code(), text files sử dụng chunk()
            - Language được detect tự động từ file extension
            - Commit info được lấy từ commit mới nhất cho file
        """
        
        # Lấy thông tin file
        relative_path = file_path.relative_to(repo.working_dir)
        
        # Lấy thông tin commit cho file này
        commits = list(repo.iter_commits(paths=str(relative_path), max_count=1))
        if not commits:
            logger.warning(f"No commits found for {relative_path}")
            return
        
        commit = commits[0]
        
        # Xây dựng external_id
        external_id = f"git_file_{hashlib.md5(str(relative_path).encode()).hexdigest()}"
        
        # Kiểm tra source có tồn tại không
        source = db.query(Source).filter(
            Source.source_type == 'git_file',
            Source.external_id == external_id
        ).first()
        
        # Đọc nội dung file
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return
        
        content_hash = hashlib.sha1(content.encode()).hexdigest()
        
        is_new = False
        
        if not source:
            # Tạo source mới
            source = Source(
                source_type='git_file',
                external_id=external_id,
                external_url=f"{repo_url}/blob/{commit.hexsha}/{relative_path}",
                project_key=repo_url.split('/')[-1].replace('.git', ''),
                language='en'  # TODO: Auto-detect
            )
            db.add(source)
            db.flush()
            is_new = True
            
            # Tạo metadata riêng cho git
            git_file = SourceGitFile(
                source_id=source.id,
                repository_name=repo_url.split('/')[-1].replace('.git', ''),
                repository_url=repo_url,
                branch=repo.active_branch.name,
                commit_hash=commit.hexsha,
                commit_short_hash=commit.hexsha[:7],
                commit_author_name=commit.author.name,
                commit_author_email=commit.author.email,
                commit_date=datetime.fromtimestamp(commit.committed_date),
                commit_message=commit.message.strip(),
                file_extension=file_path.suffix.lstrip('.'),
                file_type=detect_file_type(file_path),
                file_size_bytes=file_path.stat().st_size,
                line_count=len(content.splitlines())
            )
            db.add(git_file)
        
        existing_chunks = db.query(Chunk).filter(Chunk.source_id == source.id).all()
        previous_hash = source.sha1_content
        
        # Kiểm tra nội dung có thay đổi không
        if previous_hash == content_hash and existing_chunks:
            logger.info(f"File {relative_path} unchanged, skipping")
            source.updated_at = datetime.now()
            return
        
        # Nội dung đã thay đổi hoặc file mới
        logger.info(f"{'Creating' if is_new else 'Updating'} file {relative_path}")
        
        # Xóa chunks/embeddings hiện có nếu có
        if existing_chunks:
            # Xóa chunks và embeddings cũ (chúng sẽ được tạo lại)
            old_chunks = existing_chunks
            for chunk in old_chunks:
                # Xóa embedding trước (do foreign key)
                db.query(Embedding).filter(Embedding.chunk_id == chunk.id).delete()
                # Xóa chunk
                db.delete(chunk)
            
            logger.info(f"Deleted {len(old_chunks)} old chunks and embeddings for file {relative_path}")
        
        source.sha1_content = content_hash
        
        # Tạo chunks
        language = detect_language(file_path)
        
        if language:
            # File code
            chunks_data = chunker.chunk_code(
                content,
                language=language,
                metadata={
                    'code_language': language,
                    'file_extension': file_path.suffix.lstrip('.')
                }
            )
        else:
            # File văn bản
            chunks_data = chunker.chunk(content)
        
        # Tạo embeddings
        texts = [c['text_content'] for c in chunks_data]
        embeddings = embedder.embed_batch(texts)
        
        # Lưu chunks và embeddings
        for chunk_data, embedding_vec in zip(chunks_data, embeddings):
            # Xác thực kích thước embedding
            if len(embedding_vec) != embedder.embedding_dim:
                logger.error(
                    f"File {relative_path}: Generated embedding has wrong dimension: "
                    f"{len(embedding_vec)} (expected {embedder.embedding_dim}). Skipping chunk."
                )
                continue
            
            chunk = Chunk(
                source_id=source.id,
                status="pending",
                **chunk_data
            )
            db.add(chunk)
            db.flush()
            
            # Tính điểm chất lượng
            quality_score = embedder.compute_quality_score(embedding_vec)
            
            embedding = Embedding(
                chunk_id=chunk.id,
                embedding=embedding_vec,
                model_name=embedder.model_name,
                quality_score=quality_score,
                status="active"
            )
            db.add(embedding)
            chunk.status = "processed"
        
        source.updated_at = datetime.now()
        logger.info(f"File {relative_path} synced: {len(chunks_data)} chunks")

