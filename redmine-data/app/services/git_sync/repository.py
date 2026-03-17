"""Clone repository và phát hiện file.

Module này cung cấp RepositoryManager class để quản lý Git repositories:
- Repository cloning: Clone Git repository vào temporary directory
- File discovery: Tìm files dựa trên patterns, paths, và extensions
- Branch management: Checkout specific branch
- Cleanup: Xóa temporary directories sau khi xong

Sử dụng GitPython library để tương tác với Git repositories.
"""
import logging
import shutil
from pathlib import Path
from typing import List
from git import Repo

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Quản lý các thao tác Git repository (clone, find files).
    
    Class này xử lý việc clone Git repositories và tìm files trong repository.
    Sử dụng GitPython library để thao tác với Git.
    
    Attributes:
        temp_dir: Thư mục tạm để clone repositories (Path)
    """
    
    def __init__(self, temp_dir: Path):
        """Khởi tạo RepositoryManager.
        
        Args:
            temp_dir: Thư mục tạm để clone repositories
        """
        self.temp_dir = temp_dir
    
    def clone_repository(self, repo_url: str, branch: str = "main") -> tuple[Repo, Path]:
        """Clone Git repository vào thư mục tạm.
        
        Hàm này clone repository từ URL vào thư mục tạm. Nếu thư mục đã tồn tại,
        sẽ xóa trước khi clone mới.
        
        Args:
            repo_url: URL của Git repository (string)
            branch: Branch để clone (mặc định: "main")
        
        Returns:
            Tuple[Repo, Path]: Tuple chứa:
                - Repo: GitPython Repo object
                - repo_dir: Path đến thư mục repository đã clone
        
        Raises:
            GitCommandError: Nếu clone thất bại (authentication, network, etc.)
        
        Note:
            - Repository name được extract từ URL (phần cuối, bỏ .git)
            - Thư mục đích: temp_dir / repo_name
            - Nếu thư mục đã tồn tại, sẽ bị xóa trước khi clone
        """
        logger.info(f"Cloning repository: {repo_url}")
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_dir = self.temp_dir / repo_name
        
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        
        repo = Repo.clone_from(repo_url, repo_dir, branch=branch)
        return repo, repo_dir
    
    def find_files(
        self,
        repo_dir: Path,
        file_patterns: List[str] = None,
        target_paths: List[str] = None
    ) -> List[Path]:
        """Tìm files khớp với patterns trong repository.
        
        Hàm này tìm tất cả files trong repository khớp với file_patterns.
        Nếu target_paths được chỉ định, chỉ tìm trong các đường dẫn đó.
        Nếu không, tìm trong toàn bộ repository.
        
        Args:
            repo_dir: Thư mục repository đã clone (Path)
            file_patterns: Danh sách file patterns để tìm (tùy chọn).
                Ví dụ: ['*.md', '*.py']. Nếu None, sử dụng patterns mặc định
            target_paths: Danh sách đường dẫn cụ thể để tìm (tùy chọn).
                Ví dụ: ['docs/', 'src/']. Nếu None, tìm trong toàn bộ repo
        
        Returns:
            List[Path]: Danh sách đường dẫn đến các files khớp với patterns
        
        Note:
            - File patterns mặc định: ['*.md', '*.py', '*.js', '*.java', '*.cpp', '*.txt']
            - Nếu target_paths được chỉ định, pattern được áp dụng trong mỗi target path
            - Sử dụng glob() cho target paths và rglob() cho toàn bộ repo
            - Kết quả có thể chứa duplicates nếu patterns overlap
        """
        if not file_patterns:
            file_patterns = ['*.md', '*.py', '*.js', '*.java', '*.cpp', '*.txt']
        
        files_to_process = []
        for pattern in file_patterns:
            if target_paths:
                for target in target_paths:
                    files_to_process.extend(repo_dir.glob(f"{target}/**/{pattern}"))
            else:
                files_to_process.extend(repo_dir.rglob(pattern))
        
        logger.info(f"Found {len(files_to_process)} files matching patterns")
        return files_to_process

