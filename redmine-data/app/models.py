from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, Date, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from app.database import Base


class Source(Base):
    """Model đại diện cho một source (nguồn dữ liệu) trong hệ thống.
    
    Source có thể là Redmine issue, wiki page, Git file, hoặc document.
    Mỗi source có thể có nhiều chunks và embeddings liên quan.
    
    Attributes:
        id: UUID primary key
        source_type: Loại source (redmine_issue, redmine_wiki, git_file, document)
        external_id: ID ngoài của source (format: "redmine_issue_{id}", etc.)
        external_url: URL ngoài đến source gốc
        project_key: Project key/identifier
        project_id: Project ID (integer)
        language: Mã ngôn ngữ (mặc định: "en")
        sha1_content: SHA1 hash của content để phát hiện thay đổi
        sync_status: Trạng thái sync (pending, success, failed, outdated)
        error_message: Thông báo lỗi nếu sync thất bại
        retry_count: Số lần thử lại sync
        last_sync_at: Thời gian sync cuối cùng
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "source"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String, nullable=False)
    external_id = Column(String)
    external_url = Column(String)
    project_key = Column(String)
    project_id = Column(Integer)
    language = Column(String, default="en")
    sha1_content = Column(String)
    # Các trường theo dõi sync (đã gộp từ issue_sync_log)
    sync_status = Column(String, default="success")  # 'pending', 'success', 'failed', 'outdated'
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_sync_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SourceRedmineIssue(Base):
    """Model chứa metadata đặc thù cho Redmine issues.
    
    Model này lưu trữ các thông tin chi tiết về Redmine issue như tracker,
    status, priority, assignee, dates, etc. Liên kết với Source thông qua source_id.
    
    Attributes:
        id: UUID primary key
        source_id: Foreign key đến Source
        tracker_id, tracker_name: Tracker của issue
        status_id, status_name, status_is_closed: Status của issue
        priority_id, priority_name: Priority của issue
        category_id, category_name: Category của issue
        author_id, author_name: Tác giả của issue
        assigned_to_id, assigned_to_name: Người được giao issue
        fixed_version_id, fixed_version_name: Version fix của issue
        parent_issue_id: ID của issue cha (nếu có)
        estimated_hours: Số giờ ước tính
        done_ratio: Tỷ lệ hoàn thành (%)
        start_date, due_date: Ngày bắt đầu và hạn chót
        closed_on: Thời gian đóng issue
    """
    __tablename__ = "source_redmine_issue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE"))
    tracker_id = Column(Integer)
    tracker_name = Column(String)
    status_id = Column(Integer)
    status_name = Column(String)
    status_is_closed = Column(Boolean)
    priority_id = Column(Integer)
    priority_name = Column(String)
    category_id = Column(Integer)
    category_name = Column(String)
    author_id = Column(Integer)
    author_name = Column(String)
    assigned_to_id = Column(Integer)
    assigned_to_name = Column(String)
    fixed_version_id = Column(Integer)
    fixed_version_name = Column(String)
    parent_issue_id = Column(Integer)
    estimated_hours = Column(Float)
    done_ratio = Column(Integer)
    start_date = Column(Date)
    due_date = Column(Date)
    closed_on = Column(DateTime(timezone=True))


class SourceDocument(Base):
    """Model chứa metadata đặc thù cho documents (PDF, DOCX, etc.).
    
    Model này lưu trữ thông tin về file document như filename, mime type,
    file size, page count, author, dates. Liên kết với Source thông qua source_id.
    
    Attributes:
        id: UUID primary key
        source_id: Foreign key đến Source
        filename: Tên file
        mime_type: MIME type của file
        file_size_bytes: Kích thước file tính bằng bytes
        page_count: Số lượng trang (nếu áp dụng)
        author: Tác giả của document
        created_date: Ngày tạo file
        modified_date: Ngày sửa đổi file
        source_location: Vị trí nguồn của file
    """
    __tablename__ = "source_document"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE"))
    filename = Column(String)
    mime_type = Column(String)
    file_size_bytes = Column(Integer)
    page_count = Column(Integer)
    author = Column(String)
    created_date = Column(DateTime(timezone=True))
    modified_date = Column(DateTime(timezone=True))
    source_location = Column(String)


class SourceRedmineWiki(Base):
    """Model chứa metadata đặc thù cho Redmine wiki pages.
    
    Model này lưu trữ thông tin chi tiết về wiki page như version, author,
    parent page, comments, project info. Liên kết với Source thông qua source_id.
    
    Attributes:
        id: UUID primary key
        source_id: Foreign key đến Source
        wiki_version: Phiên bản của wiki page
        parent_page_title: Tiêu đề của trang cha (nếu có)
        author_id, author_name: Tác giả của wiki page
        comments: Comments của wiki page
        redmine_project_id, redmine_project_name: Thông tin project
    """
    __tablename__ = "source_redmine_wiki"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE"))
    wiki_version = Column(Integer)
    parent_page_title = Column(String)
    author_id = Column(Integer)
    author_name = Column(String)
    comments = Column(Text)
    redmine_project_id = Column(Integer)
    redmine_project_name = Column(String)


class SourceGitFile(Base):
    """Model chứa metadata đặc thù cho Git files.
    
    Model này lưu trữ thông tin về file trong Git repository như repository info,
    branch, commit info, file properties. Liên kết với Source thông qua source_id.
    
    Attributes:
        id: UUID primary key
        source_id: Foreign key đến Source
        repository_name: Tên repository
        repository_url: URL của repository
        branch: Branch chứa file
        commit_hash: Full commit hash
        commit_short_hash: Short commit hash (7 ký tự)
        commit_author_name, commit_author_email: Thông tin tác giả commit
        commit_date: Ngày commit
        commit_message: Message của commit
        file_extension: Extension của file
        file_type: Loại file (code, documentation, text, etc.)
        file_size_bytes: Kích thước file tính bằng bytes
        line_count: Số lượng dòng code
    """
    __tablename__ = "source_git_file"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE"))
    repository_name = Column(String)
    repository_url = Column(String)
    branch = Column(String)
    commit_hash = Column(String)
    commit_short_hash = Column(String)
    commit_author_name = Column(String)
    commit_author_email = Column(String)
    commit_date = Column(DateTime(timezone=True))
    commit_message = Column(Text)
    file_extension = Column(String)
    file_type = Column(String)
    file_size_bytes = Column(Integer)
    line_count = Column(Integer)


class Chunk(Base):
    """Model đại diện cho một chunk (đoạn văn bản) từ source.
    
    Chunk là một phần nhỏ của source đã được chia để embedding và tìm kiếm.
    Mỗi chunk có thể có một embedding tương ứng. Chunk có thể là text, code,
    issue metadata, journal, attachment, hoặc wiki content.
    
    Attributes:
        id: UUID primary key
        source_id: Foreign key đến Source
        ordinal: Thứ tự của chunk trong source (0-based)
        chunk_type: Loại chunk (text, code, issue_metadata, journal, attachment, wiki_content, wiki_metadata)
        text_content: Nội dung văn bản của chunk
        token_count: Số lượng tokens trong chunk
        status: Trạng thái chunk (pending, processed, failed)
        
        # Context metadata (cho tất cả chunk types)
        heading_title: Tiêu đề heading
        heading_level: Cấp độ heading
        author_id, author_name: Tác giả
        created_on: Ngày tạo
        
        # Journal/comment specific
        journal_id: ID của journal/comment
        is_private: Có phải private comment không
        
        # Code specific
        code_language: Ngôn ngữ lập trình
        function_name: Tên function
        class_name: Tên class
        line_start, line_end: Dòng bắt đầu và kết thúc
        
        # Document specific
        page_number: Số trang
        
        # Wiki specific
        wiki_version: Phiên bản wiki
        section_index: Chỉ số section
        
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "chunk"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("source.id", ondelete="CASCADE"))
    ordinal = Column(Integer, nullable=False)
    chunk_type = Column(String, default="text")
    text_content = Column(Text, nullable=False)
    token_count = Column(Integer)
    status = Column(String, default="pending")
    
    # Context metadata
    heading_title = Column(String)
    heading_level = Column(Integer)
    author_id = Column(Integer)
    author_name = Column(String)
    created_on = Column(DateTime(timezone=True))
    
    # Journal/comment specific
    journal_id = Column(Integer)
    is_private = Column(Boolean, default=False)
    
    # Code specific
    code_language = Column(String)
    function_name = Column(String)
    class_name = Column(String)
    line_start = Column(Integer)
    line_end = Column(Integer)
    
    # Document specific
    page_number = Column(Integer)
    
    # Wiki specific
    wiki_version = Column(Integer)
    section_index = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Embedding(Base):
    """Model đại diện cho embedding vector của một chunk.
    
    Embedding là vector representation của chunk text, được sử dụng cho
    vector similarity search. Mỗi chunk có một embedding tương ứng (one-to-one).
    
    Attributes:
        id: UUID primary key
        chunk_id: Foreign key đến Chunk (unique, one-to-one relationship)
        embedding: Vector embedding (pgvector Vector type, dimension 1024)
        model_name: Tên model embedding đã sử dụng
        quality_score: Điểm chất lượng của embedding (0-1)
        status: Trạng thái embedding (active, inactive, failed)
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "embedding"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunk.id", ondelete="CASCADE"), unique=True)
    embedding = Column(Vector(1024))
    model_name = Column(String, default="mixedbread-ai/mxbai-embed-large-v1")
    quality_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="active")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SearchLog(Base):
    """Model lưu log các tìm kiếm đã thực hiện.
    
    Model này track các search queries để analytics và debugging.
    Lưu trữ query, filters, top chunks, và response time.
    
    Attributes:
        id: UUID primary key
        user_id: ID của user thực hiện search (optional)
        query: Query text đã tìm kiếm
        filters: Filters đã áp dụng (JSONB)
        top_chunk_ids: Danh sách IDs của top chunks đã retrieve (Array of UUIDs)
        response_time_ms: Thời gian phản hồi tổng tính bằng milliseconds (bao gồm cả vector search và AI call)
        usage_log_id: Foreign key đến LLMUsageLog (optional, chỉ có khi có AI call)
        generation_time_ms: Thời gian generation AI tính bằng milliseconds (từ LLMUsageLog)
        created_at: Thời gian tạo log
    """
    __tablename__ = "search_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String)
    query = Column(String, nullable=False)
    filters = Column(JSONB)
    top_chunk_ids = Column(ARRAY(UUID(as_uuid=True)))
    response_time_ms = Column(Integer)
    usage_log_id = Column(UUID(as_uuid=True), ForeignKey("openai_usage_log.id", ondelete="SET NULL"), nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScheduledJob(Base):
    """Model đại diện cho một scheduled job (công việc đã lên lịch).
    
    Model này lưu trữ thông tin về các jobs được schedule để chạy định kỳ
    (ví dụ: sync Redmine, sync Git, check sources). Jobs được thực thi bởi scheduler.
    
    Attributes:
        id: UUID primary key
        job_name: Tên của job
        job_type: Loại job (redmine_sync, git_sync, source_check, chunk_embedding)
        cron_expression: Biểu thức cron để schedule job
        is_active: Trạng thái active (True = đang chạy, False = tạm dừng)
        config: Cấu hình job (JSONB, ví dụ: project_id, filters)
        last_run_at: Thời gian chạy cuối cùng
        next_run_at: Thời gian chạy tiếp theo (tính từ cron expression)
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "scheduled_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_name = Column(String, nullable=False)
    job_type = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    config = Column(JSONB)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class JobExecution(Base):
    """Model lưu log các lần thực thi scheduled job.
    
    Model này track mỗi lần một scheduled job được thực thi, bao gồm
    trạng thái, kết quả, và thông tin chi tiết.
    
    Attributes:
        id: UUID primary key
        job_id: Foreign key đến ScheduledJob
        started_at: Thời gian bắt đầu thực thi
        completed_at: Thời gian hoàn thành (None nếu chưa xong)
        status: Trạng thái execution (running, completed, failed, cancelled)
        items_processed: Số lượng items đã xử lý
        items_failed: Số lượng items thất bại
        error_message: Thông báo lỗi nếu có
        execution_log: Log chi tiết của execution (JSONB)
        created_at: Thời gian tạo
    """
    __tablename__ = "job_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_jobs.id", ondelete="CASCADE"))
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String, nullable=False)
    items_processed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    error_message = Column(Text)
    execution_log = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMUsageLog(Base):
    """Model lưu log việc sử dụng LLM API (OpenAI, Google, Anthropic, Groq)."""
    
    __tablename__ = "openai_usage_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False, default="openai")  # openai, google, anthropic, groq
    model = Column(String, nullable=False)
    input_token = Column(Integer, nullable=False, default=0)  # From API (e.g., prompt_token_count for Google)
    output_token = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    prompt_token = Column(Integer, nullable=True, default=0)  # Calculated: max(0, total_tokens - output_token)
    cost_usd = Column(Float, nullable=False, default=0.0)
    user_query = Column(Text)
    cached = Column(Boolean, default=False)
    response_time_ms = Column(Integer)
    extra_metadata = Column("metadata", JSONB)  # Keep legacy column name
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMUsageLogDetail(Base):
    """Model lưu chi tiết prompt và response cho LLM usage log."""
    
    __tablename__ = "openai_usage_log_detail"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usage_log_id = Column(UUID(as_uuid=True), ForeignKey("openai_usage_log.id", ondelete="CASCADE"), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMConfig(Base):
    """Model lưu cấu hình pricing và thông tin kết nối cho các LLM providers."""
    
    __tablename__ = "openai_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False, default="openai")  # openai, google, anthropic, groq
    model_name = Column(String, nullable=False, unique=True)
    input_price_per_1m = Column(Float, nullable=False)
    output_price_per_1m = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    description = Column(Text)
    api_key = Column(Text)  # optional per-provider override
    base_url = Column(String)  # optional custom endpoint (Groq, Together, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Backward compatible aliases
OpenAIUsageLog = LLMUsageLog
OpenAIUsageLogDetail = LLMUsageLogDetail
OpenAIConfig = LLMConfig


class User(Base):
    """Model đại diện cho người dùng trong hệ thống.
    
    Model này lưu trữ thông tin tài khoản người dùng, bao gồm credentials,
    thông tin cá nhân, và quyền hạn. Được sử dụng cho authentication và authorization.
    
    Attributes:
        id: UUID primary key
        username: Tên đăng nhập (unique, required)
        email: Email (unique, optional)
        hashed_password: Mật khẩu đã được hash bằng bcrypt (required)
        full_name: Tên đầy đủ (optional)
        is_active: Trạng thái active (True = có thể đăng nhập, False = bị vô hiệu hóa)
        is_admin: Có phải admin không (True = có quyền admin)
        created_at: Thời gian tạo tài khoản
        updated_at: Thời gian cập nhật
        last_login: Thời gian đăng nhập cuối cùng
    """
    __tablename__ = "account"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))


