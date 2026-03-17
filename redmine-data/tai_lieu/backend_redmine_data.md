# ⚙️ Backend: Redmine Data

## Tổng quan

**Redmine Data** là backend service xử lý dữ liệu, ingestion, và quản lý jobs cho hệ thống AI-Redmine. Service này chịu trách nhiệm:

- **Data Ingestion**: Đồng bộ dữ liệu từ các nguồn (Redmine, Documents)
- **Data Processing**: Extract, chunk, và generate embeddings
- **Job Management**: Quản lý scheduled jobs cho sync tự động
- **Monitoring**: Theo dõi usage, costs, và execution logs

> **Lưu ý**: Tài liệu này bao gồm tất cả các API endpoints (Auth, Ingestion, Search, Jobs, OpenAI Config, Budget). Phần Search API được mô tả chi tiết trong [Frontend Documentation](./frontend_redmine_assistant.md) và [RAG Search Sequence](./rag_search_sequence.md).

**Sequence Diagrams**:
- [RAG Search Sequence](./rag_search_sequence.md) - Flow tìm kiếm RAG với AI
- [Find Related Issues Sequence](./find_related_issues_sequence.md) - Flow tìm issues liên quan (Backend API endpoint)
- [Create Draft Note Sequence](./create_draft_note_sequence.md) - Flow tạo draft note với checklist

## Mục lục

