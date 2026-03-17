# 🏗️ Tổng quan Kiến trúc Hệ thống AI-Redmine

## Giới thiệu

Hệ thống AI-Redmine là một giải pháp RAG (Retrieval-Augmented Generation) tích hợp với Redmine, cho phép tìm kiếm thông minh và trả lời câu hỏi dựa trên dữ liệu từ Redmine Issues, Wiki, Git repositories và các tài liệu nội bộ.

## Kiến trúc Tổng thể

```
┌─────────────────────────────┐
│   Frontend                  │
│   Redmine Assistant         │
│   (Redmine Plugin)          │
└──────────┬──────────────────┘
           │ HTTP API
           ▼
┌─────────────────────────────┐
│   Backend                    │
│   FastAPI (redmine-data)     │
│   - Auth API                 │
│   - Search API               │
│   - Ingestion API            │
│   - Jobs API                 │
│   - OpenAI Config API        │
└──────────┬──────────────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
┌────────┐ ┌────┐ ┌─────────┐
│Postgres│ │Redis│ │ OpenAI  │
│+pgvector│ │Cache│ │   API   │
└────────┘ └────┘ └─────────┘
```

### Mô tả các Thành phần trong Sơ đồ

#### 1. Frontend - Redmine Assistant

**Vai trò**: Giao diện người dùng tích hợp vào Redmine

- **Technology**: Redmine Plugin (Ruby on Rails)
- **Location**: `redmine-assistant/plugins/custom_features/`
- **Components**:
  - Custom Search Box trong header
  - Custom Search Page với AI chat
  - Search Client để gọi backend API
- **Communication**: HTTP REST API đến Backend

> **Chi tiết**: Xem [Frontend Documentation](./frontend_redmine_assistant.md)

#### 2. Backend - FastAPI (redmine-data)

**Vai trò**: Xử lý logic nghiệp vụ và cung cấp APIs

- **Technology**: FastAPI (Python)
- **Location**: `redmine-data/app/`
- **API Groups**:
  - **Auth API** (`/api/auth/*`): Xác thực người dùng và quản lý session
  - **Search API** (`/api/search/*`): Vector search, RAG search, related issues, analytics
  - **Ingestion API** (`/api/ingest/*`): Đồng bộ dữ liệu từ Redmine, Git, Documents, source management
  - **Jobs API** (`/api/jobs/*`): Quản lý scheduled jobs
  - **OpenAI Config API** (`/api/openai-config/*`): Quản lý model configurations và pricing
  - **Budget API** (`/api/budget/*`): Quản lý budget, alerts và monitoring chi phí LLM
- **Services**: Retriever, RAG Chain, Sync Services, Job Executor, etc.

> **Chi tiết**: Xem [Backend Documentation](./backend_redmine_data.md)

#### 3. PostgreSQL + pgvector

**Vai trò**: Lưu trữ dữ liệu và vector embeddings

- **Technology**: PostgreSQL 15 với pgvector extension
- **Data Stored**:
  - Sources, Chunks, Embeddings (cho vector search)
  - Scheduled Jobs, Job Executions
  - Search Logs, OpenAI Usage Logs
  - OpenAI Config
  - Users (cho authentication)
- **Features**: Vector similarity search, full-text search indexes

> **Chi tiết**: Xem [Database Schema](./vector_DB.plantuml)

#### 4. Redis

**Vai trò**: Caching layer để tối ưu performance

- **Technology**: Redis 7
- **Usage**:
  - Cache RAG responses (TTL: 24h)
  - Cache statistics
  - Optional: Job queue
- **Optional**: System vẫn hoạt động nếu Redis down

#### 5. LLM Providers

**Vai trò**: LLM service cho AI features

