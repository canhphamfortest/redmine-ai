"""Handler upload file thủ công"""
import logging
import uuid
from pathlib import Path
from fastapi import UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.api.ingest.file_processor import process_file, process_file_async

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


async def ingest_manual(
    file: UploadFile = File(...),
    source_type: str = Form("document"),
    project_key: Optional[str] = Form(None),
    language: Optional[str] = Form("en"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Upload và ingestion file thủ công vào database và vector store.
    
    Endpoint này cho phép upload file và ingest vào hệ thống:
    1. Lưu file vào thư mục uploads
    2. Trích xuất nội dung từ file (PDF, DOCX, TXT, etc.)
    3. Chunk nội dung thành các chunks nhỏ hơn
    4. Tạo embeddings cho các chunks
    5. Lưu source, chunks, và embeddings vào database
    
    Args:
        file: File cần upload (UploadFile)
        source_type: Loại source ("document", "code", etc.) (mặc định: "document")
        project_key: Project key để gán cho source (tùy chọn)
        language: Mã ngôn ngữ của file (mặc định: "en")
        background_tasks: FastAPI BackgroundTasks để xử lý file lớn
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa kết quả:
            - Nếu file < 10MB (xử lý ngay):
                - status: "completed"
                - source_id: UUID của source đã tạo (str)
                - chunks_created: Số lượng chunks đã tạo (int)
                - message: "File processed successfully"
            - Nếu file >= 10MB (background processing):
                - status: "processing"
                - job_id: ID của background job (str)
                - message: "Large file queued for background processing"
    
    Raises:
        HTTPException: HTTP 500 nếu quá trình ingestion thất bại
    
    Note:
        - File được lưu với tên unique (UUID + filename)
        - Files >= 10MB được xử lý trong background để tránh timeout
        - Files < 10MB được xử lý ngay lập tức
        - Hỗ trợ nhiều định dạng: PDF, DOCX, TXT, Markdown, JSON, HTML
        - Sử dụng ContentExtractor để trích xuất nội dung
    """
    try:
        # Lưu file đã upload
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File saved: {file_path}")
        
        # Đối với file lớn, xử lý trong background
        file_size = len(content)
        if file_size > 10 * 1024 * 1024:  # 10MB
            job_id = str(uuid.uuid4())
            background_tasks.add_task(
                process_file_async,
                str(file_path),
                file.filename,
                source_type,
                project_key,
                language,
                job_id,
                db
            )
            return {
                "status": "processing",
                "job_id": job_id,
                "message": "Large file queued for background processing"
            }
        
        # Xử lý ngay lập tức cho file nhỏ
        result = process_file(
            str(file_path),
            file.filename,
            source_type,
            project_key,
            language,
            db
        )
        
        return {
            "status": "completed",
            "source_id": result["source_id"],
            "chunks_created": result["chunks_count"],
            "message": "File processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Manual ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

