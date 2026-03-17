# 🚀 RAG System - Retrieval-Augmented Generation

Hệ thống RAG (Retrieval-Augmented Generation) để tìm kiếm và truy vấn thông minh trên dữ liệu từ Redmine, Git, và tài liệu nội bộ.

## 📋 Tính năng

- ✅ **Multi-source Ingestion**: Redmine Issues/Wiki, Git Repository, Internal Documents (PDF, DOCX)
- ✅ **Vector Search**: Tìm kiếm ngữ nghĩa với PostgreSQL + pgvector
- ✅ **RAG Chat**: Chat với AI agent dựa trên dữ liệu của bạn
- ✅ **Job Scheduler**: Tự động sync dữ liệu từ Redmine theo lịch
- ✅ **Monitoring Dashboard**: Theo dõi metrics và hiệu suất hệ thống
- ✅ **Web UI**: Streamlit interface thân thiện

## 🏗️ Kiến trúc

```text
┌─────────────────┐
│  Data Sources   │
│ Redmine │ Git   │
│   Documents     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit UI   │
│ Upload│Search   │
│  Jobs │Monitor  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │
│  Backend        │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────┐
│PG+     │ │  OpenAI  │
│pgvector│ │   API    │
└────────┘ └──────────┘
         │
         ▼
┌─────────────────┐
│  Scheduler      │
│  Service        │
└─────────────────┘
```

**Services:**
- `postgres`: PostgreSQL + pgvector
- `redis`: Redis cache
- `backend`: FastAPI application
- `streamlit`: Streamlit UI
- `scheduler`: Job scheduler service (APScheduler)

## 🧱 Data Model

- `source` là bảng trung tâm, lưu metadata chung và `sha1_content` để phát hiện trùng lặp.
- `chunk` liên kết trực tiếp với `source`, có trạng thái xử lý (`pending`, `processed`, `failed`, `archived`) và timestamps `created_at/updated_at`.
- `embedding` gắn với từng `chunk`, theo dõi trạng thái (`active`, `outdated`, `regenerating`) để biết cần tái sinh hay không.

## 🛠️ Tech Stack

