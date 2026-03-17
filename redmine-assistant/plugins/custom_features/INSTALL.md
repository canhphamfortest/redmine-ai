# Hướng dẫn cài đặt Custom Features Plugin

## Yêu cầu
- **Redmine**: 5.1.2+
- **Docker và Docker Compose**: Để chạy Redmine
- **AI Backend Service**: Python FastAPI service với RAG capabilities
  - Service phải accessible từ Redmine container
  - Default URL: `http://backend:8000` (có thể cấu hình)

## Cài đặt

### Bước 1: Kiểm tra docker-compose.yml
Đảm bảo rằng `docker-compose.yml` đã có volume mount cho plugins:
```yaml
volumes:
  - ./plugins:/usr/src/redmine/plugins
```

### Bước 2: Khởi động lại Redmine
```bash
docker compose restart redmine
```

### Bước 3: Cấu hình AI Backend URL (nếu cần)

Nếu AI backend không ở `http://backend:8000`, cấu hình URL:

**Cách 1: Plugin Settings** (khuyến nghị)
1. Vào `Administration > Plugins > Custom Features Plugin`
2. Set `RAG API Base URL` (ví dụ: `http://your-backend:8000`)

**Cách 2: Environment Variables**
Thêm vào `docker-compose.yml`:
```yaml
environment:
  - RAG_SEARCH_API_BASE=http://your-backend:8000
```

### Bước 4: Kiểm tra plugin đã được load
Truy cập: `http://localhost:8080/admin/plugins`
Bạn sẽ thấy "Custom Features Plugin" trong danh sách plugins.

### Bước 5: Kiểm tra tính năng

#### 🤖 AI-Powered Checklist Generation
1. Mở một Issue bất kỳ
2. Cuộn xuống phần "Related issues"
3. Click button **"Create Note with Checklist"**
4. AI Agent sẽ phân tích issue và tạo checklist tự động
5. Checklist sẽ được thêm vào notes section

#### 🔗 AI-Powered Related Issues Finder
1. Trong trang Issue, tìm button **"Auto Link Related Issues"** trong phần Relations
2. Click button
3. AI Agent sẽ phân tích và hiển thị dialog với các issues liên quan
4. Xem similarity scores và xác nhận để liên kết

#### 🔍 RAG Search (AI Agent Search)
1. Click vào menu "Custom Search" ở top menu
2. Nhập câu hỏi (ví dụ: "Hướng dẫn deploy RAG")
3. AI Agent sẽ tìm kiếm và trả lời dựa trên dữ liệu đã ingest
4. Xem câu trả lời cùng với sources và retrieved chunks

## Troubleshooting

### Plugin không xuất hiện
- Kiểm tra file `init.rb` có syntax error không
- Kiểm tra logs: `docker compose logs redmine`
- Đảm bảo thư mục plugin được mount đúng
- Kiểm tra Redmine version (yêu cầu 5.1.2+)

### Hooks không hoạt động
- Kiểm tra file `lib/custom_features/hooks.rb`
- Kiểm tra partials trong `app/views/custom_features/hooks/`
- Xem logs để biết lỗi cụ thể
- Đảm bảo assets được load (check browser console)

### AI Features không hoạt động
- **Checklist Generation thất bại**:
  - Kiểm tra AI backend có accessible không
  - Kiểm tra URL configuration trong plugin settings
  - Xem logs: `docker compose logs redmine | grep ChecklistGenerator`
  - Plugin sẽ báo lỗi và không tạo note nếu AI không tạo được checklist
  
- **Related Issues không tìm được**:
  - Kiểm tra AI backend endpoint `/api/search/issues/:id/related`
  - Kiểm tra logs: `docker compose logs redmine | grep RelatedIssuesFinder`
  - Đảm bảo có dữ liệu trong vector database
  
- **RAG Search không hoạt động**:
  - Kiểm tra AI backend endpoint `/api/search/rag`
  - Kiểm tra logs: `docker compose logs redmine | grep SearchClient`
  - Đảm bảo dữ liệu đã được ingest vào vector database

### Custom Search không hoạt động
- Kiểm tra routes trong `config/routes.rb`
- Kiểm tra controller `app/controllers/custom_search_controller.rb`
- Đảm bảo user đã login
- Kiểm tra permission `use_custom_search`

### Lỗi kết nối AI Backend
- Kiểm tra network connectivity giữa Redmine và AI backend
- Test URL: `curl http://backend:8000/api/search/rag` (từ Redmine container)
- Kiểm tra timeout settings (default: 360 seconds)
- Xem logs: `docker compose logs redmine | grep SearchClient`

## Gỡ cài đặt
Để gỡ plugin, chỉ cần xóa thư mục:
```bash
rm -rf plugins/custom_features
```
Sau đó khởi động lại Redmine:
```bash
docker compose restart redmine
```

