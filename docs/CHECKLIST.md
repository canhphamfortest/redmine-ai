# Code Review Checklist

Checklist này được CodeRabbit sử dụng làm coding guideline khi review PR.
Áp dụng cho toàn bộ project: **redmine-data** (Python/FastAPI) và **redmine-assistant** (Ruby/Redmine Plugin).

---

## 🐍 Python Backend (redmine-data)

### General
- [ ] Không có credentials, API keys, hoặc secrets được hardcode trong code
- [ ] Tất cả environment variables được đọc từ `settings` / `.env`, không dùng `os.environ.get` trực tiếp tùy tiện
- [ ] File mới phải có docstring mô tả mục đích của module ở đầu file
- [ ] Import được sắp xếp đúng thứ tự: stdlib → third-party → local

### Error Handling
- [ ] Mọi exception đều được catch và log bằng `logger.error(...)` hoặc `logger.warning(...)`
- [ ] Không dùng bare `except:` — phải chỉ định exception class cụ thể
- [ ] Lỗi từ external services (OpenAI, Redmine, DB) phải được wrap thành lỗi ứng dụng
- [ ] Hàm phải trả về giá trị mặc định an toàn khi gặp lỗi (không để crash toàn bộ request)

### FastAPI / API Layer
- [ ] Router đăng ký đúng HTTP method (`GET`, `POST`, `PUT`, `DELETE`)
- [ ] Pydantic schema có đầy đủ type hint và field validation
- [ ] HTTP status codes trả về đúng ngữ nghĩa (200, 201, 400, 401, 403, 404, 500)
- [ ] Error response nhất quán: `{"detail": "message"}`
- [ ] Authentication được enforce tại mọi endpoint cần bảo vệ
- [ ] Không business logic nằm trong router handler — delegate xuống handler/service

### Database
- [ ] SQLAlchemy session được inject qua dependency, không tạo thủ công trong service
- [ ] Session được đóng đúng cách sau mỗi request (FastAPI dependency tự xử lý)
- [ ] Tránh N+1 queries: dùng `joinedload` / `selectinload` khi cần
- [ ] Không raw SQL string concatenation — dùng parameterized queries hoặc ORM
- [ ] Migration scripts (`.sql`) có thể rollback an toàn

### RAG / AI Services
- [ ] Mọi LLM call đều được log vào `OpenAIUsageLog` (token count, provider, model)
- [ ] Cache key được generate nhất quán (normalized query)
- [ ] Error response từ LLM **không** được cache
- [ ] Prompt không vượt quá `max_tokens` của model đang dùng
- [ ] Provider được load dynamic từ DB config, không hardcode `"openai"`

### Embedding & Vector
- [ ] Embedding dimension nhất quán với schema của vector DB
- [ ] Empty text → trả về zero vector, không raise exception
- [ ] Batch size hợp lý để tránh OOM (`batch_size=32` là mặc định an toàn)
- [ ] Chunk metadata (issue_id, project_id, source_type) được gắn đầy đủ vào mỗi chunk

### Chunker
- [ ] Chunk size không vượt quá token limit của embedding model
- [ ] Overlap giữa các chunks đủ để preserve context (thường 10-20% chunk size)
- [ ] Chunks rỗng hoặc quá ngắn phải được lọc trước khi embed

### Streamlit UI
- [ ] Không hardcode URL hay credentials trong UI code
- [ ] `st.session_state` không chứa data nhạy cảm persist giữa sessions
- [ ] Mọi API call có try/except và hiển thị error message thân thiện
- [ ] Không expose stack trace trực tiếp ra UI

---

## 💎 Ruby Plugin (redmine-assistant)

### General
- [ ] Không hardcode strings — dùng constants từ `constants.rb`
- [ ] Không hardcode URLs của AI service — lấy từ plugin settings
- [ ] File mới phải có comment mô tả mục đích của class/module