- **Supported Providers**: 
  - **OpenAI**: GPT-4o, GPT-4o-mini, GPT-4-turbo, etc.
  - **Google Gemini**: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp
  - **Anthropic Claude**: claude-3-5-sonnet, claude-3-opus, claude-3-haiku
  - **Groq**: llama-3.3-70b, llama-3.1-70b, mixtral-8x7b, etc.
- **Usage**: Generate AI answers trong RAG search, create draft notes
- **Cost Tracking**: Tự động log usage và costs cho tất cả providers
- **Budget Management**: Theo dõi chi phí, cảnh báo khi vượt ngưỡng
- **Authentication**: API keys từ environment variables

> **Chi tiết**: Xem [Backend Documentation - Monitoring](./backend_redmine_data.md#monitoring--observability)

## Các Thành phần Chính

| Thành phần | Vai trò | Tài liệu Chi tiết |
|------------|---------|-------------------|
| **Frontend** | Giao diện người dùng trong Redmine | [Frontend Documentation](./frontend_redmine_assistant.md) |
| **Backend** | Xử lý dữ liệu, ingestion, jobs | [Backend Documentation](./backend_redmine_data.md) |
| **Database** | Lưu trữ dữ liệu và vector embeddings | [Database Schema](./vector_DB.plantuml) |
| **Cache** | Caching RAG responses | [Backend Documentation](./backend_redmine_data.md) |
| **LLM Providers** | Multiple LLM services (OpenAI, Google, Anthropic, Groq) | [Backend Documentation](./backend_redmine_data.md) |

## Luồng Dữ liệu Chính

### 1. Data Ingestion
```
Sources → Extract → Chunk → Embed → Database
```
> **Chi tiết**: Xem [Backend Documentation - Data Processing Flow](./backend_redmine_data.md#data-processing-flow)

### 2. Search Flow
```
User Query → Frontend → Backend API → Vector Search → RAG → AI Answer
```
> **Chi tiết**: Xem [Frontend Documentation - User Search Flow](./frontend_redmine_assistant.md#1-user-search-flow)

### 3. Job Scheduling
```
Scheduler → Load Jobs → Execute → Log Results
```
> **Chi tiết**: Xem [Backend Documentation - Job Execution Flow](./backend_redmine_data.md#job-execution-flow)

## Deployment

**Docker Compose Services**:
- `postgres`: PostgreSQL + pgvector
- `redis`: Cache layer
- `backend`: FastAPI service (Main API)
- `streamlit`: Streamlit UI (Admin dashboard)
- `scheduler`: Job scheduler service (Lightweight)

**Network**: Services giao tiếp qua Docker network, frontend-backend qua HTTP REST API

> **Chi tiết**: Xem [Backend Documentation - Deployment](./backend_redmine_data.md#deployment)

## Security & Monitoring

- **Authentication**: API keys cho Redmine và OpenAI
- **Network**: Docker network isolation, CORS configuration
- **Privacy**: Data stored locally, only queries sent to OpenAI
- **Monitoring**: Application logs, usage tracking, job execution logs

> **Chi tiết**: Xem [Backend Documentation - Monitoring](./backend_redmine_data.md#monitoring--observability)

## Technology Stack Summary

| Component | Technology |
|-----------|-----------|
| Frontend | Redmine Plugin (Ruby on Rails) |
| Backend API | FastAPI (Python) |
| Database | PostgreSQL 15 + pgvector |
| Cache | Redis 7 |
| LLM | OpenAI, Google Gemini, Anthropic Claude, Groq |
| Admin UI | Streamlit |
| Embedding | intfloat/multilingual-e5-large (xem [Backend Docs - Embedding Model](./backend_redmine_data.md#embedding-model-lựa-chọn-và-so-sánh)) |
| Job Scheduler | APScheduler |
| Containerization | Docker & Docker Compose |

## Tài liệu Liên quan

- [Frontend Documentation](./frontend_redmine_assistant.md)
- [Backend Documentation](./backend_redmine_data.md)
- [Database Schema](./vector_DB.plantuml)

