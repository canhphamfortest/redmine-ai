from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Tạo database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.debug
)

# Tạo session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho models
Base = declarative_base()


def get_db():
    """Dependency function cho FastAPI endpoints để lấy database session.
    
    Hàm này được sử dụng như một dependency trong FastAPI để tự động quản lý
    database session. Khi endpoint được gọi, nó sẽ tạo một session mới và
    yield cho endpoint sử dụng. Sau khi endpoint hoàn thành, session sẽ được
    đóng tự động trong khối finally.
    
    Yields:
        Session: SQLAlchemy database session
    
    Example:
        Sử dụng trong FastAPI endpoint:
        ```python
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Khởi tạo tất cả các bảng database dựa trên SQLAlchemy models.
    
    Hàm này sẽ tạo tất cả các bảng được định nghĩa trong các model classes
    kế thừa từ Base (declarative_base). Nếu bảng đã tồn tại, nó sẽ không tạo lại.
    Thường được gọi khi ứng dụng khởi động để đảm bảo database schema đã sẵn sàng.
    
    Note:
        Hàm này chỉ tạo bảng, không xóa hoặc cập nhật schema. Để migrate schema,
        cần sử dụng công cụ migration như Alembic.
    """
    Base.metadata.create_all(bind=engine)