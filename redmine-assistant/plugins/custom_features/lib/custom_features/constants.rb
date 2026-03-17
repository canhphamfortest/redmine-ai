module CustomFeatures
  # Các hằng số cho Custom Features Plugin
  # Tập hợp tất cả các constants được sử dụng trong plugin
  module Constants
    # ===== Checklist Configuration =====
    # Các hằng số liên quan đến việc tạo và xử lý checklist
    
    # Prefix để thêm vào đầu checklist khi tạo note
    CHECKLIST_PREFIX = "AI Gen Checklist"
    CHECKLIST_MIN_ITEMS = 5
    CHECKLIST_MAX_ITEMS = 10
    CHECKLIST_TASK_MIN_LENGTH = 3
    CHECKLIST_TASK_MAX_LENGTH = 200

    # ===== Issue Content Limits =====
    # Các giới hạn về độ dài nội dung issue để tối ưu prompt cho AI
    
    # Độ dài tối đa của description khi gửi cho AI
    ISSUE_DESCRIPTION_MAX_LENGTH = 2000
    ISSUE_NOTE_MAX_LENGTH = 1000
    ISSUE_CUSTOM_FIELD_MAX_LENGTH = 200
    ISSUE_RECENT_NOTES_LIMIT = 5
    ISSUE_RECENT_NOTES_DISPLAY_LIMIT = 3
    ISSUE_CUSTOM_FIELDS_DISPLAY_LIMIT = 5
    ISSUE_CUSTOM_FIELD_MIN_VALUE_LENGTH = 10

    # ===== Related Issues Configuration =====
    # Các hằng số cho tính năng tìm issues liên quan
    
    # Số lượng issues tối đa yêu cầu từ AI API
    RELATED_ISSUES_TOP_K = 20
    RELATED_ISSUES_MAX_RESULTS = 5
    # Ngưỡng để phân biệt similarity score (0-1) và percentage (0-100)
    # Nếu score > threshold thì coi là percentage, ngược lại là score 0-1
    SIMILARITY_SCORE_THRESHOLD = 1.0

    # ===== Error Messages =====
    # Các thông báo lỗi hiển thị cho người dùng
    
    ERROR_PERMISSION_DENIED = 'Bạn không có quyền chỉnh sửa issue này'
    ERROR_PERMISSION_VIEW_DENIED = 'Bạn không có quyền xem issue này'
    ERROR_ISSUE_NOT_FOUND = 'Không tìm thấy issue'
    ERROR_SAVE_FAILED = 'Lỗi khi lưu'
    ERROR_GENERIC = 'Đã xảy ra lỗi'
    ERROR_AI_SEARCH = 'Lỗi khi tìm kiếm với AI'
    ERROR_AI_SERVICE_INVALID_RESPONSE = 'Phản hồi không hợp lệ từ AI service'
    ERROR_AI_SERVICE_CONNECTION = 'Không thể kết nối tới AI service'
    ERROR_AI_SERVICE_INVALID_URL = 'URL AI service không hợp lệ'

    # ===== Success Messages =====
    # Các thông báo thành công hiển thị cho người dùng
    
    SUCCESS_DRAFT_NOTE_CREATED = 'Draft note với checklist đã được tạo thành công!'

    # ===== Fallback Data =====
    # Dữ liệu mặc định khi AI không thể tạo được
    
    # Checklist mặc định được sử dụng khi AI không tạo được checklist
    # Hoặc khi parse checklist từ AI response thất bại
    FALLBACK_CHECKLIST_ITEMS = [
      '- [ ] Review code changes',
      '- [ ] Run tests and verify all tests pass',
      '- [ ] Update documentation if needed',
      '- [ ] Check for security vulnerabilities',
      '- [ ] Verify performance metrics',
      '- [ ] Get approval from team lead',
      '- [ ] Deploy to staging environment'
    ].freeze

    # ===== AI Prompt Templates =====
    # Các template prompt để gửi cho AI service
    
    # Phần giới thiệu cho AI prompt tạo checklist
    CHECKLIST_PROMPT_INTRO = "Bạn là một AI assistant giúp tạo checklist test cases cho QC (Quality Control) để test issue trong hệ thống quản lý dự án."
    CHECKLIST_PROMPT_INSTRUCTION = "Hãy phân tích issue sau và tạo một checklist các test cases mà QC cần test trong issue này:"
    CHECKLIST_PROMPT_REQUIREMENTS = [
      "- Tạo một checklist gồm 5-10 test cases phù hợp với nội dung issue",
      "- Mỗi test case phải cụ thể, rõ ràng về những gì cần test",
      "- Checklist phải liên quan trực tiếp đến nội dung issue (subject, description, tracker, etc.)",
      "- Tập trung vào các test cases mà QC cần thực hiện để đảm bảo chất lượng",
      "- Trả về checklist dưới dạng markdown format: mỗi dòng là '- [ ] <test case>'",
      "- Chỉ trả về checklist, không giải thích thêm",
      "- Ví dụ format:",
      "  - [ ] Test chức năng đăng nhập với các tài khoản hợp lệ",
      "  - [ ] Test validation các trường bắt buộc",
      "  - [ ] Test hiển thị dữ liệu trên các trình duyệt khác nhau"
    ].freeze
    # Kết thúc prompt, báo hiệu AI bắt đầu trả về checklist
    CHECKLIST_PROMPT_END = "CHECKLIST:"

    # ===== Regex Patterns =====
    # Các pattern regex để parse checklist từ AI response
    
    # Các pattern để nhận diện markdown checklist format (ví dụ: "- [ ] task")
    CHECKLIST_MARKDOWN_PATTERNS = [
      /^[-*•]\s*\[[\sx]\]\s*.+/i,
      /^\d+\.\s*\[[\sx]\]\s*.+/i,
      /^-\s*\[[\sx]\]\s*.+/i
    ].freeze
    
    # Pattern để nhận diện bullet point (ví dụ: "- task", "* task")
    CHECKLIST_BULLET_PATTERN = /^[-*•]\s+.+/i
    
    # Pattern để nhận diện checkbox trong text
    CHECKLIST_CHECKBOX_PATTERN = /\[[\sx]\]/i
    
    # Pattern để trích xuất task text từ markdown checklist (ví dụ: "- [ ] task" -> "task")
    CHECKLIST_EXTRACT_PATTERN = /\[[\sx]\]\s*(.+)/i
    
    # Pattern để trích xuất task text từ bullet point (ví dụ: "- task" -> "task")
    CHECKLIST_BULLET_EXTRACT_PATTERN = /^[-*•]\s+(.+)/i
    
    # Pattern để nhận diện numbered list hoặc bullet (ví dụ: "1. task", "- task")
    CHECKLIST_NUMBERED_PATTERN = /^(?:\d+\.|[-*•])\s+(.+)/i
    
    # Pattern để loại bỏ keywords không cần thiết ở đầu task text
    CHECKLIST_KEYWORD_PATTERN = /^(checklist|task|item|công việc):?\s*/i

    ERROR_CHECKLIST_GENERATION_FAILED = 'Không thể tạo checklist. AI không trả về kết quả hoặc không thể parse checklist từ response.'
  end
end

