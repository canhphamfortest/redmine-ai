module CustomFeatures
  module Services
    # Service để xây dựng nội dung issue cho phân tích AI
    class IssueContentBuilder
      include Constants

      # Khởi tạo IssueContentBuilder
      # @param issue [Issue] Issue cần xây dựng nội dung
      def initialize(issue)
        @issue = issue
      end

      # Xây dựng chuỗi nội dung từ dữ liệu issue
      # Sử dụng để tạo text content cho AI analysis hoặc search
      # Format: Subject, Description, Notes, Custom Fields (mỗi phần cách nhau 2 dòng trống)
      #
      # @return [String] Chuỗi nội dung đã được format, các phần cách nhau bằng "\n\n"
      def build
        content_parts = []

        # Thêm các phần nội dung theo thứ tự ưu tiên
        add_subject(content_parts)
        add_description(content_parts)
        add_notes(content_parts)
        add_custom_fields(content_parts)

        # Join các phần với 2 dòng trống để dễ đọc
        content_parts.join("\n\n")
      end

      # Lấy hash dữ liệu issue đầy đủ
      # @return [Hash] Hash chứa tất cả thông tin của issue
      def full_data
        {
          id: @issue.id,
          subject: @issue.subject,
          description: @issue.description,
          project: project_data,
          tracker: @issue.tracker&.name,
          status: @issue.status&.name,
          priority: @issue.priority&.name,
          assigned_to: @issue.assigned_to&.name,
          author: @issue.author&.name,
          created_on: @issue.created_on,
          updated_on: @issue.updated_on,
          due_date: @issue.due_date,
          notes: recent_notes,
          custom_fields: custom_fields_data
        }
      end

      private

      # Thêm subject vào content parts
      # @param content_parts [Array<String>] Mảng các phần nội dung
      def add_subject(content_parts)
        return unless @issue.subject.present?

        content_parts << "Subject: #{@issue.subject}"
      end

      # Thêm description vào content parts
      # @param content_parts [Array<String>] Mảng các phần nội dung
      def add_description(content_parts)
        return unless @issue.description.present?

        content_parts << "Description: #{@issue.description}"
      end

      # Thêm notes vào content parts
      # @param content_parts [Array<String>] Mảng các phần nội dung
      def add_notes(content_parts)
        notes = recent_notes
        return unless notes.any?

        content_parts << "Notes: #{notes.join(' ')}"
      end

      # Thêm custom fields vào content parts
      # @param content_parts [Array<String>] Mảng các phần nội dung
      def add_custom_fields(content_parts)
        return unless @issue.respond_to?(:custom_field_values)

        custom_values = custom_fields_data
          .select { |cf| cf[:value].to_s.length > Constants::ISSUE_CUSTOM_FIELD_MIN_VALUE_LENGTH }
          .map { |cf| "#{cf[:name]}: #{cf[:value]}" }

        return unless custom_values.any?

        content_parts << "Custom Fields: #{custom_values.join('; ')}"
      end

      # Lấy các notes của issue
      # @return [Array<String>] Mảng các notes
      def recent_notes
        return [] unless @issue.journals.any?

        @issue.journals
          .where.not(notes: [nil, ''])
          .order(created_on: :desc)
          .limit(Constants::ISSUE_RECENT_NOTES_LIMIT)
          .pluck(:notes)
      end

      # Lấy dữ liệu custom fields của issue
      # @return [Array<Hash>] Mảng các custom fields với name và value
      def custom_fields_data
        return [] unless @issue.respond_to?(:custom_field_values)

        @issue.custom_field_values
          .select { |cfv| cfv.value.present? }
          .map { |cfv| { name: cfv.custom_field.name, value: cfv.value } }
      end

      # Lấy dữ liệu project của issue
      # @return [Hash, nil] Hash chứa name và identifier của project, hoặc nil nếu không có
      def project_data
        return nil unless @issue.project

        {
          name: @issue.project.name,
          identifier: @issue.project.identifier
        }
      end
    end
  end
end