- [Tổng quan](#tổng-quan)
- [Vị trí trong Hệ thống](#vị-trí-trong-hệ-thống)
- [Cấu trúc Project](#cấu-trúc-project)
- [Data Processing Flow](#data-processing-flow)
  - [Ingestion Flow](#ingestion-flow)
  - [Job Execution Flow](#job-execution-flow)
- [Backend Logic & APIs](#backend-logic--apis)
  - [1. Authentication API (`/api/auth`)](#1-authentication-api-apiauth)
  - [2. Data Ingestion API (`/api/ingest`)](#2-data-ingestion-api-apiingest)
  - [3. Search API (`/api/search`)](#3-search-api-apisearch)
  - [4. Job Management API (`/api/jobs`)](#4-job-management-api-apijobs)
  - [5. OpenAI Config API (`/api/openai-config`)](#5-openai-config-api-apiopenai-config)
  - [6. Budget API (`/api/budget`)](#6-budget-api-apibudget)
- [Processing Services Layer](#processing-services-layer)
  - [1. Document Extractor](#1-document-extractor)
  - [2. Chunker](#2-chunker)
  - [3. Embedder](#3-embedder)
- [Sync Services Layer](#sync-services-layer)
  - [4. Redmine Sync Service](#4-redmine-sync-service)
- [Job Management Services](#job-management-services)
  - [5. Job Executor](#5-job-executor)
- [Monitoring & Tracking Services](#monitoring--tracking-services)
  - [6. OpenAI Usage Tracker](#6-openai-usage-tracker)
  - [7. OpenAI Config Service](#7-openai-config-service)
- [Job Scheduler](#job-scheduler)
- [Database Models](#database-models)
  - [Core Models](#core-models)
  - [Management Models](#management-models)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Settings (config.py)](#settings-configpy)
- [Deployment](#deployment)
  - [Docker Compose](#docker-compose)
  - [Health Check](#health-check)
- [Monitoring & Observability](#monitoring--observability)
  - [Logs](#logs)
  - [Metrics & Statistics](#metrics--statistics)
- [Tài liệu Liên quan](#tài-liệu-liên-quan)

## Vị trí trong Hệ thống

```
┌─────────────────────────────────────────────────────────┐
│         Backend Services (redmine-data)                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Data Ingestion Layer                             │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  /api/ingest/*                              │ │  │
│  │  │  - POST /manual    → File Upload            │ │  │
│  │  │  - POST /redmine   → Redmine Issue Sync      │ │  │
│  │  │  - POST /redmine/wiki → Wiki Sync           │ │  │
│  │  │  - POST /redmine/wiki/project → Project Wiki│ │  │
│  │  │  - GET  /sources  → List Sources            │ │  │
│  │  │  - POST /sources/{id}/check → Check Source   │ │  │
│  │  │  - POST /sources/{id}/resync → Resync Source │ │  │
│  │  │  - GET  /stats    → Ingestion Stats          │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                    │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Job Management Layer                              │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  /api/jobs/*                                │  │  │
│  │  │  - GET    /         → List Jobs             │  │  │
│  │  │  - POST   /         → Create Job            │  │  │
│  │  │  - PUT    /{id}     → Update Job            │  │  │
│  │  │  - DELETE /{id}     → Delete Job            │  │  │
│  │  │  - POST   /{id}/run → Run Job Manually      │  │  │
│  │  │  - GET    /{id}/history → Job History       │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                    │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Processing Services Layer                         │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Extractor Service                           │  │  │
│  │  │  • Extract text from documents               │  │  │
│  │  │  • Extract metadata                          │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Chunker Service                             │  │  │
│  │  │  • Split text into chunks                    │  │  │
│  │  │  • Preserve context                          │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Embedder Service                            │  │  │
│  │  │  • Generate vector embeddings                │  │  │
│  │  │  • Batch processing                          │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                    │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Sync Services Layer                               │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Redmine Sync Service                        │  │  │
│  │  │  • Sync issues & wiki                        │  │  │
│  │  │  • Track sync status                         │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                    │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Job Scheduler & Executor                          │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Job Scheduler (APScheduler)                  │  │  │
│  │  │  • Load jobs from database                   │  │  │
│  │  │  • Schedule by cron expression               │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Job Executor                                │  │  │
│  │  │  • Execute scheduled jobs                    │  │  │
│  │  │  • Track execution status                    │  │  │
│  │  │  • Log results                               │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                    │
│  ┌───────────────────▼───────────────────────────────┐  │
│  │  Monitoring & Tracking                             │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  OpenAI Usage Tracker                        │  │  │
│  │  │  • Track API usage & costs                   │  │  │
│  │  │  • Calculate costs                           │  │  │
│  │  │  • Store in openai_usage_log                 │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  OpenAI Config Service                       │  │  │
│  │  │  • Manage model configurations              │  │  │
│  │  │  • Update pricing                           │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │                                    │
└──────────────────────┼────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼──────┐ ┌─────▼──────┐
│  PostgreSQL  │ │   Redis   │ │  OpenAI    │
│  + pgvector  │ │  (Cache)  │ │    API     │
│              │ │           │ │            │
│  • Sources   │ │  • Cache  │ │  • LLM     │
│  • Chunks    │ │  • Stats  │ │    Models  │
│  • Embeddings│ │           │ │  • Pricing │
│  • Jobs      │ │           │ │            │
│  • Logs      │ │           │ │            │
└──────────────┘ └───────────┘ └────────────┘
```

> **Lưu ý**: Chi tiết về các layers và services được mô tả trong các phần sau: [Processing Services Layer](#processing-services-layer), [Sync Services Layer](#sync-services-layer), [Job Management Services](#job-management-services), [Monitoring & Tracking Services](#monitoring--tracking-services), và [Job Scheduler](#job-scheduler).

## Cấu trúc Project

```
redmine-data/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration settings
│   ├── database.py                # Database setup
│   ├── models.py                  # SQLAlchemy models
│   ├── auth.py                    # Authentication utilities
│   │
│   ├── api/
│   │   ├── auth.py                # Authentication endpoints
│   │   ├── ingest/                # Data ingestion API
│   │   │   ├── router.py          # Ingestion router
│   │   │   ├── schemas.py         # Request/response schemas
│   │   │   └── handlers/          # Ingestion handlers
│   │   │       ├── manual_upload.py
│   │   │       ├── redmine_ingest.py
│   │   │       ├── sources.py
│   │   │       └── stats.py
│   │   ├── search/                # Search API
│   │   │   ├── router.py          # Search router
│   │   │   ├── schemas.py         # Request/response schemas
│   │   │   └── handlers/          # Search handlers
│   │   │       ├── vector_search.py
│   │   │       ├── rag_search.py
│   │   │       ├── related_issues.py
│   │   │       ├── history.py
│   │   │       ├── analytics.py
│   │   │       └── usage.py
│   │   ├── jobs/                  # Jobs API
│   │   │   ├── router.py          # Jobs router
│   │   │   ├── schemas.py         # Request/response schemas
│   │   │   └── handlers/          # Jobs handlers
│   │   │       ├── crud.py
│   │   │       ├── execution.py
│   │   │       └── background.py
│   │   ├── openai_config/         # OpenAI Config API
│   │   │   ├── router.py          # Config router
│   │   │   ├── schemas.py         # Request/response schemas
│   │   │   └── handlers/          # Config handlers
│   │   │       ├── crud.py
│   │   │       └── defaults.py
│   │   └── budget/                # Budget API
│   │       ├── router.py          # Budget router
│   │       ├── schemas.py         # Request/response schemas
│   │       └── handlers/          # Budget handlers
│   │           ├── crud.py
│   │           ├── status.py
│   │           ├── alerts.py
│   │           └── check.py
│   │
│   ├── services/
│   │   ├── extractor/              # Content extraction
│   │   │   ├── extractor.py
│   │   │   └── extractors/        # Format-specific extractors
│   │   ├── chunker/               # Text chunking
│   │   │   ├── chunker.py
│   │   │   ├── tokenizer.py
│   │   │   └── strategies/        # Chunking strategies
│   │   ├── embedder/              # Embedding generation
│   │   │   ├── embedder.py
│   │   │   ├── model.py
│   │   │   ├── generation.py
│   │   │   └── quality.py
│   │   ├── redmine/               # Redmine synchronization
│   │   │   ├── sync.py
│   │   │   ├── issue_sync.py
│   │   │   ├── wiki_sync.py
│   │   │   ├── content_builder.py
│   │   │   ├── attachment_handler.py
│   │   │   └── utils.py
│   │   ├── retriever/             # Vector search & retrieval
│   │   │   ├── retriever.py
│   │   │   ├── vector_search.py
│   │   │   └── result_formatter.py
│   │   ├── rag_chain/             # RAG chain
│   │   │   ├── chain.py
│   │   │   ├── context_builder.py
│   │   │   ├── generator.py
│   │   │   └── source_extractor.py
│   │   ├── cache/                 # Redis cache
│   │   │   ├── cache.py
│   │   │   ├── connection.py
│   │   │   ├── operations.py
│   │   │   └── stats.py
│   │   ├── check_source/           # Source validation
│   │   │   ├── checker.py
│   │   │   ├── issue_checker.py
│   │   │   ├── wiki_checker.py
│   │   │   └── resync_handler.py
│   │   ├── job_executor/           # Job execution
│   │   │   ├── executor.py
│   │   │   └── handlers/          # Job type handlers
│   │   ├── openai_usage_tracker/  # Usage tracking
│   │   │   ├── tracker.py
│   │   │   ├── pricing.py
│   │   │   └── statistics.py
│   │   ├── openai_config_service/ # Config management
│   │   └── budget/                # Budget management
│   │       ├── service.py
│   │       ├── pricing.py
│   │       └── queries.py
│   │
│   └── schedulers/
│       └── job_scheduler.py        # APScheduler setup
│
├── scripts/
│   └── init_db.sql                 # Database schema
│
├── docker-compose.yml              # Docker services
├── Dockerfile.backend              # Backend image
├── requirements.txt                # Python dependencies
└── Makefile                        # Helper commands
```

## Data Processing Flow

### Ingestion Flow

```
User/Job triggers ingestion
        │
        ▼
┌──────────────────────┐
│  Ingestion API       │  /api/ingest/*
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Sync Service        │  Redmine Sync
│  or                  │  or
│  File Upload         │  Document Upload
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Extractor Service   │  Extract text & metadata
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Create Source       │  Save to source table
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Chunker Service     │  Split into chunks
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Create Chunks        │  Save to chunk table
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Embedder Service    │  Generate embeddings
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Create Embeddings   │  Save to embedding table
└──────────────────────┘
```

### Job Execution Flow

```
Scheduler checks cron jobs
        │
        ▼
┌──────────────────────┐
│  Job Scheduler       │  Find jobs to run
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Create Execution    │  Log in job_executions
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Job Executor        │  Execute job logic
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Sync Service        │  Redmine/Git/Document
│  (if needed)         │  Sync data
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Update Execution    │  Log results & status
└──────────────────────┘
```

## Backend Logic & APIs

### 1. Authentication API (`/api/auth`)

**Mục đích**: Xác thực người dùng và quản lý session cho hệ thống.

#### Login

```http
POST /api/auth/login
Content-Type: application/json

Body:
{
  "username": "user123",
  "password": "password123"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Đăng nhập thành công!",
  "user": {
    "id": "uuid",
    "username": "user123",
    "email": "user@example.com",
    "full_name": "User Name",
    "is_admin": false,
    "is_active": true
  }
}
```

**Features**:
- Xác thực bằng username và password
- Mật khẩu được hash bằng bcrypt
- Cập nhật `last_login` khi đăng nhập thành công
- Trả về thông tin người dùng đầy đủ
- Không throw HTTPException, chỉ trả về `success=false` nếu thất bại

#### Verify User

```http
GET /api/auth/verify/{username}
```

**Response**:
```json
{
  "id": "uuid",
  "username": "user123",
  "email": "user@example.com",
  "full_name": "User Name",
  "is_admin": false,
  "is_active": true
}
```

**Features**:
- Kiểm tra user có tồn tại và đang active
- Sử dụng để verify session hoặc khôi phục session
- Chỉ trả về user nếu `is_active=True`
- Throw HTTP 404 nếu user không tồn tại hoặc không active

#### Get Current User Info

```http
GET /api/auth/me/{username}
```

**Response**:
```json
{
  "id": "uuid",
  "username": "user123",
  "email": "user@example.com",
  "full_name": "User Name",
  "is_admin": false,
  "is_active": true
}
```

**Features**:
- Lấy thông tin đầy đủ của user theo username
- Khác với verify: trả về user ngay cả khi `is_active=False`
- Throw HTTP 404 nếu user không tồn tại

### 2. Data Ingestion API (`/api/ingest`)

**Mục đích**: Đồng bộ và xử lý dữ liệu từ các nguồn khác nhau để đưa vào vector database.

#### Manual File Upload

```http
POST /api/ingest/manual
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (required)
- source_type: str (default: "document")
- project_key: str (optional)
- language: str (default: "en")
```

**Flow**:
1. Save uploaded file
2. Extract content (text, metadata)
3. Create source record
4. Chunk content
5. Generate embeddings
6. Store in database

**Response**:
```json
{
  "source_id": "uuid",
  "chunks_created": 10,
  "status": "success"
}
```

#### Redmine Issue Sync

```http
POST /api/ingest/redmine
Content-Type: application/json

Body:
{
  "issue_id": 123
}
```

**Service**: `app/services/redmine/sync.py` - `RedmineSync.sync_single_issue()`

**Features**:
- Sync một Redmine issue đơn lẻ
- Issue được sync đồng bộ (không background)
- Sử dụng `RedmineSync.sync_single_issue()`
- Issue phải tồn tại trong Redmine

**Response**:
```json
{
  "status": "completed",
  "issue_id": 123,
  "result": {...}
}
```

#### Redmine Wiki Sync

```http
POST /api/ingest/redmine/wiki
Content-Type: application/json

Body:
{
  "project_id": "project-key",
  "wiki_page": "PageTitle",
  "version": 5
}
```

**Features**:
- Sync một trang wiki Redmine đơn lẻ
- Wiki page được sync đồng bộ (không background)
- Sử dụng `RedmineSync.sync_wiki_page()`
- Nếu `version` được chỉ định, sẽ sync version cụ thể
- Nếu `version=None`, sẽ sync version mới nhất

**Response**:
```json
{
  "status": "completed",
  "project_id": "project-key",
  "wiki_page": "PageTitle",
  "result": {...}
}
```

#### Redmine Wiki Project Sync

```http
POST /api/ingest/redmine/wiki/project
Content-Type: application/json

Body:
{
  "project_id": "project-key"
}
```

**Features**:
- Sync tất cả wiki pages trong một project
- Sync đồng bộ tất cả pages
- Sử dụng `app/services/redmine/sync.py` - `RedmineSync.sync_project_wiki()`

**Response**:
```json
{
  "status": "completed",
  "project_id": "project-key",
  "pages_synced": 10,
  "result": {...}
}
```

#### List Sources

```http
GET /api/ingest/sources?source_type=redmine_issue&sync_status=success&project_id=project-key&limit=100&offset=0
```

**Features**:
- Liệt kê sources với các bộ lọc và phân trang
- Filter theo: `source_type`, `sync_status`, `project_id`
- Sắp xếp theo `updated_at` giảm dần (mới nhất trước)
- Tất cả filters được kết hợp bằng AND

**Response**:
```json
{
  "total": 150,
  "limit": 100,
  "offset": 0,
  "sources": [
    {
      "id": "uuid",
      "source_type": "redmine_issue",
      "external_id": "redmine_issue_123",
      "external_url": "https://...",
      "project_key": "project-key",
      "project_id": 1,
      "sync_status": "success",
      "last_sync_at": "2024-01-01T00:00:00",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

#### Check Source

```http
POST /api/ingest/sources/{source_id}/check
```

**Features**:
- Kiểm tra xem source có cần được đồng bộ lại không
- So sánh content hash trong database với content hash trong Redmine
- Chỉ hỗ trợ `redmine_issue` sources
- Sử dụng `SourceChecker` để thực hiện kiểm tra
- Source sẽ được đánh dấu `outdated` nếu content đã thay đổi

**Response**:
```json
{
  "success": true,
  "outdated": false,
  "was_outdated": false,
  "message": "Source is up to date"
}
```

#### Resync Source

```http
POST /api/ingest/sources/{source_id}/resync
```

**Features**:
- Đồng bộ lại một source từ Redmine hoàn toàn
- Hỗ trợ `redmine_issue` và `redmine_wiki` sources
- Source sẽ được sync lại hoàn toàn (tạo lại chunks/embeddings nếu cần)
- Sync status sẽ được cập nhật thành `success` sau khi sync thành công

**Response**:
```json
{
  "success": true,
  "message": "Source re-synced successfully"
}
```

#### Get Ingestion Statistics

```http
GET /api/ingest/stats
```

**Features**:
- Lấy thống kê về ingestion
- Tổng số sources, chunks, embeddings
- Thống kê theo source_type
- Thống kê theo sync_status

### 3. Search API (`/api/search`)

**Mục đích**: Tìm kiếm semantic và RAG search với AI.

> **Lưu ý**: Phần Search API được mô tả chi tiết trong [Frontend Documentation](./frontend_redmine_assistant.md) và [RAG Search Sequence](./rag_search_sequence.md). Phần này liệt kê đầy đủ các endpoints với request/response examples.

#### Vector Search

```http
POST /api/search/vector
Content-Type: application/json

Body:
{
  "query": "search query",
  "top_k": 5
}
```

**Features**:
- Tìm kiếm semantic bằng vector embeddings
- Trả về top K chunks liên quan nhất
- Sử dụng vector similarity search

#### RAG Search

```http
POST /api/search/rag
Content-Type: application/json

Body:
{
  "query": "search query"
}
```

**Features**:
- RAG (Retrieval-Augmented Generation) search với AI
- Tìm kiếm chunks liên quan, rerank, và tạo câu trả lời AI
- Cache response trong Redis (1 ngày)
- Log search vào `search_log` table

**Response**:
```json
{
  "query": "search query",
  "answer": "AI generated answer...",
  "sources": [...],
  "retrieved_chunks": [...],
  "cached": false,
  "response_time_ms": 1234
}
```

#### Generate Text (AI generation không có retrieval)

```http
POST /api/search/generate
Content-Type: application/json

Body:
{
  "prompt": "Full prompt text"
}
```

**Features**:
- Generate text bằng AI trực tiếp (không có vector search và reranking)
- Bỏ qua retrieval, sử dụng prompt trực tiếp
- Cache response trong Redis (1 ngày)
- Log search vào `search_log` table
- **Sử dụng**: Checklist generation trong Create Draft Note flow

**Response**:
```json
{
  "prompt": "Full prompt text",
  "answer": "AI generated text...",
  "sources": [],
  "retrieved_chunks": [],
  "cached": false,
  "response_time_ms": 567
}
```

**Lưu ý**:
- `sources` và `retrieved_chunks` luôn là empty arrays vì không có retrieval
- Endpoint này tối ưu cho các use case không cần context từ database
- Nhanh hơn RAG search vì bỏ qua vector search và reranking

#### Find Related Issues

```http
GET /api/search/issues/{issue_id}/related?top_k=20
```

**Features**:
- Tìm các issues liên quan bằng vector embedding
- Search với từng embedding riêng và merge kết quả
- Loại trừ issue hiện tại khỏi kết quả
- Chọn top issues dựa trên similarity scores (không dùng AI)

**Response**:
```json
{
  "issue_id": 123,
  "related_issues": [
    {
      "issue_id": 456,
      "similarity_score": 0.85,
      "similarity_percentage": 85.0,
      "subject": "Related issue subject"
    }
  ],
  "count": 5,
  "response_time_ms": 567
}
```

#### Get Search History

```http
GET /api/search/history?limit=100&offset=0
```

**Features**:
- Lấy lịch sử tìm kiếm
- Phân trang với limit và offset
- Sắp xếp theo thời gian giảm dần

#### Get Search Analytics

```http
GET /api/search/analytics?days=30
```

**Features**:
- Lấy thống kê tìm kiếm
- Thống kê theo khoảng thời gian
- Số lượng queries, average response time, etc.

#### Get OpenAI Usage

```http
GET /api/search/usage?days=30&model=gpt-4o-mini
```

**Features**:
- Lấy thống kê sử dụng OpenAI API
- Filter theo model (tùy chọn)
- Tổng số tokens, chi phí ước tính, số lượng requests
- Thống kê theo model (nếu không filter)

#### Get Billing Cycle Usage

```http
GET /api/search/usage/billing-cycles?invoice_day=1&num_cycles=12&model=gpt-4o-mini
```

**Features**:
- Lấy thống kê sử dụng được nhóm theo billing cycles
- Mỗi cycle bắt đầu từ `invoice_day` của tháng
- `invoice_day`: 1-31 (mặc định: 1)
- `num_cycles`: 1-24 (mặc định: 12)
- Filter theo model (tùy chọn)

**Response**:
```json
{
  "cycles": [
    {
      "cycle_start": "2024-01-01T00:00:00",
      "cycle_end": "2024-01-31T23:59:59",
      "total_input_tokens": 1000000,
      "total_output_tokens": 500000,
      "total_tokens": 1500000,
      "estimated_cost": 0.15,
      "request_count": 100
    }
  ],
  "total_across_cycles": {...}
}
```

### 4. Job Management API (`/api/jobs`)

**Mục đích**: Quản lý scheduled jobs để tự động sync dữ liệu theo lịch định kỳ.

#### List Jobs

```http
GET /api/jobs
```

**Response**:
```json
{
  "jobs": [
    {
      "id": "uuid",
      "job_name": "Daily Redmine Sync",
      "job_type": "redmine_sync",
      "cron_expression": "0 2 * * *",
      "is_active": true,
      "last_run_at": "...",
      "next_run_at": "..."
    }
  ]
}
```

#### Create Job

```http
POST /api/jobs
Content-Type: application/json

Body:
{
  "job_name": "Daily Sync",
  "job_type": "redmine_sync",
  "cron_expression": "0 2 * * *",
  "config": {
    "project_id": 1,
    "sync_issues": true
  }
}
```

#### Update Job

```http
PUT /api/jobs/{job_id}
Content-Type: application/json

Body:
{
  "is_active": false,
  "cron_expression": "0 3 * * *"
}
```

#### Delete Job

```http
DELETE /api/jobs/{job_id}
```

#### Run Job Manually

```http
POST /api/jobs/{job_id}/run
```

#### Get Job History

```http
GET /api/jobs/{job_id}/history
```

**Response**:
```json
{
  "executions": [
    {
      "id": "uuid",
      "started_at": "...",
      "completed_at": "...",
      "status": "success",
      "items_processed": 100,
      "items_failed": 0
    }
  ]
}
```

### 5. OpenAI Config API (`/api/openai-config`)

**Mục đích**: Quản lý cấu hình OpenAI models và pricing để tính toán costs chính xác.

#### List Configs

```http
GET /api/openai-config
```

**Response**: List of all model configurations

#### Create Config

```http
POST /api/openai-config
Content-Type: application/json

Body:
{
  "model_name": "gpt-4o-mini",
  "input_price_per_1m": 0.15,
  "output_price_per_1m": 0.60,
  "is_default": false,
  "is_active": true
}
```

#### Get Config

```http
GET /api/openai-config/{model_name}
```

**Response**: Model configuration

#### Update Config

```http
PUT /api/openai-config/{model_name}
Content-Type: application/json

Body:
{
  "input_price_per_1m": 0.15,
  "output_price_per_1m": 0.60,
  "is_default": true,
  "is_active": true
}
```

#### Delete Config

```http
DELETE /api/openai-config/{model_name}
```

#### Sync Default Pricing

```http
POST /api/openai-config/sync-defaults
```

**Features**:
- Đồng bộ pricing mặc định từ hardcoded values
- Tạo hoặc cập nhật configs cho các models mặc định

#### Get Default Model

```http
GET /api/openai-config/default-model
```

**Response**: Model name của default model

#### Set Default Model

```http
POST /api/openai-config/default-model/{model_name}
```

**Features**:
- Set model mặc định cho RAG search
- Model phải tồn tại và `is_active=True`

### 6. Budget API (`/api/budget`)

**Mục đích**: Quản lý budget cho các LLM providers, theo dõi chi phí và gửi cảnh báo khi vượt ngưỡng.

#### List Budget Configs

```http
GET /api/budget/configs
```

**Response**: List of all budget configurations

#### Create Budget Config

```http
POST /api/budget/configs
Content-Type: application/json

{
  "provider": "openai",
  "budget_amount_usd": 100.0,
  "invoice_day": 1,
  "alert_thresholds": [50, 80, 100],
  "is_active": true
}
```

**Fields**:
- `provider`: Provider name (openai, google, anthropic, groq)
- `budget_amount_usd`: Budget amount in USD
- `invoice_day`: Day of month for billing cycle (1-31)
- `alert_thresholds`: Alert thresholds as percentages (e.g., [50, 80, 100])
- `is_active`: Whether budget is active

#### Update Budget Config

```http
PUT /api/budget/configs/{config_id}
Content-Type: application/json

{
  "budget_amount_usd": 150.0,
  "alert_thresholds": [60, 90, 100]
}
```

#### Get Budget Status (All Providers)

```http
GET /api/budget/status
```

**Response**:
```json
{
  "statuses": [
    {
      "provider": "openai",
      "budget_config_id": "uuid",
      "budget_amount_usd": 100.0,
      "current_spending_usd": 45.50,
      "remaining_budget_usd": 54.50,
      "percentage_used": 45.5,
      "billing_cycle_start": "2024-01-01",
      "billing_cycle_end": "2024-02-01",
      "invoice_day": 1,
      "alert_thresholds": [50, 80, 100],
      "is_active": true
    }
  ],
  "total_providers": 1
}
```

#### List Budget Alerts

```http
GET /api/budget/alerts?status=unacknowledged&provider=openai
```

**Query Parameters**:
- `status`: Filter by status (all, unacknowledged, acknowledged)
- `provider`: Filter by provider

**Features**:
- Tự động tính toán billing cycle dựa trên invoice_day
- Gửi email alerts khi vượt ngưỡng qua AWS SES hoặc SMTP
- Theo dõi chi phí theo từng provider (openai, google, anthropic, groq)
- Alert types: `threshold_reached`, `budget_exceeded`
- Tích hợp với scheduler để check định kỳ

## Processing Services Layer

Các services này xử lý dữ liệu từ ingestion đến khi lưu vào database.

### 1. Document Extractor

**File**: `app/services/extractor/extractor.py`

**Class**: `ContentExtractor`

**Chức năng**:
- Extract text từ documents (PDF, DOCX, TXT, MD, JSON, HTML)
- Extract metadata (author, dates, pages)
- Tự động phát hiện file format và chọn extractor phù hợp
- Fallback về Apache Tika cho các định dạng không được hỗ trợ trực tiếp

**Supported Formats**:
- PDF: `extract_pdf()` - PyPDF2, pdfplumber
- DOCX: `extract_docx()` - python-docx
- DOC: `extract_with_tika()` - Apache Tika (cho định dạng DOC cũ)
- TXT: `extract_text()` - Plain text
- Markdown: `extract_markdown()` - CommonMark
- JSON: `extract_json()` - JSON parser
- HTML: `extract_html()` - HTML parser
- Other: `extract_with_tika()` - Apache Tika fallback

**Extractors Location**: `app/services/extractor/extractors/`
- `pdf_extractor.py`: PDF extraction
- `docx_extractor.py`: DOCX extraction
- `text_extractor.py`: Plain text extraction
- `tika_extractor.py`: Apache Tika fallback

**Singleton Instance**: `extractor` (exported từ module)

**Sử dụng**: Được gọi trong ingestion flow khi upload file hoặc sync documents.

### 2. Chunker

**File**: `app/services/chunker/chunker.py`

**Class**: `TextChunker`

**Chức năng**:
- Split text thành chunks
- Preserve context (headings, metadata)
- Handle different chunk types với strategies riêng biệt

**Chunk Types & Strategies**:
- `text`: Plain text chunks - `chunk_text()` strategy
- `code`: Code blocks - `chunk_code()` strategy (preserve functions/classes context)
- `redmine_issue`: Issue content - `chunk_redmine_issue()` strategy
- `redmine_wiki`: Wiki sections - `chunk_redmine_wiki()` strategy

**Strategies Location**: `app/services/chunker/strategies/`
- `text_chunker.py`: Plain text chunking
- `code_chunker.py`: Code chunking với context preservation
- `issue_chunker.py`: Redmine issue chunking
- `wiki_chunker.py`: Redmine wiki chunking

**Components**:
- `tokenizer.py`: Tokenizer để đếm tokens (encoding: cl100k_base)

**Parameters**:
- `chunk_size`: Default 512 tokens (từ settings)
- `chunk_overlap`: Default 50 tokens (từ settings)

**Sử dụng**: Được gọi sau khi extract content, trước khi generate embeddings.

### 3. Embedder

**File**: `app/services/embedder/embedder.py`

**Class**: `EmbeddingService`

**Chức năng**:
- Generate vector embeddings từ text
- Batch processing để tối ưu performance
- Caching để tránh duplicate embeddings
- Quality scoring để đánh giá chất lượng embeddings

**Components**:
- `model.py`: `EmbeddingModel` - Quản lý model loading và embedding dimension
- `generation.py`: `EmbeddingGenerator` - Xử lý việc tạo embeddings với caching
- `quality.py`: `QualityScorer` - Tính điểm chất lượng của embeddings

**Model**: `intfloat/multilingual-e5-large`
- Dimension: 1024
- Supports Vietnamese và English (và 100+ ngôn ngữ khác)
- Library: sentence-transformers

**Singleton Instance**: `embedder` (exported từ module)

**Sử dụng**: Được gọi sau khi chunk content, để tạo embeddings cho vector search.

#### Embedding Model: Lựa chọn và So sánh

Hệ thống sử dụng **`intfloat/multilingual-e5-large`** làm embedding model. Phần này giải thích lý do lựa chọn và so sánh với các model khác.

##### Tại sao chọn multilingual-e5-large?

**1. Hỗ trợ đa ngôn ngữ xuất sắc**
- Hỗ trợ tốt cho **100+ ngôn ngữ**, bao gồm tiếng Việt và tiếng Anh
- Được đào tạo trên dataset đa ngôn ngữ rất lớn với contrastive learning
- Không cần pre-processing đặc biệt cho tiếng Việt (không cần tách từ, normalize)
- Hiệu suất ổn định và đồng đều trên nhiều ngôn ngữ

**2. Hiệu suất và chất lượng**
- **Dimension: 1024** - đủ lớn để capture semantic meaning phức tạp
- **Top performance** trên MTEB benchmark cho multilingual models
- Chất lượng embedding cao cho cả retrieval và clustering tasks
- Tốc độ inference tốt với batch processing

**3. Miễn phí và mã nguồn mở**
- Hoàn toàn miễn phí, không có giới hạn API calls
- Có thể chạy local hoặc qua Hugging Face
- Không phụ thuộc vào external API (tránh rate limits, costs)
- Cộng đồng lớn và được Microsoft hỗ trợ

**4. Tích hợp dễ dàng**
- Tương thích với `sentence-transformers` library
- Dễ deploy và scale
- Hỗ trợ batch processing hiệu quả
- Documentation và examples phong phú

##### So sánh với các Model khác

###### Models Miễn phí (Open Source)

| Model | Dimension | Đa ngôn ngữ | Tiếng Việt | Hiệu suất | Ghi chú |
|-------|-----------|-------------|------------|-----------|---------|
| **intfloat/multilingual-e5-large** ⭐ | 1024 | ✅ Xuất sắc (100+ ngôn ngữ) | ✅ Tốt | ⭐⭐⭐⭐⭐ | **Đã chọn** - Top performance cho multilingual |
| mixedbread-ai/mxbai-embed-large-v1 | 1024 | ✅ Tốt | ✅ Tốt | ⭐⭐⭐⭐ | Chất lượng tốt, cân bằng |
| intfloat/multilingual-e5-base | 768 | ✅ Tốt | ⚠️ Trung bình | ⭐⭐⭐ | Version nhỏ hơn, dimension thấp hơn |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | ⚠️ Hạn chế | ⚠️ Kém | ⭐⭐⭐ | Nhỏ, nhanh nhưng chất lượng thấp cho tiếng Việt |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | ✅ Tốt | ⚠️ Trung bình | ⭐⭐⭐ | Hỗ trợ đa ngôn ngữ nhưng dimension thấp |
| BAAI/bge-large-en-v1.5 | 1024 | ❌ Chỉ tiếng Anh | ❌ Không | ⭐⭐⭐⭐⭐ | Tốt cho tiếng Anh nhưng không hỗ trợ tiếng Việt |
| BAAI/bge-m3 | 1024 | ✅ Tốt | ✅ Tốt | ⭐⭐⭐⭐ | Mới, tốt nhưng lớn và phức tạp hơn |
| jinaai/jina-embeddings-v2-base-en | 768 | ❌ Chỉ tiếng Anh | ❌ Không | ⭐⭐⭐⭐ | Tốt cho tiếng Anh, không phù hợp đa ngôn ngữ |

**Kết luận cho Models Miễn phí**: `intfloat/multilingual-e5-large` được chọn vì:
- **Hỗ trợ 100+ ngôn ngữ** với chất lượng đồng đều, đặc biệt tốt cho tiếng Việt và tiếng Anh
- **Top performance** trên MTEB benchmark cho multilingual retrieval tasks
- Dimension 1024 đủ lớn cho semantic search phức tạp
- Được Microsoft Research phát triển và maintain tốt
- Cộng đồng lớn và documentation phong phú

###### Models Có phí (API-based)

| Model | Provider | Dimension | Đa ngôn ngữ | Tiếng Việt | Giá (per 1M tokens) | Ghi chú |
|-------|----------|-----------|-------------|------------|---------------------|---------|
| text-embedding-3-large | OpenAI | 3072 | ✅ Tốt | ✅ Tốt | $0.13 | Chất lượng cao nhất, nhưng đắt |
| text-embedding-3-small | OpenAI | 1536 | ✅ Tốt | ✅ Tốt | $0.02 | Rẻ hơn nhưng dimension thấp hơn |
| text-embedding-ada-002 | OpenAI | 1536 | ✅ Tốt | ⚠️ Trung bình | $0.10 | Legacy, không khuyến nghị |
| embedding-001 | Google | 768 | ✅ Tốt | ✅ Tốt | $0.0001 | Rất rẻ nhưng chất lượng thấp hơn |
| Cohere embed-multilingual-v3.0 | Cohere | 1024 | ✅ Tốt | ✅ Tốt | $0.10 | Tốt nhưng đắt |
| Voyage-large-2 | Voyage AI | 1024 | ✅ Tốt | ✅ Tốt | $0.10 | Chất lượng tốt, giá hợp lý |

**Kết luận cho Models Có phí**: 
- **OpenAI text-embedding-3-large**: Chất lượng cao nhất nhưng chi phí cao ($0.13/1M tokens)
- **OpenAI text-embedding-3-small**: Cân bằng tốt giữa chất lượng và chi phí ($0.02/1M tokens)
- **Voyage-large-2**: Chất lượng tốt, giá hợp lý ($0.10/1M tokens)

**Tại sao không chọn Models Có phí?**
1. **Chi phí**: Với lượng dữ liệu lớn (hàng nghìn chunks), chi phí API sẽ tích lũy nhanh
2. **Rate Limits**: API có giới hạn requests/second, ảnh hưởng đến batch processing
3. **Dependency**: Phụ thuộc vào external service, có thể bị downtime
4. **Privacy**: Dữ liệu phải gửi đến external API (mặc dù các provider cam kết không lưu trữ)
5. **Latency**: Network latency khi gọi API, chậm hơn local inference

##### Tiêu chí Lựa chọn

Các tiêu chí chính được xem xét khi lựa chọn embedding model:

**1. Hỗ trợ Đa ngôn ngữ (Quan trọng nhất)**
- ✅ Hỗ trợ tốt cho tiếng Việt và tiếng Anh
- ✅ Không cần pre-processing đặc biệt
- ✅ Chất lượng embedding tương đương cho cả hai ngôn ngữ

**2. Chất lượng Embedding**
- ✅ Dimension đủ lớn (≥1024) để capture semantic meaning
- ✅ Performance tốt trên các benchmark (MTEB, BEIR)
- ✅ Khả năng phân biệt semantic tốt (high recall và precision)

**3. Hiệu suất**
- ✅ Tốc độ inference nhanh (quan trọng cho batch processing)
- ✅ Hỗ trợ batch processing hiệu quả
- ✅ Memory footprint hợp lý

**4. Chi phí**
- ✅ Miễn phí hoặc chi phí thấp
- ✅ Không có giới hạn API calls
- ✅ Có thể chạy local

**5. Dễ tích hợp**
- ✅ Tương thích với `sentence-transformers`
- ✅ Dễ deploy và scale
- ✅ Documentation tốt

**6. Bảo mật và Privacy**
- ✅ Có thể chạy local (không cần gửi dữ liệu ra ngoài)
- ✅ Không phụ thuộc vào external API

##### Khi nào nên xem xét Models Có phí?

Nên xem xét models có phí (như OpenAI text-embedding-3-large) trong các trường hợp:

1. **Chất lượng là ưu tiên hàng đầu**: Khi cần chất lượng embedding tốt nhất có thể
2. **Volume thấp**: Khi lượng dữ liệu nhỏ, chi phí API không đáng kể
3. **Real-time requirements**: Khi cần inference real-time và không muốn maintain model server
4. **Multi-tenant SaaS**: Khi cần scale nhanh mà không muốn quản lý infrastructure

##### Benchmark và Performance

**MTEB (Massive Text Embedding Benchmark)** - Điểm số cho các model:

| Model | Average Score | Retrieval | Clustering | Classification |
|-------|---------------|-----------|------------|----------------|
| **multilingual-e5-large** ⭐ | **~64.6** | **~61.2** | **~65.5** | **~67.8** |
| mxbai-embed-large-v1 | ~64.0 | ~60.0 | ~65.0 | ~67.0 |
| text-embedding-3-large | ~64.5 | ~61.0 | ~66.0 | ~67.5 |
| text-embedding-3-small | ~62.0 | ~58.0 | ~63.0 | ~65.0 |

*Lưu ý: Điểm số có thể thay đổi theo version và dataset. multilingual-e5-large có performance tốt nhất trong các model open-source và tương đương với các model có phí.*

##### Kết luận

**`intfloat/multilingual-e5-large`** được chọn vì:

1. ✅ **Hỗ trợ đa ngôn ngữ xuất sắc** - Đặc biệt tốt cho tiếng Việt và tiếng Anh
2. ✅ **Chất lượng cao** - Dimension 1024, performance tốt trên benchmarks
3. ✅ **Miễn phí** - Không có chi phí API, không có rate limits
4. ✅ **Dễ tích hợp** - Tương thích với sentence-transformers, dễ deploy
5. ✅ **Privacy** - Có thể chạy local, không cần gửi dữ liệu ra ngoài
6. ✅ **Hiệu suất** - Tốc độ inference nhanh, hỗ trợ batch processing

Đây là lựa chọn tối ưu cho hệ thống cần hỗ trợ đa ngôn ngữ (tiếng Việt + tiếng Anh) với chi phí thấp và chất lượng cao.

## Sync Services Layer

Các services này đồng bộ dữ liệu từ external sources.

### 4. Redmine Sync Service

**File**: `app/services/redmine/sync.py`

**Class**: `RedmineSync`

**Chức năng**:
- Kết nối Redmine API (sử dụng redminelib)
- Đồng bộ issues và wiki pages từ Redmine
- Extract content và metadata
- Handle rate limiting (configurable delay giữa các API calls)
- Track sync status và incremental sync support

**Methods**:
- `sync_project(project_id, incremental, filters)`: Sync toàn bộ project (issues và wiki)
- `sync_single_issue(issue_id)`: Sync một issue đơn lẻ
- `sync_wiki_page(project_id, wiki_page, version)`: Sync một wiki page
- `sync_project_wiki(project_id)`: Sync tất cả wiki pages trong project

**Handlers** (trong `app/services/redmine/`):
- `issue_sync.py`: `IssueSyncHandler` - Xử lý sync issues
- `wiki_sync.py`: `WikiSyncHandler` - Xử lý sync wiki pages
- `content_builder.py`: `ContentBuilder` - Xây dựng content từ Redmine data
- `attachment_handler.py`: `AttachmentHandler` - Xử lý attachments
- `utils.py`: Utility functions

**Status Tracking**:
- `sync_status`: pending, success, failed, outdated
- `last_sync_at`: Timestamp của lần sync cuối
- `retry_count`: Số lần retry nếu failed

**Rate Limiting**: Configurable delay (`redmine_api_delay` setting, default: 0.2s)

**Sử dụng**: Được gọi từ `/api/ingest/redmine` hoặc scheduled jobs.

### 5. Git Sync Service

**File**: `app/services/git_sync/sync.py`

**Class**: `GitSync`

**Chức năng**:
- Clone Git repositories vào temporary directory
- Tìm files dựa trên patterns và paths
- Extract file content
- Track commit metadata
- Handle large repositories
- Tự động cleanup temporary directories

**Methods**:
- `sync_repository(repo_url, branch, file_patterns, paths)`: Sync toàn bộ repository
- `sync_file(file_path, ...)`: Sync single file (nếu cần)

**Components** (trong `app/services/git_sync/`):
- `repository.py`: `RepositoryManager` - Quản lý Git operations (clone, pull)
- `file_sync.py`: `FileSyncHandler` - Xử lý sync từng file (extract, chunk, embed)
- `detectors.py`: File detection utilities

**Features**:
- Content hashing (SHA1) để phát hiện thay đổi
- File filtering theo patterns và paths
- Code chunking với context preservation (functions/classes)
- Temporary directory management

**Sử dụng**: Được gọi từ `/api/ingest/git` hoặc scheduled jobs.

## Job Management Services

### 6. Job Executor

**File**: `app/services/job_executor/executor.py`

**Class**: `JobExecutor`

**Chức năng**:
- Execute scheduled jobs với đầy đủ tracking và error handling
- Tạo và cập nhật execution records
- Gọi handler phù hợp dựa trên job type
- Track progress và errors
- Cập nhật job last_run_at

**Job Types**:
- `redmine_sync`: Sync Redmine data - `execute_redmine_sync()` handler
- `source_check`: Check và resync outdated sources - `execute_source_check()` handler

**Handlers** (trong `app/services/job_executor/handlers/`):
- `redmine_handler.py`: `execute_redmine_sync()` - Redmine synchronization
- `source_check_handler.py`: `execute_source_check()` - Source checking và resync

**Workflow**:
1. Lấy hoặc tạo JobExecution record với status="running"
2. Gọi handler phù hợp dựa trên job.job_type
3. Cập nhật execution record với kết quả (status, items_processed, items_failed)
4. Cập nhật job.last_run_at
5. Xử lý errors và cập nhật execution status

**Sử dụng**: Được gọi bởi Job Scheduler khi đến thời gian chạy job, hoặc thủ công qua API `/api/jobs/{id}/run`.

## Monitoring & Tracking Services

### 6. OpenAI Usage Tracker

**File**: `app/services/openai_usage_tracker/tracker.py`

**Class**: `OpenAIUsageTracker`

**Chức năng**:
- Track API usage (tokens, costs, response times)
- Calculate costs based on model pricing
- Store usage logs vào database
- Generate statistics và billing cycle reports

**Methods**:
- `log_usage()`: Ghi log usage vào `openai_usage_log` table
- `log_usage_detail()`: Ghi log chi tiết (prompt, response) vào `openai_usage_log_detail` table
- `get_usage_stats()`: Lấy thống kê usage trong khoảng thời gian
- `get_billing_cycle_stats()`: Lấy thống kê theo billing cycles

**Components** (trong `app/services/openai_usage_tracker/`):
- `pricing.py`: `calculate_cost()` - Tính toán chi phí dựa trên pricing
- `statistics.py`: Statistics và billing cycle utilities

**Database Tables**:
- `openai_usage_log`: Log usage statistics (tokens, costs, response times)
- `openai_usage_log_detail`: Log prompt và response chi tiết

**Pricing Source**:
- Database: `openai_config` table (ưu tiên)
- Fallback: Hardcoded pricing trong `pricing.py`

**Sử dụng**: Được gọi tự động khi có OpenAI API calls (từ RAG search hoặc các services khác). Tất cả methods là static methods.

### 7. OpenAI Config Service

**File**: `app/services/openai_config_service/service.py`

**Class**: `OpenAIConfigService`

**Chức năng**:
- Manage model configurations và pricing
- Get default model
- Update pricing cho các models
- Validate configurations
- Sync pricing từ hardcoded values

**Methods**:
- `get_all_configs()`: Lấy tất cả configs (bao gồm inactive)
- `get_active_configs()`: Lấy configs đang active
- `get_config_by_model()`: Lấy config cho một model cụ thể
- `get_default_model()`: Lấy model mặc định
- `set_default_model()`: Set model mặc định
- `sync_default_pricing()`: Đồng bộ pricing mặc định từ hardcoded values

**Components** (trong `app/services/openai_config_service/`):
- `queries.py`: Database queries cho configs
- `pricing.py`: Pricing utilities và default pricing values

**Database Table**: `openai_config`

**Sử dụng**: Được gọi từ `/api/openai-config/*` endpoints và bởi Usage Tracker để lấy pricing. Tất cả methods là static methods.

## Job Scheduler

**Mục đích**: Tự động chạy scheduled jobs theo cron expression.

**File**: `app/schedulers/job_scheduler.py`

**Class**: `JobSchedulerService`

**Công nghệ**: APScheduler + httpx (gọi Backend API)

**Kiến trúc**: Lightweight scheduler (~200MB Docker image)
- **KHÔNG** import các dependency ML nặng (torch, transformers, sentence-transformers)
- Gọi Backend API để thực thi jobs thay vì chạy trực tiếp
- Cho phép chạy scheduler trong container nhỏ riêng biệt

**Chức năng**:
- Load jobs từ database (`scheduled_jobs`)
- Schedule jobs theo cron expression
- Trigger job execution qua Backend API (`POST /api/jobs/{job_id}/run`)
- Poll database để phát hiện thay đổi job và reload schedules
- Xử lý job execution events và cập nhật `next_run_at`

**Service**: Chạy trong container riêng (`scheduler`)

**Workflow**:
1. Load jobs từ `scheduled_jobs` table (chỉ jobs có `is_active = true`)
2. Schedule jobs theo `cron_expression` với APScheduler
3. Khi đến thời gian, gọi Backend API `POST /api/jobs/{job_id}/run` để trigger execution
4. Backend API sẽ gọi `JobExecutor.execute_job()` để thực thi
5. Execution được log vào `job_executions` table bởi Backend
6. Scheduler cập nhật `next_run_at` trong `scheduled_jobs` sau khi job hoàn thành

**Cron Examples**:
- `0 2 * * *`: 2 AM hàng ngày
- `0 */6 * * *`: Mỗi 6 giờ
- `0 0 * * 0`: Chủ nhật hàng tuần

**Note**: Scheduler service là lightweight và chỉ quản lý scheduling. Tất cả job execution logic được thực hiện bởi Backend service.

## Database Models

### Core Models

1. **Source**: Metadata của nguồn dữ liệu
2. **SourceRedmineIssue**: Chi tiết Redmine issue
3. **SourceRedmineWiki**: Chi tiết Wiki page
4. **SourceGitFile**: Chi tiết Git file
5. **SourceDocument**: Chi tiết Document
6. **Chunk**: Text chunks
7. **Embedding**: Vector embeddings

### Management Models

8. **ScheduledJob**: Job configurations
9. **JobExecution**: Execution history
10. **SearchLog**: Search query logs (cho analytics)
11. **OpenAIUsageLog**: Usage tracking
12. **OpenAIUsageLogDetail**: Detailed usage logs (prompt, response)
13. **OpenAIConfig**: Model pricing config
14. **User**: User accounts (cho authentication)

**Chi tiết**: Xem [Database Schema](./vector_DB.plantuml)

## Configuration

### Environment Variables

```bash
# Application
APP_NAME=RAG System
APP_VERSION=1.0.0
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/dbname

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Embedding
EMBEDDING_MODEL=intfloat/multilingual-e5-large

# Redmine
REDMINE_URL=https://redmine.example.com
REDMINE_API_KEY=...
REDMINE_API_DELAY=0.2  # Delay giữa các API calls (giây)

# Scheduler
SCHEDULER_TIMEZONE=Asia/Ho_Chi_Minh
DEFAULT_SYNC_CRON=0 2 * * *
BACKEND_API_URL=http://backend:8000  # URL cho scheduler gọi backend API

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Email (optional)
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
BUDGET_ALERT_EMAIL_RECIPIENTS=...
```


## Deployment

### Docker Compose

```yaml
services:
  backend:
    build:
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      # ...
  
  scheduler:
    build:
      dockerfile: Dockerfile.backend
    command: python -m app.schedulers.job_scheduler
    # ...
```

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "openai_model": "gpt-4o-mini"
}
```


## Tài liệu Liên quan

- [Architecture Overview](./architecture_overview.md)
- [Frontend Documentation](./frontend_redmine_assistant.md)
- [Database Schema](./vector_DB.plantuml)
- [README](../../README.md)
- [RAG Search Sequence Diagram](./rag_search_sequence.md) - Flow tìm kiếm RAG với AI
- [Find Related Issues Sequence Diagram](./find_related_issues_sequence.md) - Flow tìm issues liên quan
- [Create Draft Note Sequence Diagram](./create_draft_note_sequence.md) - Flow tạo draft note với checklist

