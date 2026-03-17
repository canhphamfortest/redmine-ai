module CustomFeatures
  module Services
    # Service để parse checklist từ AI response
    class ChecklistParser
      include Constants

      # Khởi tạo ChecklistParser
      # @param ai_answer [String] Response từ AI
      def initialize(ai_answer)
        @ai_answer = ai_answer.to_s
      end

      # Parse các checklist items từ AI response
      # Thử nhiều format khác nhau theo thứ tự ưu tiên: markdown, bullet, numbered
      # Mỗi format sẽ được thử nếu format trước đó không tìm được items
      #
      # @return [Array<String>] Mảng các checklist items đã được format (tối đa CHECKLIST_MAX_ITEMS)
      def parse
        return [] if @ai_answer.blank?

        # Thử parse theo thứ tự ưu tiên:
        # 1. Markdown format (ví dụ: "- [ ] task") - ưu tiên cao nhất
        checklist = parse_markdown_format
        
        # 2. Bullet format (ví dụ: "- task") - nếu markdown không có
        checklist = parse_bullet_format if checklist.empty?
        
        # 3. Numbered format (ví dụ: "1. task") - nếu cả hai trên không có
        checklist = parse_numbered_format if checklist.empty?

        # Giới hạn số lượng items tối đa để tránh checklist quá dài
        checklist.first(Constants::CHECKLIST_MAX_ITEMS)
      end

      private

      # Parse checklist từ format markdown (ví dụ: "- [ ] task")
      # Đây là format ưu tiên nhất vì rõ ràng và dễ parse
      #
      # @return [Array<String>] Mảng các checklist items đã được format
      def parse_markdown_format
        checklist = []
        lines = @ai_answer.split("\n")

        lines.each do |line|
          line = line.strip
          next if line.blank?

          # Bước 1: Kiểm tra xem dòng có khớp với pattern markdown checklist không
          # Pattern có thể là: "- [ ]", "* [ ]", "• [ ]", hoặc numbered với checkbox
          next unless matches_markdown_pattern?(line)

          # Bước 2: Trích xuất task text từ dòng (loại bỏ checkbox và bullet)
          task_text = extract_task_text(line)
          next unless valid_task_text?(task_text)

          # Bước 3: Format lại thành markdown checklist chuẩn và thêm vào kết quả
          checklist << format_checklist_item(task_text)
        end

        checklist
      end

      # Parse checklist từ format bullet (ví dụ: "- task")
      # @return [Array<String>] Mảng các checklist items
      def parse_bullet_format
        checklist = []
        lines = @ai_answer.split("\n")

        lines.each do |line|
          line = line.strip
          next if line.blank?
          next if line.match?(Constants::CHECKLIST_CHECKBOX_PATTERN) # Bỏ qua nếu đã có checkbox

          # Kiểm tra xem dòng có phải là bullet point không có checkbox không
          next unless line.match?(Constants::CHECKLIST_BULLET_PATTERN)

          task_text = extract_bullet_text(line)
          next unless valid_task_text?(task_text)

          checklist << format_checklist_item(task_text)
        end

        checklist
      end

      # Parse checklist từ format numbered (ví dụ: "1. task")
      # @return [Array<String>] Mảng các checklist items
      def parse_numbered_format
        checklist = []
        lines = @ai_answer.split("\n")

        lines.each do |line|
          line = line.strip
          next if line.blank?

          # Kiểm tra xem dòng có khớp với pattern numbered hoặc bullet không
          match = line.match(Constants::CHECKLIST_NUMBERED_PATTERN)
          next unless match

          task_text = match[1].strip
          task_text = remove_keywords(task_text)
          next unless valid_task_text?(task_text)

          checklist << format_checklist_item(task_text)
        end

        checklist
      end

      # Kiểm tra xem dòng có khớp với pattern markdown checklist không
      # @param line [String] Dòng text cần kiểm tra
      # @return [Boolean] true nếu khớp pattern
      def matches_markdown_pattern?(line)
        Constants::CHECKLIST_MARKDOWN_PATTERNS.any? { |pattern| line.match?(pattern) }
      end

      # Trích xuất task text từ dòng markdown checklist
      # @param line [String] Dòng text
      # @return [String, nil] Task text hoặc nil nếu không tìm thấy
      def extract_task_text(line)
        match = line.match(Constants::CHECKLIST_EXTRACT_PATTERN)
        return nil unless match

        task_text = match[1].strip
        # Loại bỏ các ký tự bullet còn lại
        task_text.sub(/^[-*•]\s*/, '').strip
      end

      # Trích xuất task text từ dòng bullet
      # @param line [String] Dòng text
      # @return [String, nil] Task text hoặc nil nếu không tìm thấy
      def extract_bullet_text(line)
        match = line.match(Constants::CHECKLIST_BULLET_EXTRACT_PATTERN)
        return nil unless match

        match[1].strip
      end

      # Loại bỏ các keywords không cần thiết từ task text
      # @param task_text [String] Task text
      # @return [String] Task text đã được làm sạch
      def remove_keywords(task_text)
        task_text.sub(Constants::CHECKLIST_KEYWORD_PATTERN, '').strip
      end

      # Kiểm tra xem task text có hợp lệ không
      # @param task_text [String] Task text cần kiểm tra
      # @return [Boolean] true nếu hợp lệ
      def valid_task_text?(task_text)
        return false if task_text.blank?

        length = task_text.length
        length >= Constants::CHECKLIST_TASK_MIN_LENGTH && length < Constants::CHECKLIST_TASK_MAX_LENGTH
      end

      # Format task text thành checklist item markdown
      # @param task_text [String] Task text
      # @return [String] Checklist item đã được format
      def format_checklist_item(task_text)
        "- [ ] #{task_text}"
      end
    end
  end
end