### Authorization & Security
- [ ] Controller phải có `before_action :require_login` và kiểm tra quyền truy cập issue
- [ ] Output trong views phải được escape: dùng `h()`, `sanitize()`, hoặc ERB auto-escape
- [ ] Không dùng `innerHTML` trong JS với dữ liệu từ server — dùng `textContent`
- [ ] Mọi AJAX POST/PATCH/DELETE phải gửi kèm CSRF token (`X-CSRF-Token`)
- [ ] Không log sensitive data (token, password, API key) vào Rails logger

### Controllers
- [ ] `before_action` filter chạy trước mọi action (authenticate + authorize)
- [ ] JSON response cho API endpoints, HTML response cho web endpoints
- [ ] Không đặt business logic trong controller — delegate xuống Service class
- [ ] Rescue lỗi và respond với HTTP status code phù hợp

### Services
- [ ] Mỗi Service class có **single responsibility**
- [ ] Log prefix nhất quán: `[ClassName] message` cho mọi log entry
- [ ] Rescue exception cụ thể (`SearchError`, `StandardError`), không dùng bare `rescue`
- [ ] Trả về `[]` hoặc `nil` khi lỗi thay vì raise lên controller (trừ trường hợp cần báo lỗi lên)
- [ ] `SearchClient` được inject vào constructor (không hardcode singleton gọi trực tiếp trong logic)

### ChecklistGenerator
- [ ] Prompt được build từ `IssueContentBuilder`, không concatenate string thủ công
- [ ] AI response được parse qua `ChecklistParser`, không parse bằng regex inline
- [ ] Checklist rỗng sau parse → raise `ChecklistGenerationError`, không dùng fallback silently
- [ ] Độ dài description/notes trong prompt bị truncate theo `ISSUE_DESCRIPTION_MAX_LENGTH`

### RelatedIssuesFinder
- [ ] Lọc bỏ issue hiện tại và issues đã có relation trước khi hiển thị
- [ ] Chỉ hiển thị issues trong **cùng project** với issue hiện tại
- [ ] Similarity score được normalize về 0-1 trước khi hiển thị
- [ ] Số lượng kết quả tối đa tuân theo `RELATED_ISSUES_MAX_RESULTS`

### JavaScript
- [ ] Không dùng `var` — dùng `const` / `let`
- [ ] Không global variable pollution — wrap trong IIFE hoặc module pattern
- [ ] Loading state phải được hiển thị trong khi chờ API response
- [ ] Error từ API phải được hiển thị cho user (không silent fail)

---

## 🐳 Infrastructure & Config

### Docker / Docker Compose
- [ ] Không hardcode credentials trong `docker-compose.yml` — dùng `${ENV_VAR}`
- [ ] `.env.example` phải được cập nhật khi thêm biến môi trường mới
- [ ] Services quan trọng (backend, DB) nên có `healthcheck` định nghĩa
- [ ] Volume mounts đúng path, data persistence được đảm bảo

### SQL Scripts
- [ ] Không có SQL injection risk (dùng parameterized queries)
- [ ] Migration có thể rollback (cung cấp `DROP`/`ALTER` tương ứng)
- [ ] Index được tạo cho các columns thường xuyên dùng trong `WHERE` / `JOIN`

### Environment Variables
- [ ] File `.env` thực **không bao giờ** được commit vào git
- [ ] Chỉ commit `.env.example` với placeholder values (e.g., `OPENAI_API_KEY=your_key_here`)
- [ ] Biến mới phải được thêm vào cả `.env.example` và tài liệu

---

## 📋 PR Checklist (tự check trước khi tạo PR)

- [ ] Code đã được test locally (unit test hoặc manual test)
- [ ] Không có debug code (`print`, `console.log`, `binding.pry`, `debugger`) còn sót
- [ ] Không có commented-out code không cần thiết
- [ ] PR description mô tả rõ **what** và **why** của thay đổi
- [ ] Breaking changes được ghi chú rõ trong PR description
- [ ] Database migrations (nếu có) đã được test rollback
- [ ] `.env.example` đã được cập nhật nếu thêm env vars mới
- [ ] `CHANGELOG.md` đã được cập nhật nếu là feature/bugfix đáng kể
