from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Cấu hình ứng dụng RAG System.
    
    Class này chứa tất cả các cấu hình của ứng dụng, được load từ environment
    variables hoặc file .env. Kế thừa từ Pydantic BaseSettings để tự động parse
    và validate các giá trị cấu hình.
    
    Attributes:
        app_name: Tên ứng dụng (mặc định: "RAG System")
        app_version: Phiên bản ứng dụng (mặc định: "1.0.0")
        debug: Chế độ debug (mặc định: True)
        log_level: Mức độ logging (mặc định: "INFO")
        database_url: URL kết nối database (bắt buộc)
        redis_url: URL kết nối Redis (mặc định: "redis://redis:6379/0")
        openai_api_key: API key cho OpenAI (mặc định: "")
        openai_model: Model OpenAI sử dụng (mặc định: "gpt-4o-mini")
        embedding_model: Model embedding sử dụng (mặc định: "intfloat/multilingual-e5-large")
        chunk_size: Kích thước chunk khi chia văn bản (mặc định: 512)
        chunk_overlap: Độ chồng chéo giữa các chunk (mặc định: 50)
        similarity_top_k: Số lượng kết quả top khi tìm kiếm (mặc định: 5)
        similarity_threshold: Ngưỡng similarity tối thiểu (mặc định: 0.5)
        redmine_url: URL của Redmine instance
        redmine_api_key: API key cho Redmine
        redmine_api_delay: Độ trễ giữa các lời gọi Redmine API (giây, mặc định: 0.2)
        max_attachment_content_size: Kích thước tối đa của attachment content cho tất cả file types (characters, mặc định: 5000 = ~5KB). Lấy 2500 chars từ đầu và 2500 chars từ cuối.
        git_username: Username cho Git authentication
        git_token: Token cho Git authentication
        scheduler_timezone: Timezone cho scheduler (mặc định: "Asia/Ho_Chi_Minh")
        default_sync_cron: Cron expression mặc định cho sync job (mặc định: "0 2 * * *")
        backend_api_url: URL của backend API cho scheduler (mặc định: "http://backend:8000")
        smtp_host: SMTP host cho email (AWS SES endpoint hoặc SMTP server khác)
        smtp_port: SMTP port (mặc định: 587)
        smtp_user: SMTP username (AWS SES SMTP username hoặc email)
        smtp_password: SMTP password (AWS SES SMTP password)
        smtp_from_email: Email người gửi (mặc định dùng smtp_user nếu để trống)
        BUDGET_ALERT_EMAIL_RECIPIENTS: Email nhận thông báo (có thể nhiều email, cách nhau bởi dấu phẩy)
        ses_configuration_set: AWS SES Configuration Set name (e.g., "ait-ses-dev")
        api_host: Host cho API server (mặc định: "0.0.0.0")
        api_port: Port cho API server (mặc định: 8000)
        api_workers: Số lượng worker processes (mặc định: 4)
    """
    # Application
    app_name: str = "RAG System"
    app_version: str = "1.0.0"
    debug: bool = False  # Set to True only for development/debugging (causes verbose SQL logging)
    log_level: str = "INFO"
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    default_llm_provider: str = "openai"

    # Google Gemini - Service Account Only
    google_service_account_path: str = ""  # Đường dẫn đến service account JSON file
    google_cloud_project: str = ""  # Google Cloud Project ID (optional, có thể lấy từ service account JSON)
    google_cloud_location: str = "us-central1"  # Google Cloud Location (optional)
    google_ssl_verify: bool = True  # SSL verification cho Google API (set False nếu gặp lỗi certificate)

    # Anthropic Claude
    anthropic_api_key: str = ""

    # Groq
    groq_api_key: str = ""
    
    # Ollama (deprecated, kept for backward compatibility)
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    
    # Embedding
    embedding_model: str = "intfloat/multilingual-e5-large"
    
    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Vector Search
    similarity_top_k: int = 5
    similarity_threshold: float = 0.5  # Ngưỡng thấp hơn để recall tốt hơn
    
    # Redmine
    redmine_url: str = ""
    redmine_api_key: str = ""
    redmine_api_delay: float = 0.2  # Độ trễ giữa các lời gọi API tính bằng giây (mặc định: 0.2s = ~5 req/s)
    max_attachment_content_size: int = 5000  # Kích thước tối đa của attachment content cho tất cả file types (characters, mặc định: 5000 = ~5KB). Lấy 2500 chars từ đầu và 2500 chars từ cuối.
    
    # Git
    git_username: str = ""
    git_token: str = ""
    
    # Scheduler
    scheduler_timezone: str = "Asia/Ho_Chi_Minh"
    default_sync_cron: str = "0 2 * * *"
    backend_api_url: str = "http://backend:8000"  # Backend API URL for scheduler to call
    
    # Email / SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""  # Email người gửi (mặc định dùng smtp_user nếu để trống)
    BUDGET_ALERT_EMAIL_RECIPIENTS: str = ""
    
    # AWS SES Configuration
    ses_configuration_set: str = ""  # AWS SES Configuration Set (e.g., "ait-ses-dev")
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Lấy instance cấu hình ứng dụng (singleton với cache).
    
    Hàm này sử dụng lru_cache để đảm bảo chỉ tạo một instance Settings duy nhất
    trong suốt vòng đời ứng dụng. Lần đầu tiên gọi sẽ load cấu hình từ environment
    variables hoặc file .env, các lần gọi sau sẽ trả về instance đã cache.
    
    Returns:
        Settings: Instance cấu hình ứng dụng đã được cache
    """
    return Settings()


settings = get_settings()