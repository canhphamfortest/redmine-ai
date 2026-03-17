# 📚 Tài liệu Hệ thống AI-Redmine

Thư mục này chứa tất cả tài liệu kỹ thuật về hệ thống AI-Redmine.

## 📖 Danh sách Tài liệu

### 1. [Tổng quan Kiến trúc](./architecture_overview.md)
Tài liệu tổng quan về kiến trúc hệ thống, các thành phần chính, luồng dữ liệu, và cách các components tương tác với nhau.

**Nội dung**:
- Kiến trúc tổng thể
- Các thành phần chính (Frontend, Backend, Database, Cache)
- Luồng dữ liệu (Ingestion, Search, Job Scheduling)
- Deployment architecture
- Technology stack

### 2. [Frontend: Redmine Assistant](./frontend_redmine_assistant.md)
Tài liệu chi tiết về phần frontend - Redmine plugin cung cấp giao diện tìm kiếm thông minh.

**Nội dung**:
- Cấu trúc plugin
- Tính năng chính (Custom Search Box, Search Page)
- Search Client và API integration
- View hooks và UI components
- Configuration và deployment

### 3. [Backend: Redmine Data](./backend_redmine_data.md)
Tài liệu chi tiết về phần backend - FastAPI service xử lý dữ liệu và quản lý jobs.

**Nội dung**:
- Cấu trúc project
- API endpoints (Auth, Ingestion, Search, Jobs, OpenAI Config)
- Services layer (Redmine Sync, Git Sync, Extractor, Chunker, Embedder, Retriever, RAG Chain)
- Job Scheduler
- Database models
- Configuration và deployment

> **Lưu ý**: Tài liệu này bao gồm tất cả API endpoints. Xem [RAG Search Sequence](./rag_search_sequence.md) để hiểu chi tiết về search flow.

### 4. [Database Schema](./vector_DB.plantuml)
Sơ đồ PlantUML mô tả cấu trúc database và các quan hệ giữa các bảng.

**Nội dung**:
- Entity Relationship Diagram (ERD)
- Các bảng chính (source, chunk, embedding)
- Các bảng quản lý (scheduled_jobs, job_executions, openai_usage_log, openai_config)
- Quan hệ giữa các bảng
- Notes và constraints

**Xem sơ đồ**: Mở file `.plantuml` bằng PlantUML viewer hoặc VS Code extension.

### 5. Sequence Diagrams

Các sơ đồ tuần tự mô tả chi tiết flow của các tính năng chính:

#### 5.1. [RAG Search Sequence](./rag_search_sequence.md)
Sơ đồ mô tả quy trình tìm kiếm RAG (Retrieval-Augmented Generation) với AI.

**Nội dung**:
- Request và cache check phase
- Retrieval phase (embedding, vector search, reranking)
- Context building và prompt creation
- AI generation và logging
- Response preparation và caching

#### 5.2. [Find Related Issues Sequence](./find_related_issues_sequence.md)
Sơ đồ mô tả quy trình tìm kiếm các issues liên quan bằng vector embedding similarity search.

**Nội dung**:
- Tìm source và embeddings của issue
- Vector similarity search với từng embedding riêng
- Merge kết quả và group chunks by issue
- Chọn top issues dựa trên similarity scores (không dùng AI)
- Filter và format response

#### 5.3. [Create Draft Note Sequence](./create_draft_note_sequence.md)
Sơ đồ mô tả quy trình tạo draft note với AI-generated checklist.

**Nội dung**:
- Build issue data và checklist prompt
- AI generation trực tiếp (không có vector search hay reranking)
- Parse checklist từ AI response
- Create journal entry với checklist

## 🗺️ Hướng dẫn Đọc Tài liệu

### Cho người mới bắt đầu

1. Bắt đầu với [Architecture Overview](./architecture_overview.md) để hiểu tổng quan hệ thống
2. Đọc [Database Schema](./vector_DB.plantuml) để hiểu cấu trúc dữ liệu
3. Tùy theo vai trò:
   - **Frontend Developer**: Đọc [Frontend Documentation](./frontend_redmine_assistant.md)
   - **Backend Developer**: Đọc [Backend Documentation](./backend_redmine_data.md)

### Cho người phát triển

- **Thêm tính năng mới**: Xem Architecture Overview và tài liệu component liên quan
- **Debug issues**: Xem Troubleshooting sections trong từng tài liệu
- **Deploy**: Xem Deployment sections

### Cho người quản trị

- **Monitor**: Xem Monitoring sections trong Backend documentation
- **Configure**: Xem Configuration sections trong Backend documentation

## 🔗 Liên kết Nhanh

| Tài liệu | Mô tả | Đối tượng |
|----------|-------|-----------|
| [Architecture Overview](./architecture_overview.md) | Tổng quan hệ thống | Tất cả |
| [Frontend Docs](./frontend_redmine_assistant.md) | Redmine Plugin | Frontend Dev |
| [Backend Docs](./backend_redmine_data.md) | FastAPI Backend | Backend Dev |
| [Database Schema](./vector_DB.plantuml) | ERD Diagram | Database/Backend Dev |
| [RAG Search Sequence](./rag_search_sequence.md) | Flow tìm kiếm RAG | Backend/Frontend Dev |
| [Find Related Issues Sequence](./find_related_issues_sequence.md) | Flow tìm issues liên quan | Backend/Frontend Dev |
| [Create Draft Note Sequence](./create_draft_note_sequence.md) | Flow tạo draft note | Backend/Frontend Dev |

---

**Last Updated**: December 2024
**Version**: 1.1

