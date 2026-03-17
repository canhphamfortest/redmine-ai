# Custom Features Plugin for Redmine

Plugin tùy chỉnh cho Redmine với các tính năng AI-powered:

1. **AI-Powered Checklist Generation**: Tự động tạo checklist cho issue sử dụng AI Agent
2. **AI-Powered Related Issues Finder**: Tìm issues liên quan sử dụng RAG (Retrieval-Augmented Generation)
3. **RAG Search**: Tìm kiếm thông minh với AI Agent để trả lời câu hỏi dựa trên dữ liệu đã ingest
4. **Auto Link Related Issues**: Tự động liên kết các issues liên quan được phát hiện bởi AI

## Cài đặt

1. Đảm bảo plugin đã được mount trong `docker-compose.yml`:

   ```yaml
   volumes:
     - ./plugins:/usr/src/redmine/plugins
   ```

2. Khởi động lại Redmine container:

   ```bash
   docker compose restart redmine
   ```

3. Plugin sẽ tự động được nhận diện và kích hoạt.

## Sử dụng

### 🤖 AI-Powered Checklist Generation

**Tính năng**: Tự động tạo checklist cho issue sử dụng AI Agent phân tích nội dung issue.

- Button **"Create Note with Checklist"** xuất hiện ngay dưới phần **Related Issues** (trong div `#relations`)
- Button được tự động chèn vào sau form "Add relation" bằng JavaScript
- **Cách hoạt động**:

  1. AI Agent phân tích nội dung issue (subject, description, notes, custom fields, tracker, status, priority)
  2. Tạo checklist phù hợp với nội dung issue (5-10 tasks)
  3. Tự động tạo journal entry (note) với checklist đã được format
  4. Nếu AI không tạo được hoặc parse thất bại, hệ thống sẽ báo lỗi và không tạo note
- Checklist được format theo Markdown (`- [ ] task`) tương thích với Redmine
- Sau khi tạo, bạn có thể chỉnh sửa và submit note như bình thường

### 🔗 AI-Powered Related Issues Finder

**Tính năng**: Tìm issues liên quan sử dụng AI Agent với RAG (Retrieval-Augmented Generation).

- Button **"Auto Link Related Issues"** xuất hiện trong phần Relations
- **Cách hoạt động**:
  1. AI Agent phân tích sâu nội dung issue hiện tại
  2. Sử dụng RAG để tìm các issues có liên quan về mặt ngữ nghĩa
  3. Hiển thị dialog với danh sách issues liên quan kèm similarity score
  4. Cho phép xác nhận để tự động liên kết các issues
- Chỉ hiển thị issues trong cùng project và có quyền truy cập
- Tự động loại trừ các issues đã có quan hệ

### 🔍 RAG Search (AI Agent Search)

**Tính năng**: Tìm kiếm thông minh với AI Agent để trả lời câu hỏi dựa trên dữ liệu đã ingest.

- **Custom Search Box**: Xuất hiện tự động bên cạnh phần "Search" (quick-search) trong header
- **Menu Custom Search**: Truy cập menu "Custom Search" ở top menu để vào trang search đầy đủ
- **Cách hoạt động**:

  1. Nhập câu hỏi hoặc từ khóa tìm kiếm
  2. AI Agent sử dụng RAG để tìm thông tin liên quan trong database
  3. Trả về câu trả lời tổng hợp cùng với các nguồn tham khảo (sources)
  4. Hiển thị các chunks được retrieve với similarity score
- Tự động lấy project context từ URL nếu đang ở trong project
- Hỗ trợ tìm kiếm trong Issues, Projects, Wiki pages, và các tài liệu đã ingest

## Cấu trúc Plugin

```text
custom_features/
├── init.rb                          # Plugin initialization và dependency loading
├── lib/
│   └── custom_features/
│       ├── hooks.rb                 # View hooks để inject UI
│       ├── search_client.rb          # HTTP client để gọi AI backend API
│       ├── config.rb                 # Configuration management
│       ├── constants.rb              # Constants và configuration values
│       ├── errors.rb                 # Custom error classes
│       ├── services/                 # Business logic services
│       │   ├── checklist_generator.rb    # AI-powered checklist generation
│       │   ├── checklist_parser.rb       # Parse checklist từ AI response
│       │   ├── issue_content_builder.rb  # Build issue content cho AI
│       │   └── related_issues_finder.rb # Find related issues với AI
│       └── formatters/              # Data formatters
│           ├── issue_formatter.rb        # Format issue data
│           └── search_result_formatter.rb # Format search results
├── app/
│   ├── controllers/
│   │   ├── custom_features/
│   │   │   └── custom_features_controller.rb  # Checklist và related issues
│   │   └── custom_search_controller.rb        # RAG search
│   └── views/
│       ├── custom_features/
│       │   └── hooks/               # Hook partials
│       └── custom_search/           # Search views
├── assets/
│   ├── stylesheets/
│   │   └── custom_features.css      # Plugin styles
│   └── javascripts/
│       └── custom_features/
│           ├── main.js              # Entry point
│           ├── utils.js             # Utility functions
│           ├── checklist.js         # Checklist functionality
│           ├── search.js            # Search functionality
│           └── auto_link.js        # Auto-link related issues
└── config/
    └── routes.rb                    # Plugin routes
```

## Configuration

### AI Backend URL

Plugin cần kết nối đến AI backend service. Cấu hình URL qua một trong các cách sau:

1. **Plugin Settings** (ưu tiên cao nhất):

   - Vào `Administration > Plugins > Custom Features Plugin`
   - Set `RAG API Base URL` (ví dụ: `http://backend:8000`)

2. **Environment Variables**:

   ```bash
   RAG_SEARCH_API_BASE=http://backend:8000
   # hoặc
   RAG_BACKEND_URL=http://backend:8000
   ```

3. **Default**: `http://backend:8000` (nếu không set)

### API Endpoints

Plugin gọi các endpoints sau từ AI backend:

- `POST /api/search/rag` - RAG search
- `GET /api/search/issues/:issue_id/related?top_k=20` - Find related issues

## Tùy chỉnh

Bạn có thể tùy chỉnh:

- **Prompts cho AI**: Sửa constants trong `lib/custom_features/constants.rb`
- **Styling**: Sửa `assets/stylesheets/custom_features.css`
- **JavaScript behavior**: Sửa các file trong `assets/javascripts/custom_features/`
- **Business logic**: Sửa các services trong `lib/custom_features/services/`
- **UI components**: Sửa views trong `app/views/`

## Requirements

- **Redmine**: 5.1.2+
- **Ruby on Rails**: (included in Redmine)
- **AI Backend Service**: Python FastAPI service với RAG capabilities

  - Endpoint: `/api/search/rag` cho RAG search
  - Endpoint: `/api/search/issues/:id/related` cho related issues
  - Response format: JSON với structure như trong code

## License

MIT License