- **Vector DB**: PostgreSQL 15 + pgvector
- **LLM**: OpenAI API (GPT-4o-mini, GPT-4, etc.)
- **Embeddings**: sentence-transformers (mixedbread-ai/mxbai-embed-large-v1)
- **Framework**: LangChain
- **Backend**: FastAPI
- **UI**: Streamlit
- **Scheduler**: APScheduler
- **Cache**: Redis

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB+ RAM
- OpenAI API key (get from https://platform.openai.com)
- 10GB+ disk space

### 1. Cài đặt tự động

```bash
# Clone repository
git clone https://git-2.1steam.com/ait/ai-agent/redmine-data.git
cd redmine-data

# Chạy script setup
chmod +x setup.sh
./setup.sh
```

Script sẽ tự động:
- ✅ Kiểm tra Docker và Docker Compose đã cài đặt
- ✅ Tạo file `.env` từ `.env.example` (nếu chưa có)
- ✅ Tạo các thư mục cần thiết (uploads, scripts, tests, ...)
- ✅ Build Docker images cho backend và streamlit
- ✅ Start tất cả services (PostgreSQL, Redis, Backend, Streamlit, Scheduler)
- ✅ Kiểm tra và đợi services sẵn sàng
- ✅ Initialize database schema

**Lưu ý:** Sau khi setup, bạn cần:
1. Sửa file `.env` và thêm `OPENAI_API_KEY` của bạn
2. Vào Streamlit UI → tab **⚙️ OpenAI Config** → Sync default pricing và set default model
3. Cấu hình `REDMINE_URL` và `REDMINE_API_KEY` nếu cần sync từ Redmine

### 2. Access hệ thống

- **Streamlit UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

### 3. Configuration

Sửa file `.env`:

```bash
# OpenAI (Required)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini  # Fallback model (model thực tế được lưu trong DB)

# Embedding Model
EMBEDDING_MODEL=mixedbread-ai/mxbai-embed-large-v1

# Redmine
REDMINE_URL=https://your-redmine.com
REDMINE_API_KEY=your_api_key

# Git (if needed)
GIT_USERNAME=your_username
GIT_TOKEN=your_token

# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/rag_db
REDIS_URL=redis://redis:6379/0
```

**Lưu ý về OpenAI Model:**
- `OPENAI_MODEL` trong `.env` chỉ là giá trị fallback khi chưa có model nào được set trong database
- **Model thực tế được lưu trong database** (bảng `openai_config` với `is_default=True`)
- Sau khi setup, vào tab **⚙️ OpenAI Config** trong Streamlit UI để:
  - Sync default pricing từ hệ thống
  - Chọn và set default model
  - Quản lý pricing cho từng model

## 📖 Hướng dẫn sử dụng

### Upload dữ liệu

1. Vào tab **📤 Upload**
2. Chọn source type: Redmine/Git/Document
3. Upload file hoặc nhập URL
4. Click **Process**

### Tìm kiếm

1. Vào tab **🔍 Search**
2. Nhập query vào search box
3. Sử dụng filters (project, date, source type)
4. Toggle "AI Answer" để chat với RAG

### Cấu hình Job Scheduler

1. Vào tab **⚙️ Jobs**
2. Click "Add New Job"
3. Nhập:
   - Job name
   - Cron expression (vd: `0 2 * * *` cho 2AM hàng ngày)
   - Redmine project ID
   - Sync settings
4. Save và enable job

### Monitor

1. Vào tab **📊 Monitor**
2. Xem:
   - Source statistics
   - Processing performance
   - Search analytics
   - OpenAI usage tracking
   - Error logs

### Quản lý Sources

1. Vào tab **📁 Sources**
2. Xem danh sách sources
3. Check source status
4. Resync source nếu cần

### Cấu hình OpenAI

1. Vào tab **⚙️ OpenAI Config**
2. Quản lý model configurations
3. Set pricing cho từng model
4. Set default model
5. Xem usage statistics

## 🔧 Commands

```bash
# Start/Stop
make up              # Start all services
make down            # Stop all services
make restart         # Restart services

# Logs
make logs            # All logs
make logs-backend    # Backend logs
make logs-streamlit  # Streamlit logs
make logs-scheduler  # Scheduler logs

# Database
make db-shell        # PostgreSQL shell
make db-reset        # Reset database
make backup-db       # Backup database

# Development
make dev             # Start with hot reload

# Stats
make stats           # Show statistics
make ps              # Show containers
```

## 📂 Project Structure

```text
rag-system/
├── app/
│   ├── main.py              # FastAPI app
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── config.py            # Configuration
│   │
│   ├── services/
│   │   ├── extractor.py           # Content extraction
│   │   ├── chunker.py             # Text chunking
│   │   ├── embedder.py            # Embedding generation
│   │   ├── retriever.py           # Vector search
│   │   ├── rag_chain.py           # RAG pipeline
│   │   ├── redmine_sync.py        # Redmine sync
│   │   ├── git_sync.py            # Git sync
│   │   ├── cache.py               # Redis caching
│   │   ├── check_source.py        # Source validation
│   │   ├── job_executor.py        # Job execution
│   │   ├── openai_config_service.py # OpenAI config management
│   │   └── openai_usage_tracker.py  # Usage tracking
│   │
│   ├── schedulers/
│   │   └── job_scheduler.py # APScheduler
│   │
│   └── api/
│       ├── ingest.py        # Upload endpoints
│       ├── search.py        # Search endpoints
│       ├── jobs.py          # Job management
│       └── openai_config.py # OpenAI config endpoints
│
├── streamlit_app/
│   ├── Home.py              # Main page
│   └── pages/
│       ├── upload.py        # Upload documents
│       ├── search.py        # Search interface
│       ├── jobs.py          # Job scheduler
│       ├── monitors.py      # Monitoring dashboard
│       ├── sources.py       # Source management
│       └── openai_config.py # OpenAI configuration
│
├── scripts/
│   ├── init_db.sql          # Database schema
│   └── seed_data.py         # Sample data
│
├── docker-compose.yml       # Main compose file
├── docker-compose.dev.yml   # Dev overrides
├── Dockerfile.backend
├── Dockerfile.streamlit
├── requirements.txt
├── Makefile
└── setup.sh
```

## 🔍 API Endpoints

### Ingestion

```bash
POST   /api/ingest/manual
POST   /api/ingest/redmine
POST   /api/ingest/redmine/wiki
POST   /api/ingest/redmine/wiki/project
GET    /api/ingest/status/{job_id}
GET    /api/ingest/stats
GET    /api/ingest/sources
POST   /api/ingest/sources/{source_id}/check
POST   /api/ingest/sources/{source_id}/resync
```

### Search

```bash
POST   /api/search/vector
POST   /api/search/rag
GET    /api/search/history
GET    /api/search/analytics
GET    /api/search/usage
DELETE /api/search/cache
GET    /api/search/cache/stats
```

### Jobs

```bash
GET    /api/jobs
POST   /api/jobs
GET    /api/jobs/{job_id}
PUT    /api/jobs/{job_id}
DELETE /api/jobs/{job_id}
POST   /api/jobs/{job_id}/run
GET    /api/jobs/{job_id}/history
```

### OpenAI Configuration

```bash
GET    /api/openai-config
GET    /api/openai-config/{model_name}
POST   /api/openai-config
PUT    /api/openai-config/{model_name}
DELETE /api/openai-config/{model_name}
GET    /api/openai-config/default-model
POST   /api/openai-config/default-model/{model_name}
POST   /api/openai-config/sync-defaults
```

## 🎯 OpenAI Configuration

### Model Storage

**Quan trọng:** Model được lưu trong **database**, không phải trong `.env` file.

- Hệ thống ưu tiên lấy model từ database (bảng `openai_config` với `is_default=True`)
- `OPENAI_MODEL` trong `.env` chỉ là fallback khi chưa có model nào trong DB
- Model và pricing được quản lý qua database để dễ dàng thay đổi mà không cần restart

### Supported Models

Hệ thống hỗ trợ các model OpenAI:
- `gpt-4o-mini` - Recommended, cost-effective (default)
- `gpt-4o` - Better quality, higher cost
- `gpt-4-turbo` - High quality
- `gpt-3.5-turbo` - Fast, lower cost

### Embedding Models

- `mixedbread-ai/mxbai-embed-large-v1` - Default, high quality
- `sentence-transformers/all-MiniLM-L6-v2` - Faster, smaller

### Configure Model

1. **Via Streamlit UI (Recommended):**
   - Vào tab **⚙️ OpenAI Config**
   - Click "Sync Default Pricing" để tạo các model configs mặc định
   - Chọn model và click "Set as Default"
   - Model sẽ được lưu vào database và sử dụng ngay

2. **Via API:**
   ```bash
   # Sync default pricing (tạo các model configs)
   POST /api/openai-config/sync-defaults
   
   # Set default model
   POST /api/openai-config/default-model/{model_name}
   
   # Create/Update config
   POST /api/openai-config
   {
     "model_name": "gpt-4o",
     "input_price_per_1m": 2.50,
     "output_price_per_1m": 10.00,
     "is_active": true
   }
   ```

3. **Fallback via .env:**
   ```bash
   # Chỉ dùng khi chưa có model nào trong DB
   OPENAI_MODEL=gpt-4o-mini
   EMBEDDING_MODEL=mixedbread-ai/mxbai-embed-large-v1
   ```

## 🐛 Troubleshooting

### Services không start

```bash
# Check logs
make logs

# Restart
make down && make up
```

### OpenAI API errors

```bash
# Check API key
echo $OPENAI_API_KEY

# Check usage limits
# Visit OpenAI dashboard: https://platform.openai.com/usage

# Use cheaper model
OPENAI_MODEL=gpt-4o-mini  # instead of gpt-4o
```

### PostgreSQL connection error

```bash
# Check database
make db-shell

# Reset database
make db-reset
```

### Slow embedding generation

```bash
# Use lighter embedding model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Or adjust chunk size
CHUNK_SIZE=256  # Smaller chunks = faster processing
```

## 📊 Performance Tips

1. **Chunking**: Adjust `CHUNK_SIZE` in .env (default: 512)
2. **Top K**: Reduce `SIMILARITY_TOP_K` (default: 5)
3. **Batch size**: Process multiple files together
4. **Index**: pgvector IVFFlat index tự động tối ưu

## 🔒 Security

- Không commit file `.env`
- Dùng strong passwords
- Limit API access với authentication
- Regularly backup database
