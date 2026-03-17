# Code Review Checklist

Checklist này được CodeRabbit sử dụng làm coding guideline khi review PR.
Áp dụng cho toàn bộ project: **redmine-data** (Python/FastAPI) và **redmine-assistant** (Ruby/Redmine Plugin).

---

## Python Backend (redmine-data)

### General

- [ ] Không có credentials, API keys, hoặc secrets được hardcode trong code
- [ ] Tất cả environment variables được đọc qua `settings` object từ `app/config.py`, không gọi `os.environ.get` trực tiếp tùy tiện
- [ ] File mới phải có docstring mô tả mục đích của module ở đầu file
- [ ] Import được sắp xếp đúng thứ tự: stdlib → third-party → local
- [ ] Không có `print()` statement trong production code — dùng `logger` thay thế
- [ ] Không có debug code còn sót (`breakpoint()`, `pdb`, `ipdb`)

### Error Handling

- [ ] Mọi exception đều được catch và log bằng `logger.error(...)` hoặc `logger.warning(...)`
- [ ] Không dùng bare `except:` — phải chỉ định exception class cụ thể (e.g., `except Exception as e`)
- [ ] Lỗi từ external services (OpenAI, Redmine API, PostgreSQL, Redis) phải được wrap thành application error rõ ràng
- [ ] Hàm phải trả về giá trị mặc định an toàn khi gặp lỗi (không để crash toàn bộ request)
- [ ] Không expose stack trace hay internal error message trực tiếp ra API response

### FastAPI / API Layer

