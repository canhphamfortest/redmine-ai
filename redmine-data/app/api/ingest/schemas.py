"""Pydantic schemas cho API ingest.

Module này định nghĩa các request/response schemas cho ingestion endpoints:
- RedmineIssueRequest: Schema cho ingest Redmine issue
- RedmineWikiRequest: Schema cho ingest Redmine wiki page
- RedmineWikiProjectRequest: Schema cho ingest tất cả wiki pages trong project
"""
from pydantic import BaseModel
from typing import Optional


class RedmineIssueRequest(BaseModel):
    """Schema cho request ingest Redmine issue.
    
    Attributes:
        issue_id: ID của Redmine issue cần ingest (int)
        project_id: ID hoặc identifier của project (str, optional).
                   Nếu không cung cấp, sẽ được lấy từ issue
    """
    issue_id: int
    project_id: Optional[str] = None


class RedmineWikiRequest(BaseModel):
    """Schema cho request ingest Redmine wiki page.
    
    Attributes:
        project_id: ID hoặc identifier của project (str)
        wiki_page: Tên hoặc title của wiki page (str)
        version: Phiên bản cụ thể của wiki page (int, optional).
                Nếu không cung cấp, sẽ ingest version mới nhất
    """
    project_id: str
    wiki_page: str
    version: Optional[int] = None


class RedmineWikiProjectRequest(BaseModel):
    """Schema cho request ingest tất cả wiki pages trong project.
    
    Attributes:
        project_id: ID hoặc identifier của project (str)
        incremental: Có ingest incremental không (bool, default: True).
                    Nếu True, chỉ ingest các pages chưa có hoặc đã thay đổi.
                    Nếu False, ingest lại tất cả pages
    """
    project_id: str
    incremental: Optional[bool] = True

