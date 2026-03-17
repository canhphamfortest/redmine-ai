# Create Draft Note Sequence Diagram

Tài liệu mô tả quy trình tạo draft note với AI-generated checklist cho Redmine issue.

## Sơ đồ tuần tự (Mermaid)

```mermaid
sequenceDiagram
    actor User
    participant Redmine as Redmine<br/>Controller
    participant SearchClient as SearchClient<br/>(Ruby)
    participant API as Backend API<br/>/api/search/generate
    participant Cache as Cache<br/>(Redis)
    participant RAGChain
    participant OpenAI as OpenAI API
    participant Tracker as UsageTracker
    participant Journal as Journal<br/>(Redmine)
    participant DB as Database<br/>(PostgreSQL)

    Note over User,Journal: Request Phase
    User->>Redmine: POST /issues/{id}/create_draft_note
    Redmine->>Redmine: find_issue(issue_id)
    
    alt Issue Not Found
        Redmine-->>User: 404 Not Found
    else Issue Found
        Redmine->>Redmine: Check permissions<br/>(visible? && editable?)
        
        alt No Permission
            Redmine-->>User: 403 Forbidden
        else Has Permission
            Note over Redmine: Build Issue Data
            Redmine->>Redmine: get_issue_full_data(issue)<br/>(id, subject, description,<br/>project, tracker, status,<br/>priority, notes, custom_fields)
            
            Note over Redmine: Build Checklist Prompt
            Redmine->>Redmine: build_checklist_prompt(issue)<br/>(system instructions +<br/>issue details)
            
            Note over Redmine,SearchClient: AI Generation Phase
            Redmine->>SearchClient: generate_text(<br/>prompt=prompt)
            
            SearchClient->>API: POST /api/search/generate<br/>{prompt}
            
            Note over API,Cache: Cache Check
            API->>+Cache: get_rag_response(prompt)
            Cache-->>-API: cached_response or null
            
            alt Cache Hit
                API->>+Tracker: log_usage(cached=True)
                Tracker->>DB: Save usage log
                Tracker-->>-API: Success
                API-->>SearchClient: Return cached response
            else Cache Miss
                Note over API,RAGChain: AI Generation (No Retrieval)
                API->>RAGChain: generate_answer(<br/>query=prompt,<br/>use_cache=True,<br/>skip_retrieval=True)
                
                Note over RAGChain: Skip vector search,<br/>reranking, and context building
                RAGChain->>RAGChain: Use prompt directly<br/>(no retrieval needed)
                
                RAGChain->>+OpenAI: chat.completions.create(prompt)
                Note over OpenAI: Generate checklist<br/>based on issue info in prompt
                OpenAI-->>-RAGChain: answer + usage_info
                
                RAGChain->>+Tracker: log_usage(tokens, cost, time)
                Tracker->>DB: Save to openai_usage_log
                Tracker-->>-RAGChain: usage_log
                
                RAGChain->>+Tracker: log_usage_detail(prompt, response)
                Tracker->>DB: Save to openai_usage_log_detail
                Tracker-->>-RAGChain: Success
                
                RAGChain->>+Cache: set_rag_response(response, TTL=24h)
                Cache-->>-RAGChain: Success
                
                RAGChain-->>API: {answer, sources=[], chunks=[]}
                API-->>SearchClient: {answer: "checklist items"}
            end
            
            Note over SearchClient,Redmine: Parse Checklist
            SearchClient-->>Redmine: {answer: "AI response"}
            Redmine->>Redmine: ChecklistParser.parse(ai_answer)<br/>(extract markdown checklist items)
            
            alt Checklist Empty or Parse Failed
                Note over Redmine: Raise Error
                Redmine->>Redmine: Raise ChecklistGenerationError<br/>(không tạo note)
                Redmine-->>User: JSON response<br/>{<br/>  success: false,<br/>  message: 'Không thể tạo checklist...'<br/>}
            end
            
            Note over Redmine: Format Notes Content
            Redmine->>Redmine: Format notes_content<br/>("**Checklist:**\n\n" + checklist.join("\n"))
            
            Note over Redmine,Journal: Create Journal Entry
            Redmine->>Journal: init_journal(User.current, notes_content)
            Journal->>Journal: Create journal entry
            
            Redmine->>+DB: Save issue<br/>(with journal)
            DB-->>-Redmine: Success
            
            alt Save Success
                Note over Redmine: Send Notification
                Redmine->>Redmine: Send notification<br/>(if enabled)
                
                Redmine-->>User: JSON response<br/>{<br/>  success: true,<br/>  message: 'Draft note created',<br/>  journal_id: id,<br/>  redirect_url: issue_path<br/>}
            else Save Failed
                Redmine-->>User: JSON response<br/>{<br/>  success: false,<br/>  message: 'Error saving'<br/>}
            end
        end
    end
```

