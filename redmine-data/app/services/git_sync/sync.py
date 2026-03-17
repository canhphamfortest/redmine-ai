"""Service GitSync chính.

Module này cung cấp GitSync class để đồng bộ code từ Git repositories:
- Repository cloning: Clone Git repository vào temporary directory
- File discovery: Tìm files dựa trên patterns và paths
- File synchronization: Đồng bộ từng file (extract, chunk, embed)
- Content hashing: Phát hiện thay đổi bằng SHA1 hash
- Cleanup: Tự động cleanup temporary directories

Hỗ trợ sync code files với chunking đặc biệt cho code (preserve functions/classes context).
"""
import logging
from typing import Dict, Any, List
from pathlib import Path
import tempfile
import shutil

from app.database import SessionLocal
from app.services.git_sync.repository import RepositoryManager
from app.services.git_sync.file_sync import FileSyncHandler

logger = logging.getLogger(__name__)


class GitSync:
    """Service đồng bộ files từ Git repository vào database và vector store.
    
    Class này xử lý toàn bộ quy trình sync một Git repository:
    - Clone repository vào thư mục tạm
    - Tìm files khớp với patterns
    - Sync từng file (chunk, embed, lưu database)
    - Dọn dẹp thư mục tạm
    
    Attributes:
        temp_dir: Thư mục tạm để clone repositories (Path)
        repository_manager: RepositoryManager instance để quản lý Git operations
        file_sync_handler: FileSyncHandler instance để sync từng file
    """
    
    def __init__(self):
        """Khởi tạo GitSync với thư mục tạm và handlers."""
        self.temp_dir = Path(tempfile.gettempdir()) / "rag_git_sync"
        self.temp_dir.mkdir(exist_ok=True)
        self.repository_manager = RepositoryManager(self.temp_dir)
        self.file_sync_handler = FileSyncHandler()
    
    def sync_repository(
        self,
        repo_url: str,
        branch: str = "main",
        file_patterns: List[str] = None,
        target_paths: List[str] = None
    ) -> Dict[str, Any]:
        """Clone và đồng bộ files từ Git repository vào database.
        
        Quy trình:
        1. Clone repository vào thư mục tạm
        2. Tìm files khớp với patterns và target_paths
        3. Sync từng file (tạo source, chunks, embeddings)
        4. Dọn dẹp thư mục tạm
        5. Trả về statistics
        
        Args:
            repo_url: URL của Git repository (string, có thể là HTTPS hoặc SSH)
            branch: Branch để clone và sync (mặc định: "main")
            file_patterns: Danh sách file patterns để filter (tùy chọn).
                Ví dụ: ['*.md', '*.py', '*.js']. Nếu None, sử dụng patterns mặc định
            target_paths: Danh sách đường dẫn cụ thể để sync (tùy chọn).
                Ví dụ: ['docs/', 'src/']. Nếu None, tìm trong toàn bộ repository
        
        Returns:
            Dict[str, Any]: Dictionary chứa kết quả sync:
                - processed: Số lượng files đã xử lý (int)
                - created: Số lượng sources mới được tạo (int)
                - updated: Số lượng sources đã được cập nhật (int)
                - failed: Số lượng files thất bại (int)
                - errors: Danh sách error messages (List[str])
        
        Raises:
            Exception: Nếu clone repository thất bại hoặc có lỗi nghiêm trọng
        
        Note:
            - Repository được clone vào thư mục tạm và xóa sau khi xong
            - Mỗi file được sync riêng lẻ, lỗi một file không làm gián đoạn các file khác
            - File patterns mặc định: ['*.md', '*.py', '*.js', '*.java', '*.cpp', '*.txt']
            - Database transaction được commit sau khi tất cả files được xử lý
        """
        db = SessionLocal()
        repo_dir = None
        
        try:
            result = {
                'processed': 0,
                'created': 0,
                'updated': 0,
                'failed': 0,
                'errors': []
            }
            
            # Clone repository (giữ nguyên thuật ngữ kỹ thuật)
            repo, repo_dir = self.repository_manager.clone_repository(repo_url, branch)
            
            # Tìm files để xử lý
            files_to_process = self.repository_manager.find_files(
                repo_dir,
                file_patterns,
                target_paths
            )
            
            # Xử lý từng file
            for file_path in files_to_process:
                try:
                    if file_path.is_file():
                        self.file_sync_handler.sync_file(file_path, repo, repo_url, db)
                        result['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync file {file_path}: {e}")
                    result['failed'] += 1
                    result['errors'].append(f"{file_path.name}: {str(e)}")
            
            db.commit()
            logger.info(f"Git sync completed: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Repository sync failed: {e}")
            db.rollback()
            raise
        
        finally:
            # Dọn dẹp
            if repo_dir and repo_dir.exists():
                try:
                    shutil.rmtree(repo_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
            
            db.close()


# Singleton instance
git_sync = GitSync()