class BudgetConfig(Base):
    """Model lưu cấu hình budget cho từng provider.
    
    Model này lưu trữ cấu hình budget cho việc theo dõi chi phí LLM usage
    theo từng provider (OpenAI, Google, Anthropic, Groq). Budget được tính
    theo billing cycle (từ invoice_day đến invoice_day của tháng tiếp theo).
    
    Attributes:
        id: UUID primary key
        provider: Provider name (openai, google, anthropic, groq)
        budget_amount_usd: Số tiền budget tính bằng USD (float)
        invoice_day: Ngày invoice trong tháng (1-31)
        alert_thresholds: JSONB chứa các ngưỡng cảnh báo (ví dụ: [50, 80, 100])
        is_active: Budget có đang active không (Boolean)
        created_at: Thời gian tạo
        updated_at: Thời gian cập nhật
    """
    __tablename__ = "budget_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)  # openai, google, anthropic, groq
    budget_amount_usd = Column(Float, nullable=False)
    invoice_day = Column(Integer, nullable=False)  # 1-31
    alert_thresholds = Column(JSONB, nullable=False)  # [50, 80, 100]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BudgetAlert(Base):
    """Model lưu lịch sử cảnh báo budget.
    
    Model này lưu trữ các cảnh báo đã được gửi khi budget vượt quá ngưỡng
    đã thiết lập. Mỗi alert được gửi một lần cho mỗi threshold trong mỗi billing cycle.
    
    Attributes:
        id: UUID primary key
        budget_config_id: Foreign key đến BudgetConfig
        provider: Provider name (để query nhanh)
        billing_cycle_start: Ngày bắt đầu billing cycle
        billing_cycle_end: Ngày kết thúc billing cycle
        threshold_percentage: Ngưỡng đã trigger (int, ví dụ: 50)
        current_spending_usd: Chi phí hiện tại khi trigger
        budget_amount_usd: Budget amount tại thời điểm trigger
        alert_type: Loại alert (threshold_reached, budget_exceeded)
        alert_channels: JSONB chứa các kênh đã gửi (in_app, email, etc.)
        sent_at: Thời gian gửi alert
        acknowledged_at: Thời gian user acknowledge (optional)
        created_at: Timestamp
    """
    __tablename__ = "budget_alert"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_config_id = Column(UUID(as_uuid=True), ForeignKey("budget_config.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)  # openai, google, anthropic, groq
    billing_cycle_start = Column(DateTime(timezone=True), nullable=False)
    billing_cycle_end = Column(DateTime(timezone=True), nullable=False)
    threshold_percentage = Column(Integer, nullable=False)  # 50, 80, 100
    current_spending_usd = Column(Float, nullable=False)
    budget_amount_usd = Column(Float, nullable=False)
    alert_type = Column(String, nullable=False)  # threshold_reached, budget_exceeded
    alert_channels = Column(JSONB, nullable=False)  # ["in_app", "email"]
    sent_at = Column(DateTime(timezone=True), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())