## Mô tả chi tiết các bước

### 1. Request Phase
- User gửi POST request đến Redmine controller
- Controller tìm issue và kiểm tra quyền (visible && editable)

### 2. Build Issue Data Phase
- Lấy đầy đủ thông tin issue:
  - Basic: id, subject, description
  - Metadata: project, tracker, status, priority
  - Content: notes (5 gần nhất), custom fields

### 3. Build Checklist Prompt Phase
- Tạo prompt với:
  - System instructions: "Bạn là AI assistant tạo checklist..."
  - Issue details: subject, description, project, tracker, status, priority, notes
  - Yêu cầu: Tạo checklist phù hợp với nội dung issue

### 4. AI Generation Phase
- Gọi generate_text với prompt đã tạo
- Bỏ qua vector search và reranking (skip_retrieval=True)
- Gọi AI trực tiếp với prompt đã có đầy đủ issue info
- AI sẽ phân tích issue và tạo checklist items

### 5. Parse Checklist Phase
- Parse AI response để extract checklist items
- Format: Markdown checklist (`- [ ] item`)
- Nếu parse fail hoặc checklist rỗng → raise error và không tạo note

### 6. Format Notes Content Phase
- Format notes content với header "**Checklist:**"
- Join checklist items với newlines

### 7. Create Journal Entry Phase
- Tạo journal entry mới với notes content
- Link với current user
- Save issue (có journal)

### 8. Notification Phase
- Gửi notification nếu enabled
- Trả về response với journal_id và redirect_url

## Error Handling

- **Issue not found**: 404 Not Found
- **No permission**: 403 Forbidden
- **AI generation failed**: Raise `ChecklistGenerationError`, trả về error message, không tạo note
- **Parse failed**: Raise `ChecklistGenerationError`, trả về error message, không tạo note
- **Checklist empty**: Raise `ChecklistGenerationError`, trả về error message, không tạo note
- **AI service error**: Raise `SearchClient::SearchError`, trả về error message, không tạo note
- **Save failed**: Trả về error message

**Lưu ý**: Nếu AI không tạo được checklist hoặc parse thất bại, hệ thống sẽ **không tạo note** và trả về error message cho người dùng. Không có fallback checklist.

## Performance Optimizations

1. **No Retrieval**: Bỏ qua vector search và reranking → nhanh hơn
2. **Direct AI Call**: Gọi AI trực tiếp với prompt đã có → đơn giản hơn
3. **Caching**: Responses được cache 24h (theo prompt)
4. **Error Handling**: Báo lỗi rõ ràng nếu AI không tạo được checklist
5. **Async Notification**: Notification không block response

## Database Tables Used

- `openai_usage_log`: Log usage statistics
- `openai_usage_log_detail`: Log prompt và response chi tiết
- Redmine `issues`, `journals`: Issue và journal entries

## Lưu ý

- Endpoint `/api/search/generate` không sử dụng vector search hay reranking
- Prompt đã chứa đầy đủ thông tin issue, không cần retrieval từ database
- Response format tương tự RAG nhưng `retrieved_chunks` và `sources` luôn là empty arrays