- [ ] Router đăng ký đúng HTTP method (`GET`, `POST`, `PUT`, `DELETE`)
- [ ] Pydantic schema có đầy đủ type hint và field validation (kể cả `Optional`, `Field(...)` với constraints)
- [ ] HTTP status codes trả về đúng ngữ nghĩa: `200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `500 Internal Server Error`
- [ ] Error response nhất quán theo format: `{"detail": "message"}`
- [ ] Authentication được enforce tại mọi endpoint cần bảo vệ (dependency `get_current_user`)
- [ ] Không để business logic nằm trong router handler — phải delegate xuống handler/service layer
- [ ] Response schema (Pydantic) khớp với dữ liệu thực tế trả về
- [ ] Endpoint mới phải được đăng ký trong router tương ứng và include vào `app/main.py`

### Database

- [ ] SQLAlchemy session được inject qua FastAPI dependency (`Depends(get_db)`), không tạo session thủ công trong service
- [ ] Session được đóng đúng cách sau mỗi request (FastAPI dependency generator tự xử lý)
- [ ] Tránh N+1 queries: dùng `joinedload` / `selectinload` khi truy vấn quan hệ
- [ ] Không dùng raw SQL string concatenation — dùng parameterized queries hoặc ORM expressions
- [ ] Migration scripts (`.sql`) phải có thể rollback an toàn (kèm `DROP`/`ALTER` tương ứng)
- [ ] Index được tạo cho các columns thường xuyên dùng trong `WHERE` / `JOIN` / `ORDER BY`
- [ ] Vector columns (`VECTOR(1024)`) phải có HNSW hoặc IVFFlat index để tối ưu similarity search

### RAG / AI Services

- [ ] Mọi LLM call đều được log vào bảng `OpenAIUsageLog` (token count, provider, model, cost)
- [ ] Cache key được generate nhất quán (normalized query — lowercase, stripped whitespace)
- [ ] Error response từ LLM **không** được cache vào Redis
- [ ] Prompt không vượt quá `max_tokens` của model đang dùng
- [ ] LLM provider được load dynamic từ DB config (`LLMConfig` table), không hardcode `"openai"` hay model name
- [ ] Kết quả tìm kiếm trống (empty results) cache với TTL ngắn hơn (1 giờ), kết quả hợp lệ cache 24 giờ
- [ ] Timing metrics được ghi lại cho từng bước trong RAG pipeline (embed, retrieve, generate)

### Embedding & Vector

- [ ] Embedding dimension (1024) nhất quán với schema của vector DB (`VECTOR(1024)`)
- [ ] Empty text hoặc text quá ngắn → trả về zero vector hoặc skip, không raise exception
- [ ] Batch size hợp lý để tránh OOM (`batch_size=32` là mặc định an toàn cho model `mxbai-embed-large-v1`)
- [ ] Chunk metadata đầy đủ: `issue_id`, `project_id`, `source_type`, `chunk_index`, `content_hash`
- [ ] Không embed lại chunk nếu `content_hash` không thay đổi (idempotent embedding)

### Chunker

- [ ] Chunk size không vượt quá token limit của embedding model
- [ ] Overlap giữa các chunks đủ để preserve context (thường 10-20% chunk size)
- [ ] Chunks rỗng hoặc quá ngắn (< 50 ký tự) phải được lọc trước khi embed
- [ ] Mỗi loại content có strategy chunker phù hợp: `IssueChunker`, `WikiChunker`, `CodeChunker`, `TextChunker`
- [ ] Chunker mới phải kế thừa base class và implement đúng interface

### Data Ingestion & Sync

- [ ] Redmine sync sử dụng rate limiting (`REDMINE_API_DELAY=0.2s`) để tránh overload API
- [ ] Incremental sync chỉ xử lý records đã thay đổi (dựa vào `updated_on` timestamp)
- [ ] File attachments được extract text trước khi embed (PDF/DOCX/TXT qua `ExtractorService`)
- [ ] Git sync xử lý đúng encoding (UTF-8 fallback) cho file code
- [ ] Manual upload validate file type và size trước khi xử lý
- [ ] Resync handler xóa embeddings cũ trước khi tạo lại (tránh duplicate vectors)

### Job Scheduling

- [ ] Job mới phải được đăng ký trong `job_scheduler.py` với cron expression rõ ràng
- [ ] Job execution log đầy đủ: start time, end time, status, error message nếu có
- [ ] Job timeout phải được set để tránh job treo vô thời hạn
- [ ] Scheduler service nhẹ (~200MB) chỉ trigger job, không thực thi heavy work trực tiếp

### Budget & Cost Tracking

- [ ] Mọi LLM call đều tính cost theo bảng giá trong `pricing.py` (input/output tokens riêng biệt)
- [ ] Budget alert được gửi email khi vượt ngưỡng (thông qua SMTP/AWS SES)
- [ ] Budget check chạy định kỳ qua scheduler, không chỉ on-demand
- [ ] Email recipients đọc từ env var `BUDGET_ALERT_EMAIL_RECIPIENTS`, không hardcode

### Streamlit UI

- [ ] Không hardcode URL hay credentials trong UI code — đọc từ environment hoặc `st.secrets`
- [ ] `st.session_state` không chứa data nhạy cảm persist giữa sessions
- [ ] Mọi API call có try/except và hiển thị error message thân thiện cho user
- [ ] Không expose stack trace trực tiếp ra UI
- [ ] Login state được kiểm tra trước khi render trang (redirect nếu chưa đăng nhập)

---

## Ruby Plugin (redmine-assistant)

### General

- [ ] Không hardcode strings — dùng constants từ `lib/custom_features/constants.rb`
- [ ] Không hardcode URLs của AI service — lấy từ plugin settings hoặc environment variable
- [ ] File mới phải có comment mô tả mục đích của class/module
- [ ] Không có `puts` hay `p` statement trong production code — dùng `Rails.logger`
- [ ] Không có `binding.pry` hay debug breakpoints còn sót

### Authorization & Security

- [ ] Controller phải có `before_action :require_login` bảo vệ mọi action
- [ ] Kiểm tra quyền truy cập issue (`issue.visible?`) trước khi xử lý
- [ ] Output trong views phải được escape: dùng `h()`, `sanitize()`, hoặc ERB auto-escape `<%= %>`
- [ ] Không dùng `innerHTML` trong JS với dữ liệu từ server — dùng `textContent` hoặc tạo DOM element
- [ ] Mọi AJAX POST/PATCH/DELETE phải gửi kèm CSRF token (`X-CSRF-Token` header)
- [ ] Không log sensitive data (token, password, API key) vào Rails logger

### Controllers

- [ ] `before_action` filter chạy trước mọi action (authenticate + authorize)
- [ ] API endpoints trả về JSON response, web endpoints trả về HTML
- [ ] Không đặt business logic trong controller — delegate xuống Service class
- [ ] Rescue lỗi và respond với HTTP status code phù hợp (`render json: ..., status: :unprocessable_entity`)
- [ ] Controller mới phải được đăng ký trong `config/routes.rb`

### Services

- [ ] Mỗi Service class có **single responsibility** (một class, một nhiệm vụ)
- [ ] Log prefix nhất quán: `[ClassName] message` cho mọi log entry
- [ ] Rescue exception cụ thể (`SearchError`, `StandardError`), không dùng bare `rescue`
- [ ] Trả về `[]` hoặc `nil` khi lỗi thay vì raise lên controller (trừ trường hợp cần thông báo lỗi cho user)
- [ ] `SearchClient` được dùng qua singleton (`SearchClient.instance`) hoặc inject vào constructor — không tạo instance mới trong mỗi method call

### SearchClient (HTTP Client)

- [ ] Timeout phải được set cho mọi HTTP request (default: 360 giây cho RAG, 30 giây cho các call khác)
- [ ] Base URL được đọc dynamic từ settings mỗi request (không cache URL để hỗ trợ config thay đổi không cần restart)
- [ ] HTTP error codes (4xx, 5xx) phải được handle và log rõ ràng
- [ ] JSON parse error được catch và log, trả về giá trị mặc định an toàn
- [ ] Không hardcode endpoint paths — dùng constants từ `constants.rb`

### ChecklistGenerator

- [ ] Prompt được build từ `IssueContentBuilder`, không concatenate string thủ công
- [ ] AI response được parse qua `ChecklistParser`, không parse bằng regex inline trong generator
- [ ] Checklist rỗng sau parse → raise `ChecklistGenerationError`, không dùng fallback silently
- [ ] Độ dài description/notes trong prompt phải bị truncate theo `ISSUE_DESCRIPTION_MAX_LENGTH`
- [ ] Journal entry được tạo trong transaction để tránh partial save

### RelatedIssuesFinder

- [ ] Lọc bỏ issue hiện tại và issues đã có relation trước khi hiển thị
- [ ] Chỉ hiển thị issues trong **cùng project** với issue hiện tại
- [ ] Similarity score được normalize về range 0-1 trước khi hiển thị
- [ ] Số lượng kết quả tối đa tuân theo `RELATED_ISSUES_MAX_RESULTS` (default: 20 từ API, filter xuống trước khi trả về)
- [ ] Chỉ hiển thị issues mà user hiện tại có quyền xem (`issue.visible?`)

### Hooks

- [ ] Hook mới phải được đăng ký trong `ViewHooks` class trong `hooks.rb`
- [ ] Hook partial phải nằm đúng trong thư mục `app/views/custom_features/hooks/`
- [ ] Asset (CSS/JS) phải được load qua hook `view_layouts_base_html_head`, không inline trong partial

### JavaScript

- [ ] Không dùng `var` — dùng `const` / `let`
- [ ] Không global variable pollution — wrap trong IIFE hoặc module pattern
- [ ] Loading state phải được hiển thị trong khi chờ API response (spinner hoặc disabled button)
- [ ] Error từ API phải được hiển thị cho user (không silent fail)
- [ ] Không dùng `innerHTML` với dữ liệu từ server — tránh XSS
- [ ] AJAX request phải kèm CSRF token: đọc từ `document.querySelector('meta[name="csrf-token"]')`
- [ ] Kiểm tra element tồn tại trong DOM trước khi thao tác (tránh null reference error)
- [ ] Idempotent DOM insertion — kiểm tra đã tồn tại trước khi chèn (tránh duplicate elements)

---

## Infrastructure & Config

### Docker / Docker Compose

- [ ] Không hardcode credentials trong `docker-compose.yml` — dùng `${ENV_VAR}` với fallback nếu cần
- [ ] `.env.example` phải được cập nhật khi thêm biến môi trường mới (kèm comment mô tả)
- [ ] Services quan trọng (`postgres`, `redis`) phải có `healthcheck` định nghĩa
- [ ] Service `backend` phải `depends_on` với `condition: service_healthy` cho `postgres` và `redis`
- [ ] Volume mounts đúng path, data persistence được đảm bảo cho `postgres_data`, `redis_data`
- [ ] Không commit file `.env` thực vào git — chỉ commit `.env.example`
- [ ] `rag-network` là external network dùng chung cho cả `redmine-data` và `redmine-assistant`

### SQL Scripts

- [ ] Không có SQL injection risk (dùng parameterized queries)
- [ ] Migration script idempotent — có thể chạy lại mà không gây lỗi (dùng `CREATE IF NOT EXISTS`, `ALTER ... IF NOT EXISTS`)
- [ ] Migration có thể rollback (cung cấp `DROP`/`ALTER` tương ứng hoặc comment hướng dẫn rollback)
- [ ] pgvector extension phải được enable trước khi tạo bảng có `VECTOR` column: `CREATE EXTENSION IF NOT EXISTS vector`
- [ ] HNSW index cho vector search: `USING hnsw (embedding vector_cosine_ops)`

### Environment Variables

- [ ] File `.env` thực **không bao giờ** được commit vào git (đã có trong `.gitignore`)
- [ ] Chỉ commit `.env.example` với placeholder values (e.g., `OPENAI_API_KEY=your_key_here`)
- [ ] Biến mới phải được thêm vào cả `.env.example` lẫn tài liệu liên quan
- [ ] Biến sensitive (API keys, passwords) không được có default value trong code
- [ ] `DEBUG=false` trong production — `DEBUG=true` gây verbose SQL logging (~500MB/ngày)

### Logging

- [ ] Log level phù hợp: `DEBUG` cho development, `INFO` hoặc `WARNING` cho production
- [ ] Log rotation được cấu hình (tránh disk full do log quá lớn)
- [ ] Không log sensitive data: API keys, passwords, user tokens
- [ ] Structured logging với timestamp, level, module name cho dễ trace

---

## PR Checklist (tự check trước khi tạo PR)

- [ ] Code đã được test locally (unit test hoặc manual test với các case cơ bản)
- [ ] Không có debug code còn sót (`print`, `console.log`, `binding.pry`, `debugger`, `breakpoint()`)
- [ ] Không có commented-out code không cần thiết
- [ ] PR description mô tả rõ **what** (thay đổi gì) và **why** (tại sao cần thay đổi)
- [ ] Breaking changes được ghi chú rõ trong PR description
- [ ] Database migrations (nếu có) đã được test rollback
- [ ] `.env.example` đã được cập nhật nếu thêm env vars mới
- [ ] `CHANGELOG.md` đã được cập nhật nếu là feature/bugfix đáng kể
- [ ] Không có file tạm, log file, hay output file bị commit nhầm
- [ ] Thay đổi ảnh hưởng đến API contract (request/response schema) phải được thông báo cho team frontend/plugin

---

## Integration Checklist (khi thêm tính năng liên quan đến cả 2 hệ thống)

_Áp dụng khi thay đổi có ảnh hưởng đến giao tiếp giữa `redmine-assistant` (Ruby plugin) và `redmine-data` (FastAPI backend)._

- [ ] API endpoint mới trong backend đã được document (FastAPI auto-docs tại `/docs`)
- [ ] Request/response JSON schema khớp giữa `SearchClient` (Ruby) và FastAPI router (Python)
- [ ] Timeout phía Ruby client phù hợp với thời gian xử lý phía Python backend
- [ ] Lỗi từ backend (4xx, 5xx) được handle gracefully phía plugin (không crash Redmine UI)
- [ ] Thay đổi URL endpoint phải update cả `constants.rb` (Ruby) và routing (Python) đồng thời
- [ ] Cả hai service đều trong cùng Docker network (`rag-network`) khi chạy production
