"""Module đồng bộ Redmine.

Module này cung cấp Redmine synchronization service để đồng bộ dữ liệu từ Redmine:
- RedmineSync: Class chính thực hiện Redmine sync operations
- redmine_sync: Singleton instance (chỉ được tạo nếu Redmine được cấu hình)
- safe_attr: Utility function để safely get attributes từ Redmine objects

Các chức năng chính:
- Sync issues: Đồng bộ Redmine issues với metadata và content
- Sync wiki: Đồng bộ Redmine wiki pages
- Content building: Xây dựng searchable content từ issue/wiki data
- Attachment handling: Xử lý và download attachments
- Issue/Wiki sync handlers: Xử lý sync cho từng issue/wiki page

Module chỉ được khởi tạo nếu Redmine URL và API key được cấu hình trong settings.
"""
from app.config import settings
from app.services.redmine.sync import RedmineSync
from app.services.redmine.utils import safe_attr

# Singleton instance
redmine_sync = RedmineSync() if settings.redmine_url and settings.redmine_api_key else None

__all__ = ['RedmineSync', 'redmine_sync', 'safe_attr']

