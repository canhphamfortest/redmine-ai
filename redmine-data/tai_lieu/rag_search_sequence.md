# RAG Search Sequence Diagram

Tài liệu mô tả quy trình tìm kiếm RAG (Retrieval-Augmented Generation) bằng sơ đồ tuần tự.

## Sơ đồ tuần tự (Mermaid)

```mermaid
sequenceDiagram
    actor Client
    participant API as API<br/>/search/rag
    participant Cache as Cache<br/>(Redis)
    participant RAG as RAGChain
    participant Retriever
    participant Embedder
    participant DB as Database<br/>(PostgreSQL)
    participant OpenAI as OpenAI API
    participant Tracker as UsageTracker
    participant Log as SearchLog

    Note over Client,Log: Request Phase
    Client->>API: POST /api/search/rag<br/>{query}

    Note over API,Cache: Cache Check Phase
    API->>+Cache: get_rag_response(query)
    Cache-->>-API: cached_response or null

    alt Cache Hit
        API->>+Tracker: log_usage(cached=True)
        Tracker->>DB: Save usage log
        Tracker-->>-API: Success
        API-->>Client: Return cached response
    else Cache Miss
        Note over API,RAG: Retrieval Phase
        API->>RAG: generate_answer(query)
        
        RAG->>+Retriever: search(query)
        
        Retriever->>+Embedder: embed(query)
        Note over Embedder: Generate embedding vector
        Embedder-->>-Retriever: query_embedding
        
        Retriever->>+DB: Vector similarity search<br/>(top_k candidates)
        DB-->>-Retriever: chunks
        
        Retriever-->>-RAG: chunks[]
        
        alt No Chunks Found
            RAG->>Cache: set_rag_response(empty, TTL=1h)
            RAG-->>API: Return empty response
        else Chunks Found
            Note over RAG: Context Building Phase
            Note over RAG: - Prioritize issue_metadata chunks<br/>- Format with source labels<br/>- Combine into context string
            RAG->>RAG: _build_context(chunks)
            
            Note over RAG: - Add system instructions<br/>- Include context<br/>- Add user query
            RAG->>RAG: _create_prompt(query, context)
            
            Note over RAG,OpenAI: Generation Phase
            RAG->>+OpenAI: chat.completions.create(prompt)
            Note over OpenAI: Process with LLM
            OpenAI-->>-RAG: answer + usage_info
            
            Note over RAG,Tracker: Logging Phase
            RAG->>+Tracker: log_usage(tokens, cost, time)
            Tracker->>DB: Save to openai_usage_log
            Tracker-->>-RAG: usage_log
            
            RAG->>+Tracker: log_usage_detail(prompt, response)
            Tracker->>DB: Save to openai_usage_log_detail
            Tracker-->>-RAG: Success
            
            Note over RAG: Response Preparation
            RAG->>RAG: _extract_sources(chunks)
            RAG->>RAG: Build response object
            
            Note over RAG,Cache: Caching Phase
            alt Successful Response
                RAG->>+Cache: set_rag_response(response, TTL=24h)
                Cache-->>-RAG: Success
            else Error Response
                Note over RAG: Skip caching error responses
            end
            
            RAG-->>API: {answer, sources, chunks, cached: false}
        end
        
        Note over API,Log: Search Logging
        API->>+Log: Create SearchLog entry
        Log->>DB: Save search_log
        Log-->>-API: Success
        
        API-->>Client: Return response<br/>{answer, sources, chunks, response_time}
    end
```

## Mô tả chi tiết các bước

### 1. Request Phase
- Client gửi POST request đến `/api/search/rag` với:
  - `query`: Câu hỏi của người dùng

### 2. Cache Check Phase
- API kiểm tra Redis cache trước
- Nếu có cache hit:
  - Log usage với `cached=True`
  - Trả về response ngay lập tức
  - Không gọi OpenAI API

### 3. Retrieval Phase (nếu cache miss)
- **Embedding**: Chuyển query thành vector embedding
- **Vector Search**: Tìm kiếm trong database bằng cosine similarity (lấy top_k candidates)

### 4. Context Building Phase
- Ưu tiên chunks từ `issue_metadata`
- Format với source labels và metadata
- Tạo prompt với:
  - System instructions
  - Context từ chunks
  - User query

### 5. Generation Phase
- Gọi OpenAI API với prompt đã tạo
- Nhận về answer và usage information

### 6. Logging Phase
- Log usage vào `openai_usage_log`:
  - Tokens (input, output, total)
  - Cost (USD)
  - Response time
- Log chi tiết vào `openai_usage_log_detail`:
  - Full prompt
  - Full response

### 7. Caching Phase
- Chỉ cache successful responses (không cache errors)
- TTL: 24 giờ cho successful, 1 giờ cho empty results

### 8. Response Phase
- Trả về:
  - `answer`: Câu trả lời từ AI
  - `sources`: Danh sách nguồn tham khảo
  - `retrieved_chunks`: Chunks đã retrieve
  - `cached`: Có phải từ cache không
  - `response_time_ms`: Thời gian xử lý

## Error Handling

- Nếu không tìm thấy chunks: Trả về message thông báo
- Nếu OpenAI API lỗi: Trả về error message, không cache
- Nếu logging lỗi: Warning nhưng không ảnh hưởng response

## Performance Optimizations

1. **Caching**: Giảm thiểu API calls với Redis cache
2. **Async Logging**: Log không block response

## Database Tables Used

- `chunk`: Chứa text content
- `embedding`: Chứa vector embeddings
- `source`: Metadata của sources
- `openai_usage_log`: Log usage statistics
- `openai_usage_log_detail`: Log prompt và response chi tiết
- `search_log`: Log search history

