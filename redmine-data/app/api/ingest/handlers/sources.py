"""Các handler quản lý source"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import and_, or_

from app.database import get_db
from app.models import Source
from app.services.check_source import SourceChecker

logger = logging.getLogger(__name__)


async def list_sources(
    source_type: Optional[str] = None,
    sync_status: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Liệt kê sources với các bộ lọc và phân trang.
    
    Endpoint này trả về danh sách sources với khả năng filter theo:
    - source_type (redmine_issue, redmine_wiki, git_file, document, etc.)
    - sync_status (success, failed, outdated, pending)
    - project_id: Project ID (số) hoặc Project key (string) để filter
    
    Args:
        source_type: Loại source để filter (tùy chọn)
        sync_status: Trạng thái sync để filter (tùy chọn)
        project_id: Project ID (số) hoặc Project key (string) để filter (tùy chọn)
        limit: Số lượng sources tối đa trả về (mặc định: 100)
        offset: Số lượng sources bỏ qua (mặc định: 0)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - total: Tổng số sources khớp với filters (int)
            - limit: Limit đã sử dụng (int)
            - offset: Offset đã sử dụng (int)
            - sources: Danh sách sources (List[Dict]):
                - id: UUID của source (str)
                - source_type: Loại source (str)
                - external_id: External ID (str)
                - external_url: URL ngoài (str, optional)
                - project_key: Project key (str, optional)
                - project_id: Project ID (int, optional)
                - sync_status: Trạng thái sync (str)
                - last_sync_at: Thời gian sync cuối (str, ISO format, optional)
                - created_at: Thời gian tạo (str, ISO format)
                - updated_at: Thời gian cập nhật (str, ISO format)
    
    Note:
        - Sources được sắp xếp theo updated_at giảm dần (mới nhất trước)
        - Tất cả filters được kết hợp bằng AND
    """
    query = db.query(Source)
    
    filters = []
    if source_type:
        filters.append(Source.source_type == source_type)
    if sync_status:
        filters.append(Source.sync_status == sync_status)
    if project_id:
        # Hỗ trợ filter theo cả project_id (số) và project_key (string)
        # Nếu input là số, kiểm tra project_id (exact match)
        # Nếu input là string, dùng LIKE để tìm project_key (partial match)
        try:
            # Thử chuyển đổi thành số
            project_id_int = int(project_id)
            # Nếu là số, kiểm tra project_id (exact match)
            filters.append(Source.project_id == project_id_int)
        except ValueError:
            # Nếu không phải số, dùng LIKE để tìm project_key (partial match)
            filters.append(Source.project_key.like(f"%{project_id}%"))
    
    if filters:
        query = query.filter(and_(*filters))
    
    total = query.count()
    sources = query.order_by(Source.updated_at.desc()).limit(limit).offset(offset).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "sources": [
            {
                "id": str(source.id),
                "source_type": source.source_type,
                "external_id": source.external_id,
                "external_url": source.external_url,
                "project_key": source.project_key,
                "project_id": source.project_id,
                "sync_status": source.sync_status,
                "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
                "created_at": source.created_at.isoformat() if source.created_at else None,
                "updated_at": source.updated_at.isoformat() if source.updated_at else None,
            }
            for source in sources
        ]
    }


async def check_source(source_id: str, db: Session = Depends(get_db)):
    """Kiểm tra xem source có cần được đồng bộ lại không.
    
    Endpoint này kiểm tra một source cụ thể bằng cách so sánh content hash
    trong database với content hash trong Redmine để phát hiện updates.
    
    Args:
        source_id: UUID của source cần kiểm tra (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa kết quả từ SourceChecker.check_single_source():
            - success: True nếu kiểm tra thành công, False nếu có lỗi (bool)
            - outdated: True nếu source đã outdated, False nếu không (bool, nếu success=True)
            - was_outdated: True nếu source đã outdated trước đó (bool, nếu success=True)
            - message: Thông báo kết quả (str, nếu success=True)
            - error: Error message nếu có lỗi (str, nếu success=False)
    
    Raises:
        HTTPException: HTTP 500 nếu quá trình kiểm tra thất bại
    
    Note:
        - Chỉ hỗ trợ redmine_issue sources
        - Sử dụng SourceChecker để thực hiện kiểm tra
        - Source sẽ được đánh dấu outdated nếu content đã thay đổi
    """
    try:
        source_checker = SourceChecker()
        result = source_checker.check_single_source(source_id)
        return result
    except Exception as e:
        logger.error(f"Failed to check source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def list_projects(db: Session = Depends(get_db)):
    """Lấy danh sách unique projects từ sources.
    
    Endpoint này trả về danh sách tất cả projects có trong sources,
    được query trực tiếp từ database để tối ưu hiệu suất.
    
    Args:
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - projects: Danh sách projects (List[Dict]):
                - project_id: Project ID (int)
                - project_key: Project key (str, optional)
                - display_name: Tên hiển thị (str): project_key hoặc "Project {id}"
    
    Note:
        - Chỉ trả về projects có project_id (không null)
        - Sắp xếp theo project_key nếu có, sau đó theo project_id
    """
    try:
        # Query unique projects với project_id không null
        # Sử dụng distinct để lấy unique combinations
        results = db.query(
            Source.project_id,
            Source.project_key
        ).filter(
            Source.project_id.isnot(None)
        ).distinct().all()
        
        projects = []
        for project_id, project_key in results:
            display_name = project_key if project_key else f"Project {project_id}"
            projects.append({
                "project_id": project_id,
                "project_key": project_key,
                "display_name": display_name
            })
        
        # Sort by project_key first, then by project_id
        projects.sort(key=lambda x: (x["project_key"] or "", x["project_id"]))
        
        return {
            "projects": projects
        }
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def resync_source(source_id: str, db: Session = Depends(get_db)):
    """Đồng bộ lại một source từ Redmine.
    
    Endpoint này thực hiện sync lại hoàn toàn một source (issue hoặc wiki page)
    từ Redmine, bất kể trạng thái hiện tại. Chunks và embeddings sẽ được tạo lại
    nếu content đã thay đổi.
    
    Args:
        source_id: UUID của source cần đồng bộ lại (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa kết quả từ SourceChecker.resync_source():
            - success: True nếu sync thành công, False nếu có lỗi (bool)
            - message: Thông báo kết quả (str, nếu success=True)
            - error: Error message nếu có lỗi (str, nếu success=False)
    
    Raises:
        HTTPException:
            - HTTP 400 nếu sync thất bại (từ SourceChecker)
            - HTTP 500 nếu có lỗi trong quá trình sync
    
    Note:
        - Hỗ trợ redmine_issue và redmine_wiki sources
        - Source sẽ được sync lại hoàn toàn (tạo lại chunks/embeddings nếu cần)
        - Sync status sẽ được cập nhật thành 'success' sau khi sync thành công
    """
    try:
        source_checker = SourceChecker()
        result = source_checker.resync_source(source_id)
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to re-sync source'))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to re-sync source {source_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

