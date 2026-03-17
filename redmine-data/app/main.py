from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db
from app.api import ingest, search, jobs, openai_config, auth, budget
from app.logging_config import setup_logging
from app.middleware.access_log import AccessLogMiddleware

# Setup logging with file output
setup_logging(service_name="backend", level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời của ứng dụng FastAPI.
    
    Context manager này xử lý các sự kiện khởi động và tắt của ứng dụng.
    Khi ứng dụng khởi động, nó sẽ khởi tạo database. Khi ứng dụng tắt,
    nó sẽ ghi log thông báo shutdown.
    
    Args:
        app: Instance của FastAPI application
    
    Yields:
        None: Yield để giữ context manager active trong suốt vòng đời app
    """
    # Khởi động
    logger.info("Starting RAG System...")
    init_db()
    logger.info("Database initialized")
    yield
    # Tắt
    logger.info("Shutting down RAG System...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# Middleware for access logging
app.add_middleware(AccessLogMiddleware)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bao gồm routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(openai_config.router, prefix="/api/openai-config", tags=["LLM Config"])
app.include_router(budget.router, prefix="/api/budget", tags=["Budget"])


@app.get("/")
async def root():
    """Endpoint kiểm tra trạng thái cơ bản của ứng dụng.
    
    Endpoint này trả về thông tin cơ bản về ứng dụng bao gồm tên ứng dụng,
    phiên bản và trạng thái đang chạy. Được sử dụng để xác nhận rằng API
    đang hoạt động.
    
    Returns:
        dict: Dictionary chứa thông tin ứng dụng:
            - app (str): Tên ứng dụng
            - version (str): Phiên bản ứng dụng
            - status (str): Trạng thái "running"
    """
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Kiểm tra trạng thái sức khỏe chi tiết của hệ thống.
    
    Endpoint này kiểm tra kết nối đến các dịch vụ quan trọng:
    - Database: Kiểm tra kết nối bằng cách thực thi query đơn giản
    - Redis: Kiểm tra kết nối cache (tùy chọn, không bắt buộc)
    - OpenAI Model: Trả về model đang được sử dụng
    
    Nếu database không kết nối được, endpoint sẽ trả về HTTP 503 (Service Unavailable).
    Redis là tùy chọn nên lỗi Redis không làm cho hệ thống bị đánh dấu là unhealthy.
    
    Returns:
        dict: Dictionary chứa trạng thái sức khỏe:
            - status (str): "healthy" hoặc "unhealthy"
            - database (str): "connected" hoặc "disconnected"
            - redis (str): "connected" hoặc "disconnected"
            - openai_model (str): Tên model OpenAI đang sử dụng
    
    Raises:
        HTTPException: HTTP 503 nếu database không kết nối được
    """
    from app.database import engine
    from app.services.cache import cache
    
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "openai_model": settings.openai_model
    }
    
    # Kiểm tra kết nối database
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    # Kiểm tra kết nối Redis
    try:
        if cache._is_connected():
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "disconnected"
            # Redis là tùy chọn, không đánh dấu là unhealthy
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["redis"] = "disconnected"
    
    # Chỉ trả về unhealthy nếu database bị down
    if health_status["database"] == "disconnected":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status