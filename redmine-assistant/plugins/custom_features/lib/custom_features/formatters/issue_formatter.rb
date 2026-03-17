module CustomFeatures
  module Formatters
    # Formatter cho dữ liệu issue thành JSON response
    # Chuyển đổi Issue object thành Hash để trả về JSON
    class IssueFormatter
      # Format issue cho JSON response (định dạng đơn giản cho related issues)
      # Chỉ bao gồm các thông tin cơ bản, không bao gồm description và notes chi tiết
      #
      # @param issue [Issue] Issue object cần format
      # @return [Hash] Hash chứa thông tin issue đã được format:
      #   - id: Issue ID
      #   - subject: Tiêu đề issue
      #   - status: Hash {id, name}
      #   - priority: Hash {id, name}
      #   - tracker: Hash {id, name}
      #   - assigned_to: Hash {id, name} hoặc nil
      #   - project: Hash {id, name, identifier}
      #   - created_on: Ngày tạo
      #   - updated_on: Ngày cập nhật
      #   - due_date: Ngày hết hạn
      #   - similarity_score: nil (sẽ được set bởi caller)
      #   - similarity_percentage: nil (sẽ được set bởi caller)
      def self.format(issue)
        {
          id: issue.id,
          subject: issue.subject,
          status: format_status(issue.status),
          priority: format_priority(issue.priority),
          tracker: format_tracker(issue.tracker),
          assigned_to: format_user(issue.assigned_to),
          project: format_project(issue.project),
          created_on: issue.created_on,
          updated_on: issue.updated_on,
          due_date: issue.due_date,
          similarity_score: nil, # Sẽ được set bởi caller
          similarity_percentage: nil # Sẽ được set bởi caller
        }
      end

      # Format issue với đầy đủ dữ liệu (cho AI prompts)
      # Bao gồm tất cả thông tin cần thiết để gửi cho AI service
      #
      # @param issue [Issue] Issue object cần format
      # @return [Hash] Hash chứa đầy đủ thông tin issue:
      #   - id: Issue ID
      #   - subject: Tiêu đề issue
      #   - description: Mô tả issue
      #   - project: Hash {name, identifier}
      #   - tracker: Tên tracker
      #   - status: Tên status
      #   - priority: Tên priority
      #   - assigned_to: Tên người được giao
      #   - author: Tên người tạo
      #   - created_on: Ngày tạo
      #   - updated_on: Ngày cập nhật
      #   - due_date: Ngày hết hạn
      #   - notes: Mảng các notes
      #   - custom_fields: Mảng các custom fields {name, value}
      def self.format_full(issue)
        {
          id: issue.id,
          subject: issue.subject,
          description: issue.description,
          project: format_project_full(issue.project),
          tracker: issue.tracker&.name,
          status: issue.status&.name,
          priority: issue.priority&.name,
          assigned_to: issue.assigned_to&.name,
          author: issue.author&.name,
          created_on: issue.created_on,
          updated_on: issue.updated_on,
          due_date: issue.due_date,
          notes: recent_notes(issue),
          custom_fields: format_custom_fields(issue)
        }
      end

      private

      # Format status object thành Hash
      #
      # @param status [IssueStatus, nil] Status object hoặc nil
      # @return [Hash, nil] Hash {id, name} hoặc nil
      def self.format_status(status)
        return nil unless status

        {
          id: status.id,
          name: status.name
        }
      end

      # Format priority object thành Hash
      #
      # @param priority [IssuePriority, nil] Priority object hoặc nil
      # @return [Hash, nil] Hash {id, name} hoặc nil
      def self.format_priority(priority)
        return nil unless priority

        {
          id: priority.id,
          name: priority.name
        }
      end

      # Format tracker object thành Hash
      #
      # @param tracker [Tracker, nil] Tracker object hoặc nil
      # @return [Hash, nil] Hash {id, name} hoặc nil
      def self.format_tracker(tracker)
        return nil unless tracker

        {
          id: tracker.id,
          name: tracker.name
        }
      end

      # Format user object thành Hash
      #
      # @param user [User, nil] User object hoặc nil
      # @return [Hash, nil] Hash {id, name} hoặc nil
      def self.format_user(user)
        return nil unless user

        {
          id: user.id,
          name: user.name
        }
      end

      # Format project object thành Hash (đầy đủ thông tin)
      #
      # @param project [Project, nil] Project object hoặc nil
      # @return [Hash, nil] Hash {id, name, identifier} hoặc nil
      def self.format_project(project)
        return nil unless project

        {
          id: project.id,
          name: project.name,
          identifier: project.identifier
        }
      end

      # Format project object thành Hash (chỉ name và identifier, không có id)
      # Sử dụng cho format_full khi không cần ID
      #
      # @param project [Project, nil] Project object hoặc nil
      # @return [Hash, nil] Hash {name, identifier} hoặc nil
      def self.format_project_full(project)
        return nil unless project

        {
          name: project.name,
          identifier: project.identifier
        }
      end

      # Lấy các notes của issue
      # Chỉ lấy các journal entries có notes (không rỗng)
      # Giới hạn 5 notes gần nhất, sắp xếp theo thời gian giảm dần
      #
      # @param issue [Issue] Issue object
      # @return [Array<String>] Mảng các notes (strings)
      def self.recent_notes(issue)
        return [] unless issue.journals.any?

        issue.journals
          .where.not(notes: [nil, ''])
          .order(created_on: :desc)
          .limit(5)
          .pluck(:notes)
      end

      # Format custom fields của issue thành mảng Hash
      # Chỉ lấy các custom fields có value (không rỗng)
      #
      # @param issue [Issue] Issue object
      # @return [Array<Hash>] Mảng các custom fields {name, value}
      def self.format_custom_fields(issue)
        return [] unless issue.respond_to?(:custom_field_values)

        issue.custom_field_values
          .select { |cfv| cfv.value.present? }
          .map { |cfv| { name: cfv.custom_field.name, value: cfv.value } }
      end
    end
  end
end

