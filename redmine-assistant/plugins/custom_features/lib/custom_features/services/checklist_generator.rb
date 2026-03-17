module CustomFeatures
  module Services
    # Service để tạo checklist cho issue sử dụng AI
    class ChecklistGenerator
      include Constants

      # Khởi tạo ChecklistGenerator
      # @param issue [Issue] Issue cần tạo checklist
      # @param user_id [Integer, String, nil] ID của user thực hiện request (optional)
      # @param search_client [SearchClient, nil] SearchClient instance (optional)
      def initialize(issue, user_id: nil, search_client: nil)
        @issue = issue
        @user_id = user_id
        @search_client = search_client || CustomFeatures::SearchClient.instance
        @content_builder = Services::IssueContentBuilder.new(issue)
      end

      # Tạo checklist sử dụng AI, raise error nếu thất bại
      # Đây là method chính được gọi từ controller
      # Nếu AI không tạo được checklist, sẽ raise error thay vì dùng fallback
      #
      # @return [Array<String>] Mảng các checklist items từ AI
      # @raise [CustomFeatures::ChecklistGenerationError] Nếu AI không tạo được checklist hoặc checklist rỗng
      def generate
        # Thử tạo checklist với AI
        checklist = generate_with_ai

        # Nếu AI không tạo được (rỗng), raise error
        if checklist.empty?
          Rails.logger.error "[ChecklistGenerator] AI generation failed, checklist is empty"
          raise CustomFeatures::ChecklistGenerationError, 'Không thể tạo checklist. AI không trả về kết quả hoặc không thể parse checklist từ response.'
        end

        checklist
      end

      # Tạo checklist chỉ sử dụng AI (không có fallback)
      # Flow: Build prompt -> Call AI directly -> Parse response -> Return checklist
      #
      # @return [Array<String>] Mảng các checklist items, rỗng nếu thất bại
      def generate_with_ai
        # Bước 1: Xây dựng prompt từ issue data
        prompt = build_prompt

        Rails.logger.info "[ChecklistGenerator] Generating checklist with AI for issue ##{@issue.id}"
        Rails.logger.debug "[ChecklistGenerator] Prompt length: #{prompt.length} chars"

        # Bước 2: Gọi AI service trực tiếp (không có vector search hay reranking)
        # Sử dụng generate_text vì checklist generation chỉ cần issue info đã có trong prompt
        response = @search_client.generate_text(prompt: prompt, user_id: @user_id)
        ai_answer = response['answer'] || ''

        Rails.logger.info "[ChecklistGenerator] AI response received, length: #{ai_answer.length} chars"
        Rails.logger.debug "[ChecklistGenerator] AI answer: #{ai_answer}"

        # Bước 3: Parse checklist từ AI response
        # Parser sẽ thử nhiều format khác nhau (markdown, bullet, numbered)
        checklist = Services::ChecklistParser.new(ai_answer).parse

        # Bước 4: Log kết quả
        if checklist.any?
          Rails.logger.info "[ChecklistGenerator] Successfully generated #{checklist.length} checklist items"
        else
          Rails.logger.warn "[ChecklistGenerator] Failed to parse checklist from AI response"
        end

        checklist
      rescue CustomFeatures::SearchClient::SearchError => e
        Rails.logger.error "[ChecklistGenerator] AI search error: #{e.message}"
        []
      rescue StandardError => e
        Rails.logger.error "[ChecklistGenerator] Error calling AI: #{e.message}\n#{e.backtrace.first(5).join("\n")}"
        []
      end

      # Format các checklist items thành nội dung notes
      # @param checklist [Array<String>] Mảng các checklist items
      # @return [String] Nội dung notes đã được format
      def format_notes_content(checklist)
        "#{Constants::CHECKLIST_PREFIX}\n\n#{checklist.join("\n")}"
      end

      private

      # Xây dựng prompt để gửi cho AI
      # Prompt được xây dựng theo cấu trúc:
      # 1. Introduction và instruction
      # 2. Issue information (subject, description, metadata)
      # 3. Requirements và format
      #
      # @return [String] Prompt string đã được format
      def build_prompt
        # Lấy đầy đủ dữ liệu issue từ content builder
        issue_data = @content_builder.full_data
        prompt_parts = []

        # Phần 1: Introduction và instruction
        prompt_parts << Constants::CHECKLIST_PROMPT_INTRO
        prompt_parts << ""
        prompt_parts << Constants::CHECKLIST_PROMPT_INSTRUCTION
        prompt_parts << ""
        
        # Phần 2: Issue basic info
        prompt_parts << "Issue ##{issue_data[:id]}: #{issue_data[:subject]}"

        # Phần 3: Thêm các thông tin chi tiết của issue (nếu có)
        add_description_to_prompt(prompt_parts, issue_data)
        add_project_to_prompt(prompt_parts, issue_data)
        add_tracker_to_prompt(prompt_parts, issue_data)
        add_status_to_prompt(prompt_parts, issue_data)
        add_priority_to_prompt(prompt_parts, issue_data)
        add_notes_to_prompt(prompt_parts, issue_data)
        add_custom_fields_to_prompt(prompt_parts, issue_data)

        # Phần 4: Requirements và format instructions
        prompt_parts << ""
        prompt_parts.concat(Constants::CHECKLIST_PROMPT_REQUIREMENTS)
        prompt_parts << ""
        prompt_parts << Constants::CHECKLIST_PROMPT_END

        # Join tất cả các phần thành một prompt hoàn chỉnh
        prompt_parts.join("\n")
      end

      # Thêm description vào prompt
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_description_to_prompt(prompt_parts, issue_data)
        return unless issue_data[:description].present?

        desc = issue_data[:description]
        desc = truncate(desc, Constants::ISSUE_DESCRIPTION_MAX_LENGTH)
        prompt_parts << "Mô tả: #{desc}"
      end

      # Thêm project vào prompt
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_project_to_prompt(prompt_parts, issue_data)
        return unless issue_data[:project]

        prompt_parts << "Project: #{issue_data[:project][:name]}"
      end

      # Thêm tracker vào prompt
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_tracker_to_prompt(prompt_parts, issue_data)
        return unless issue_data[:tracker]

        prompt_parts << "Tracker: #{issue_data[:tracker]}"
      end

      # Thêm status vào prompt
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_status_to_prompt(prompt_parts, issue_data)
        return unless issue_data[:status]

        prompt_parts << "Status: #{issue_data[:status]}"
      end

      # Thêm priority vào prompt
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_priority_to_prompt(prompt_parts, issue_data)
        return unless issue_data[:priority]

        prompt_parts << "Priority: #{issue_data[:priority]}"
      end

      # Thêm notes vào prompt
      # Lấy tất cả note của user và 3 note AI mới nhất
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_notes_to_prompt(prompt_parts, issue_data)
        notes = issue_data[:notes] || []
        return unless notes.any?

        # Tách notes thành user notes và AI notes
        user_notes, ai_notes = separate_notes(notes)

        # Lấy tất cả user notes và 3 AI notes mới nhất
        selected_notes = user_notes + ai_notes.first(3)

        return unless selected_notes.any?

        prompt_parts << "Notes:"
        selected_notes.each_with_index do |note, idx|
          note_text = truncate(note.to_s, Constants::ISSUE_NOTE_MAX_LENGTH)
          prompt_parts << "  #{idx + 1}. #{note_text}"
        end
      end

      # Tách notes thành user notes và AI notes
      # Note AI là note có prefix "AI Gen Checklist" ở đầu
      # @param notes [Array<String>] Mảng các notes
      # @return [Array<Array<String>>] Mảng gồm [user_notes, ai_notes]
      def separate_notes(notes)
        user_notes = []
        ai_notes = []

        notes.each do |note|
          note_str = note.to_s
          if note_str.start_with?(Constants::CHECKLIST_PREFIX)
            ai_notes << note
          else
            user_notes << note
          end
        end

        [user_notes, ai_notes]
      end

      # Thêm custom fields vào prompt
      # @param prompt_parts [Array<String>] Mảng các phần của prompt
      # @param issue_data [Hash] Dữ liệu issue
      def add_custom_fields_to_prompt(prompt_parts, issue_data)
        custom_fields = issue_data[:custom_fields] || []
        return unless custom_fields.any?

        prompt_parts << "Custom Fields:"
        custom_fields.first(Constants::ISSUE_CUSTOM_FIELDS_DISPLAY_LIMIT).each do |cf|
          cf_value = truncate(cf[:value].to_s, Constants::ISSUE_CUSTOM_FIELD_MAX_LENGTH)
          prompt_parts << "  - #{cf[:name]}: #{cf_value}"
        end
      end

      # Cắt ngắn text nếu vượt quá max_length
      # @param text [String] Text cần cắt
      # @param max_length [Integer] Độ dài tối đa
      # @return [String] Text đã được cắt (nếu cần)
      def truncate(text, max_length)
        return text if text.length <= max_length

        "#{text[0..max_length]}..."
      end
    end
  end
end

