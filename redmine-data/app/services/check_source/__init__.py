"""Module checker source.

Module này cung cấp source checking service để kiểm tra và cập nhật sources:
- SourceChecker: Class chính thực hiện source checking operations
- source_checker: Singleton instance được sử dụng trong toàn bộ ứng dụng

Các chức năng chính:
- Check sources: Kiểm tra các sources có cần cập nhật không
- Priority checking: Ưu tiên check các sources quan trọng (outdated, failed)
- Resync sources: Re-sync các sources đã outdated hoặc failed
- Content comparison: So sánh content hash để phát hiện thay đổi

Hỗ trợ check cho Redmine issues và wiki pages, tự động phát hiện và sync các sources đã thay đổi.
"""
from app.services.check_source.checker import SourceChecker

# Singleton instance
source_checker = SourceChecker()

__all__ = ['SourceChecker', 'source_checker']

