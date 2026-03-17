# 🎨 Frontend: Redmine Assistant

## Tổng quan

**Redmine Assistant** là một Redmine plugin cung cấp giao diện tìm kiếm thông minh tích hợp vào Redmine, cho phép người dùng tìm kiếm và tương tác với AI assistant trực tiếp trong môi trường Redmine.

## Mục lục

- [Tổng quan](#tổng-quan)
- [Vị trí trong Hệ thống](#vị-trí-trong-hệ-thống)
- [Cấu trúc Plugin](#cấu-trúc-plugin)
- [Tính năng Chính](#tính-năng-chính)
  - [Search (Tìm kiếm AI)](#1-search-tìm-kiếm-ai)
  - [Create Draft Note](#2-create-draft-note)
  - [Find Related Issues](#3-find-related-issues)
- [Luồng Hoạt động](#luồng-hoạt-động)
  - [User Search Flow](#1-user-search-flow)
  - [Search Client Request Flow](#2-search-client-request-flow)
- [API Integration](#api-integration)
  - [Routes](#routes)
  - [Backend API Endpoints được sử dụng](#backend-api-endpoints-được-sử-dụng)
- [Configuration](#configuration)
  - [Plugin Settings](#plugin-settings)
  - [Environment Variables](#environment-variables)
- [Deployment](#deployment)
  - [Installation](#installation)
  - [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
  - [Search không hoạt động](#search-không-hoạt-động)
  - [Results không hiển thị](#results-không-hiển-thị)
- [Best Practices](#best-practices)
- [Tài liệu Liên quan](#tài-liệu-liên-quan)

## Vị trí trong Hệ thống

```
┌─────────────────────────────────────┐
│      Redmine (5.1.2)               │
│  ┌───────────────────────────────┐  │
│  │  Custom Features Plugin      │  │
│  │  (redmine-assistant)         │  │
│  │                              │  │
│  │  - Custom Search Box         │  │
│  │  - Custom Search Page        │  │
│  │  - Search Client             │  │
│  └───────────┬─────────────────┘  │
└───────────────┼───────────────────┘
                 │ HTTP REST API
                 │ (GET/POST /api/search/*)
                 ▼
┌─────────────────────────────────────────────────────┐
│         FastAPI Backend (redmine-data)              │
│         Search API Layer                            │
│  ┌───────────────────────────────────────────────┐  │
│  │  /api/search/*                               │  │
│  │  ┌─────────────────────────────────────────┐ │  │
│  │  │  POST /rag              → RAG Search   │ │  │
│  │  │                         (AI Answer)     │ │  │
│  │  └─────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────┐ │  │
│  │  │  GET /issues/{id}/related → Related     │ │  │
│  │  │                         Issues (Vector) │ │  │
│  │  └─────────────────────────────────────────┘ │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │                               │
│  ┌───────────────────▼───────────────────────────┐  │
│  │  Search Services Layer                        │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Retriever Service                       │  │  │
│  │  │  • Vector similarity search              │  │  │
│  │  │  • Reranking & diversity filtering       │  │  │
│  │  │  • Filter by project/source/language    │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  RAG Chain Service                       │  │  │
│  │  │  • Build context from chunks             │  │  │
│  │  │  • Create LLM prompt                    │  │  │
│  │  │  • Call OpenAI API                       │  │  │
│  │  │  • Generate AI answer                    │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Cache Service (Redis)                    │  │  │
│  │  │  • Cache RAG responses (24h TTL)          │  │  │
│  │  │  • Reduce OpenAI API costs              │  │  │
│  │  │  • Cache statistics                     │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Usage Tracker                          │  │  │
│  │  │  • Log search requests                  │  │  │
│  │  │  • Track OpenAI usage & costs           │  │  │
│  │  │  • Store in search_log table            │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────┬───────────────────────────┘  │
│                      │                               │
└──────────────────────┼───────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼──────┐ ┌─────▼──────┐
│  PostgreSQL  │ │   Redis   │ │  OpenAI    │
│  + pgvector  │ │  (Cache)  │ │    API     │
│              │ │           │ │            │
│  • Chunks    │ │  • RAG    │ │  • GPT-4o  │
│  • Embeddings│ │    Cache  │ │  • GPT-4o- │
│  • Sources   │ │  • Stats  │ │    mini    │
│  • Vector    │ │           │ │  • etc.    │
│    Search    │ │           │ │            │
└──────────────┘ └───────────┘ └────────────┘
```

> **Lưu ý**: Chi tiết về các thành phần và API endpoints được mô tả trong phần [Tính năng Chính](#tính-năng-chính), [Internal Services](#internal-services), và [API Integration](#api-integration). Chi tiết về Backend Services được mô tả trong [Backend Documentation](./backend_redmine_data.md).

## Cấu trúc Plugin

```
redmine-assistant/
└── plugins/
    └── custom_features/
        ├── init.rb                          # Plugin initialization
        ├── README.md                        # Plugin documentation
        │
        ├── app/
        │   ├── controllers/
        │   │   ├── custom_features/
        │   │   │   └── custom_features_controller.rb  # Draft note, related issues
        │   │   └── custom_search_controller.rb        # Search controller
        │   │
        │   └── views/
        │       ├── custom_features/
        │       │   └── hooks/
        │       │       └── _view_issues_related_custom.html.erb
        │       └── custom_search/
        │           └── index.html.erb       # Main search page
        │
        ├── lib/
        │   └── custom_features/
        │       ├── config.rb                # Configuration management
        │       ├── constants.rb             # Constants và messages
        │       ├── errors.rb                # Custom error classes
        │       ├── hooks.rb                 # View hooks registration
        │       ├── search_client.rb          # HTTP client to backend API
        │       │
        │       ├── services/
        │       │   ├── checklist_generator.rb    # Generate checklist với AI
        │       │   ├── checklist_parser.rb      # Parse checklist từ AI response
        │       │   ├── issue_content_builder.rb  # Build issue content cho AI
        │       │   └── related_issues_finder.rb  # Find related issues với AI
        │       │
        │       └── formatters/
        │           ├── issue_formatter.rb        # Format issue data
        │           └── search_result_formatter.rb # Format search results
        │
        ├── assets/
        │   ├── stylesheets/
        │   │   └── custom_features.css      # Custom styling
        │   └── javascripts/
        │       └── custom_features/
        │           ├── main.js              # Main JavaScript
        │           ├── search.js            # Search functionality
        │           ├── checklist.js         # Checklist functionality
        │           ├── auto_link.js         # Auto-link functionality
        │           └── utils.js             # Utility functions
        │
        └── config/
            └── routes.rb                    # Plugin routes
```

## Tính năng Chính

Frontend plugin cung cấp **3 tính năng chính** cho người dùng:

### 1. Search (Tìm kiếm AI)

Tính năng tìm kiếm thông minh với AI, bao gồm 2 components:

#### Custom Search Box
**Vị trí**: Header của Redmine, bên cạnh search box mặc định

**Chức năng**:
- Nhập từ khóa tìm kiếm
- Tự động lấy project context từ URL
- Gửi request đến backend API
- Navigate đến Custom Search Page với query

**Implementation**:
- Hook: `view_layouts_base_html_head`
- Partial: `app/views/custom_features/hooks/_custom_search_box.html.erb`
- JavaScript: Xử lý form submission và navigation

#### Custom Search Page
**Route**: `/custom_search` hoặc `/custom_search/index`

**Chức năng**:
- Giao diện tìm kiếm đầy đủ
- Hiển thị AI answer và sources từ RAG search
- Tích hợp AI chat (RAG)
- Filters: project, source type, language

**Controller**: `CustomSearchController`

**View**: `app/views/custom_search/index.html.erb`

**API Endpoint**: `POST /api/search/rag`

### 2. Create Draft Note

**Route**: `POST /issues/:issue_id/create_draft_note`

**Chức năng**:
- Tạo draft note (journal entry) với AI-generated checklist
- Phân tích issue và tạo checklist phù hợp
- Gọi AI trực tiếp với prompt đã có (không có vector search hay reranking)
- Báo lỗi và không tạo note nếu AI không tạo được checklist

**Controller**: `CustomFeatures::CustomFeaturesController#create_draft_note`

**API Endpoint**: `POST /api/search/generate`

**Sequence Diagram**: Xem [Create Draft Note Sequence](./create_draft_note_sequence.md) để hiểu chi tiết flow.

### 3. Find Related Issues

**Route**: `GET /issues/:issue_id/find_related_issues`

**Chức năng**:
- Tìm các issues liên quan đến issue hiện tại
- Sử dụng vector embedding similarity search
- Loại trừ issues đã có quan hệ
- Hiển thị trong view hook `_view_issues_related_custom.html.erb`

**Controller**: `CustomFeatures::CustomFeaturesController#find_related_issues`

**Service**: `CustomFeatures::Services::RelatedIssuesFinder`

**API Endpoint**: `GET /api/search/issues/{issue_id}/related?top_k=20`

**Response Format**:
```json
{
  "success": true,
  "related_issues": [
    {
      "issue_id": 456,
      "similarity_score": 0.85,
      "similarity_percentage": 85.0,
      "subject": "Related issue subject",
      "project": {...},
      "status": "...",
      "url": "..."
    }
  ],
  "count": 5
}
```

**Sequence Diagram**: Xem [Find Related Issues Sequence](./find_related_issues_sequence.md) để hiểu chi tiết flow.

## Luồng Hoạt động

### 1. User Search Flow

```
User nhập query
        │
        ▼
┌──────────────────────┐
│  Custom Search Box   │  (Header)
│  hoặc Search Page    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  JavaScript Handler  │  Submit form
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  CustomSearchController│  Process request
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  SearchClient        │  HTTP request
│  .rag_search()       │
└──────────┬───────────┘
           │
           │ HTTP POST/GET
           ▼
┌──────────────────────┐
│  FastAPI Backend      │
│  /api/search/*       │
└──────────┬───────────┘
           │
           │ JSON Response
           ▼
┌──────────────────────┐
│  Display Results      │  Render in ERB
│  (View Template)      │
└──────────────────────┘
```

## Internal Services

Các service classes hỗ trợ bên trong plugin (không phải tính năng trực tiếp cho người dùng):

### SearchClient

**Class**: `CustomFeatures::SearchClient`

**Chức năng**: HTTP client để giao tiếp với FastAPI backend

**Pattern**: Singleton pattern (`SearchClient.instance`)

**Methods**:
- `rag_search(query:)`: RAG search với AI (có vector search và reranking)
  - Input: `query` (String)
  - Output: Hash với `answer`, `sources`, `retrieved_chunks`, `cached`, `response_time_ms`
  - Endpoint: `POST /api/search/rag`
  - **Sử dụng**: User search trong frontend
- `generate_text(prompt:)`: Generate text bằng AI trực tiếp (không có retrieval)
  - Input: `prompt` (String) - Prompt đầy đủ đã được build
  - Output: Hash với `answer`, `sources` (empty), `retrieved_chunks` (empty), `cached`, `response_time_ms`
  - Endpoint: `POST /api/search/generate`
  - **Sử dụng**: Checklist generation (không cần vector search)
- `find_related_issues(issue_id:, top_k:)`: Tìm related issues
  - Input: `issue_id` (Integer), `top_k` (Integer, default: 20)
  - Output: Hash với `related_issues`, `count`, `response_time_ms`
  - Endpoint: `GET /api/search/issues/{issue_id}/related?top_k={top_k}`

**Configuration**:
- Base URL được lấy từ (theo thứ tự ưu tiên):
  1. Parameter `base_url` khi khởi tạo (optional)
  2. Plugin settings (`rag_api_base_url`)
  3. Environment variable (`RAG_SEARCH_API_BASE` hoặc `RAG_BACKEND_URL`)
  4. Default: `http://backend:8000`
- Timeout: 360 seconds (DEFAULT_TIMEOUT)
- Headers: `Content-Type: application/json`, `Accept: application/json`

**Error Handling**:
- `SearchError`: Custom error class cho search-related errors
- JSON parsing errors → `SearchError` với message
- HTTP errors → `SearchError` với status code và detail
- Network errors → `SearchError` với connection message
- Logging: Chi tiết request/response trong Rails logger

**Dependencies**: Được sử dụng bởi `ChecklistGenerator`, `RelatedIssuesFinder`, và các controllers

### Các Services khác

Các service classes hỗ trợ khác được sử dụng bởi các tính năng chính:

- **`ChecklistGenerator`**: Tạo checklist cho issue sử dụng AI trực tiếp (không có vector search), build prompt từ issue data, gọi `generate_text` API, parse checklist từ AI response. Nếu AI không tạo được hoặc parse thất bại, raise error và không tạo note
- **`ChecklistParser`**: Parse checklist từ AI response text, extract checklist items từ markdown hoặc plain text
- **`IssueContentBuilder`**: Xây dựng nội dung issue cho phân tích AI, collect và format issue data
- **`RelatedIssuesFinder`**: Tìm issues liên quan sử dụng AI service, loại trừ issues đã có quan hệ, format và normalize API response

> **Lưu ý**: Chi tiết implementation của các services này có thể xem trong source code tại `lib/custom_features/services/`.

## API Integration

### Routes

**Plugin Routes** (`config/routes.rb`):
- `GET /custom_search` → `CustomSearchController#index`
- `POST /custom_search` → `CustomSearchController#search`
- `POST /issues/:issue_id/create_draft_note` → `CustomFeatures::CustomFeaturesController#create_draft_note`
- `GET /issues/:issue_id/find_related_issues` → `CustomFeatures::CustomFeaturesController#find_related_issues`

### Backend API Endpoints được sử dụng

1. **RAG Search**
   - `POST /api/search/rag`
   - Payload: `{ query }`
   - Response: `{ query, answer, sources[], retrieved_chunks[], cached, response_time_ms }`
   - **Sử dụng**: Mode mặc định trong frontend (mode = 'rag')
   - **Controller**: `CustomSearchController#perform_rag_search`
   - **Features**: Vector search, reranking, và AI generation với context

2. **Generate Text** (AI generation không có retrieval)
   - `POST /api/search/generate`
   - Payload: `{ prompt }`
   - Response: `{ prompt, answer, sources[] (empty), retrieved_chunks[] (empty), cached, response_time_ms }`
   - **Sử dụng**: Checklist generation trong Create Draft Note
   - **Service**: `ChecklistGenerator#generate_with_ai`
   - **Features**: Gọi AI trực tiếp với prompt, bỏ qua vector search và reranking

3. **Find Related Issues**
   - `GET /api/search/issues/{issue_id}/related?top_k=20`
   - Response: `{ issue_id, related_issues[], count, response_time_ms }`
   - **Sử dụng**: Tìm issues liên quan trong issue detail page
   - **Controller**: `CustomFeatures::CustomFeaturesController#find_related_issues`
   - **Service**: `CustomFeatures::Services::RelatedIssuesFinder`

## Configuration

### Plugin Settings

Cấu hình trong Redmine Admin → Plugins → Custom Features:

- `rag_api_base_url`: Backend API base URL
- Các settings khác (nếu có)

### Environment Variables

- `RAG_SEARCH_API_BASE`: Backend URL
- `RAG_BACKEND_URL`: Alternative backend URL

## Deployment

### Installation

1. Mount plugin trong `docker-compose.yml`:
   ```yaml
   volumes:
     - ./plugins:/usr/src/redmine/plugins
   ```

2. Restart Redmine:
   ```bash
   docker compose restart redmine
   ```

3. Plugin tự động được nhận diện và kích hoạt

### Requirements

- Redmine 5.1.2+
- Ruby on Rails (included in Redmine)
- Network access đến FastAPI backend

## Troubleshooting

### Search không hoạt động

1. **Check Backend URL**:
   - Verify plugin settings
   - Check environment variables
   - Test backend connectivity

2. **Check Logs**:
   - Redmine logs: `docker compose logs redmine`
   - Search for `[SearchClient]` messages

3. **Network Issues**:
   - Verify Docker network
   - Check firewall rules
   - Test backend health: `curl http://backend:8000/health`

### Results không hiển thị

1. Check JavaScript console
2. Verify JSON response format
3. Check ERB template rendering
4. Verify CSS styling

## Best Practices

1. **Error Handling**: Luôn wrap API calls trong try-catch
2. **Logging**: Log requests và responses để debug
3. **User Experience**: Hiển thị loading states
4. **Performance**: Cache results khi có thể
5. **Security**: Sanitize user input trước khi gửi API

## Tài liệu Liên quan

- [Architecture Overview](./architecture_overview.md)
- [Backend Documentation](./backend_redmine_data.md)
- [Plugin README](../../redmine-assistant/plugins/custom_features/README.md)
- [RAG Search Sequence Diagram](./rag_search_sequence.md) - Flow tìm kiếm RAG với AI
- [Find Related Issues Sequence Diagram](./find_related_issues_sequence.md) - Flow tìm issues liên quan
- [Create Draft Note Sequence Diagram](./create_draft_note_sequence.md) - Flow tạo draft note với checklist

