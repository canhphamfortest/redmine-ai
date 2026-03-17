# Changelog

## Version 1.0.0 (2025-01-XX)

### Features
- ✅ **AI-Powered Checklist Generation**: Tự động tạo checklist cho issue sử dụng AI Agent
  - Phân tích nội dung issue (subject, description, notes, custom fields, tracker, status, priority)
  - Tạo checklist phù hợp với nội dung (5-10 tasks)
  - Fallback checklist nếu AI không tạo được
  - Format Markdown checklist tương thích Redmine
- ✅ **AI-Powered Related Issues Finder**: Tìm issues liên quan sử dụng RAG
  - Phân tích sâu nội dung issue với AI Agent
  - Hiển thị similarity score và percentage
  - Tự động loại trừ issues đã có quan hệ
  - Chỉ hiển thị issues trong cùng project
- ✅ **RAG Search (AI Agent Search)**: Tìm kiếm thông minh với AI
  - Trả lời câu hỏi dựa trên dữ liệu đã ingest
  - Hiển thị sources và retrieved chunks
  - Similarity scores cho kết quả
  - Project context awareness
- ✅ **Auto Link Related Issues**: Tự động liên kết issues được phát hiện bởi AI
- ✅ Custom Search Box trong header (quick search)
- ✅ Menu item "Custom Search" trong top menu
- ✅ CSS và JavaScript tùy chỉnh với đầy đủ documentation
- ✅ Hỗ trợ đa ngôn ngữ (tiếng Việt)

### Technical
- **Architecture**:
  - Service-oriented architecture với separation of concerns
  - Formatters để normalize data
  - Error handling với custom error classes
  - Configuration management với multiple sources
- **AI Integration**:
  - HTTP client với timeout và error handling
  - RAG search integration
  - Related issues API integration
  - Prompt engineering cho checklist generation
- **UI/UX**:
  - Redmine hooks để tích hợp vào UI
  - JavaScript modules với proper initialization
  - Loading indicators và error messages
  - Responsive design
- **Code Quality**:
  - Đầy đủ docstrings và comments (YARD format)
  - JSDoc comments cho JavaScript
  - Section comments cho CSS
  - Comprehensive error handling
- **Documentation**:
  - README với đầy đủ hướng dẫn
  - INSTALL guide
  - Inline code documentation

