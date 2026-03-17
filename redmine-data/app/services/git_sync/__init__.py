"""Module service đồng bộ Git.

Module này cung cấp Git synchronization service để đồng bộ code từ Git repositories:
- GitSync: Class chính thực hiện Git sync operations
- git_sync: Singleton instance được sử dụng trong toàn bộ ứng dụng

Các chức năng chính:
- Clone repository: Clone Git repository vào temporary directory
- Find files: Tìm files dựa trên patterns và paths
- Sync files: Đồng bộ từng file (extract, chunk, embed)
- Content hashing: Phát hiện thay đổi bằng SHA1 hash
- Cleanup: Tự động cleanup temporary directories sau khi sync

Hỗ trợ sync code files với chunking đặc biệt cho code (preserve functions/classes context).
"""
from app.services.git_sync.sync import git_sync, GitSync

__all__ = ['git_sync', 'GitSync']

