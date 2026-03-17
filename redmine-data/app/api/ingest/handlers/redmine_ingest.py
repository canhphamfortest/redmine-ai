"""Các handler ingestion Redmine"""
import logging
from fastapi import Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.redmine import redmine_sync
from app.api.ingest.schemas import RedmineIssueRequest, RedmineWikiRequest, RedmineWikiProjectRequest

logger = logging.getLogger(__name__)


async def ingest_redmine(
    payload: RedmineIssueRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Ingest một Redmine issue đơn lẻ vào database và vector store.
    
    Endpoint này cho phép sync một Redmine issue cụ thể theo yêu cầu.
    Issue sẽ được lấy từ Redmine API, chunk, embed, và lưu vào database.
    
    Args:
        payload: RedmineIssueRequest chứa issue_id cần ingest
        background_tasks: FastAPI BackgroundTasks (không được sử dụng trong hàm này)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - status: Trạng thái ingest ("completed")
            - issue_id: ID của issue đã ingest (int)
            - result: Kết quả sync từ RedmineSync (Dict)
    
    Raises:
        HTTPException:
            - HTTP 400 nếu Redmine integration chưa được cấu hình
            - HTTP 500 nếu quá trình ingest thất bại
    
    Note:
        - Issue được sync đồng bộ (không background)
        - Sử dụng RedmineSync.sync_single_issue() để sync
        - Issue phải tồn tại trong Redmine
    """
    if redmine_sync is None:
        raise HTTPException(
            status_code=400,
            detail="Redmine integration is not configured. Please set REDMINE_URL and REDMINE_API_KEY."
        )

    try:
        logger.info(f"Manual Redmine ingest requested for issue #{payload.issue_id}")
        result = redmine_sync.sync_single_issue(payload.issue_id)
        return {
            "status": "completed",
            "issue_id": payload.issue_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Redmine manual ingest failed for issue #{payload.issue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def ingest_redmine_wiki(
    payload: RedmineWikiRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Ingest một trang wiki Redmine đơn lẻ vào database và vector store.
    
    Endpoint này cho phép sync một wiki page cụ thể theo yêu cầu.
    Wiki page sẽ được lấy từ Redmine API, chunk, embed, và lưu vào database.
    
    Args:
        payload: RedmineWikiRequest chứa project_id, wiki_page_title, và version (optional)
        background_tasks: FastAPI BackgroundTasks (không được sử dụng trong hàm này)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - status: Trạng thái ingest ("completed")
            - project_id: ID của project (str)
            - wiki_page: Tiêu đề của wiki page (str)
            - result: Kết quả sync từ RedmineSync (Dict)
    
    Raises:
        HTTPException:
            - HTTP 400 nếu Redmine integration chưa được cấu hình
            - HTTP 500 nếu quá trình ingest thất bại
    
    Note:
        - Wiki page được sync đồng bộ (không background)
        - Sử dụng RedmineSync.sync_wiki_page() để sync
        - Nếu version được chỉ định, sẽ sync version cụ thể
        - Nếu version=None, sẽ sync version mới nhất
    """
    if redmine_sync is None:
        raise HTTPException(
            status_code=400,
            detail="Redmine integration is not configured. Please set REDMINE_URL and REDMINE_API_KEY."
        )

    try:
        logger.info(f"Manual Redmine wiki ingest requested for page '{payload.wiki_page_title}' in project {payload.project_id}")
        result = redmine_sync.sync_wiki_page(
            payload.project_id,
            payload.wiki_page_title,
            payload.version
        )
        return {
            "status": "completed",
            "project_id": payload.project_id,
            "wiki_page": payload.wiki_page_title,
            "result": result
        }
    except Exception as e:
        logger.error(f"Redmine manual wiki ingest failed for page '{payload.wiki_page_title}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def ingest_redmine_wiki_project(
    payload: RedmineWikiProjectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Ingest tất cả các trang wiki từ một Redmine project.
    
    Endpoint này cho phép sync tất cả wiki pages trong một project.
    Tất cả wiki pages sẽ được lấy từ Redmine API, chunk, embed, và lưu vào database.
    
    Args:
        payload: RedmineWikiProjectRequest chứa project_id và incremental flag
        background_tasks: FastAPI BackgroundTasks (không được sử dụng trong hàm này)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - status: Trạng thái ingest ("completed")
            - project_id: ID của project (str)
            - result: Kết quả sync từ RedmineSync (Dict):
                - processed: Số lượng wiki pages đã xử lý (int)
                - created: Số lượng wiki pages mới được tạo (int)
                - updated: Số lượng wiki pages đã cập nhật (int)
                - failed: Số lượng wiki pages thất bại (int)
                - errors: Danh sách error messages (List[str])
    
    Raises:
        HTTPException:
            - HTTP 400 nếu Redmine integration chưa được cấu hình
            - HTTP 500 nếu quá trình ingest thất bại
    
    Note:
        - Wiki pages được sync đồng bộ (không background)
        - Sử dụng RedmineSync.sync_project_wiki() để sync
        - Nếu incremental=True, chỉ sync các pages đã cập nhật kể từ lần sync cuối
        - Nếu incremental=False, sync tất cả pages
    """
    if redmine_sync is None:
        raise HTTPException(
            status_code=400,
            detail="Redmine integration is not configured. Please set REDMINE_URL and REDMINE_API_KEY."
        )

    try:
        logger.info(f"Manual Redmine wiki project ingest requested for project {payload.project_id}")
        result = redmine_sync.sync_project_wiki(
            payload.project_id,
            payload.incremental
        )
        return {
            "status": "completed",
            "project_id": payload.project_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Redmine manual wiki project ingest failed for project {payload.project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

