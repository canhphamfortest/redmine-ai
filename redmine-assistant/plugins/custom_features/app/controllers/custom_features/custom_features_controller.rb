module CustomFeatures
  # Controller xử lý các tính năng tùy chỉnh của plugin
  # Bao gồm: tạo draft note (checklist) và tìm issues liên quan
  class CustomFeaturesController < ApplicationController
    before_action :require_login
    before_action :find_issue, only: [:create_draft_note, :find_related_issues, :get_issue_info]

    # Tạo draft note (checklist) cho issue sử dụng AI
    # Sử dụng AI service để tạo checklist dựa trên nội dung issue
    # Checklist được tạo dưới dạng journal entry (note) trong issue
    #
    # @return [JSON] Response chứa:
    #   - success: true/false
    #   - message: Thông báo kết quả
    #   - journal_id: ID của journal entry đã tạo (nếu thành công)
    #   - redirect_url: URL để redirect đến issue (nếu thành công)
    #
    # @raise [JSON] Error response nếu:
    #   - Không có quyền xem/chỉnh sửa issue
    #   - Issue không tồn tại
    #   - Lỗi khi lưu issue
    #   - Lỗi khi gọi AI service
    def create_draft_note
      unless @issue.visible? && @issue.editable?
        render_error(Constants::ERROR_PERMISSION_DENIED, :forbidden)
        return
      end

      begin
        # Tạo checklist sử dụng AI service
        generator = Services::ChecklistGenerator.new(@issue, user_id: User.current.id)
        checklist = generator.generate
        notes_content = generator.format_notes_content(checklist)

        # Tạo journal entry (note)
        journal = @issue.init_journal(User.current, notes_content)

        if @issue.save
          # Gửi thông báo nếu cần
          send_notification(journal) if Setting.notified_events.include?('issue_updated')

          render json: {
            success: true,
            message: Constants::SUCCESS_DRAFT_NOTE_CREATED,
            journal_id: journal.id,
            redirect_url: issue_path(@issue)
          }
        else
          render_error("#{Constants::ERROR_SAVE_FAILED}: #{@issue.errors.full_messages.join(', ')}", :unprocessable_entity)
        end
      rescue CustomFeatures::Errors::ChecklistGenerationError => e
        Rails.logger.error "Checklist generation failed: #{e.message}"
        render_error(e.message, :unprocessable_entity)
      rescue CustomFeatures::SearchClient::SearchError => e
        Rails.logger.error "AI service error: #{e.message}"
        render_error("Lỗi khi gọi AI service: #{e.message}", :internal_server_error)
      rescue StandardError => e
        Rails.logger.error "Error creating draft note: #{e.message}\n#{e.backtrace.join("\n")}"
        render_error("#{Constants::ERROR_GENERIC}: #{e.message}", :internal_server_error)
      end
    end

    # Lấy thông tin issue dưới dạng JSON (proxy endpoint)
    # Endpoint này cho phép JavaScript lấy thông tin issue
    # sử dụng session authentication của user đã đăng nhập
    #
    # @return [JSON] Issue data trong format của Redmine API
    #
    # @raise [JSON] Error response nếu:
    #   - Không có quyền xem issue
    #   - Issue không tồn tại
    def get_issue_info
      unless @issue.visible?
        render_error(Constants::ERROR_PERMISSION_VIEW_DENIED, :forbidden)
        return
      end

      # Render issue data giống như Redmine API format
      render json: {
        issue: {
          id: @issue.id,
          project: {
            id: @issue.project.id,
            name: @issue.project.name
          },
          tracker: {
            id: @issue.tracker.id,
            name: @issue.tracker.name
          },
          status: {
            id: @issue.status.id,
            name: @issue.status.name
          },
          priority: {
            id: @issue.priority.id,
            name: @issue.priority.name
          },
          author: {
            id: @issue.author.id,
            name: @issue.author.name
          },
          subject: @issue.subject,
          description: @issue.description,
          created_on: @issue.created_on,
          updated_on: @issue.updated_on
        }
      }
    rescue StandardError => e
      Rails.logger.error "Error getting issue info: #{e.message}\n#{e.backtrace.join("\n")}"
      render_error("#{Constants::ERROR_GENERIC}: #{e.message}", :internal_server_error)
    end

    # Tìm các issues liên quan đến issue hiện tại sử dụng AI
    # Sử dụng AI service để phân tích nội dung và tìm các issues có liên quan
    # về mặt ngữ nghĩa hoặc nội dung
    #
    # @return [JSON] Response chứa:
    #   - success: true/false
    #   - related_issues: Mảng các issues liên quan đã được format
    #   - count: Số lượng issues liên quan
    #   - message: Thông báo lỗi (nếu có)
    #
    # @raise [JSON] Error response nếu:
    #   - Không có quyền xem issue
    #   - Issue không tồn tại
    #   - Lỗi khi gọi AI search service
    def find_related_issues
      unless @issue.visible?
        render_error(Constants::ERROR_PERMISSION_VIEW_DENIED, :forbidden)
        return
      end

      begin
        # Sử dụng service để tìm issues liên quan
        related_issues = Services::RelatedIssuesFinder.new(@issue).find

        render json: {
          success: true,
          related_issues: related_issues,
          count: related_issues.length
        }
      rescue SearchClient::SearchError => e
        Rails.logger.error "AI Search Error: #{e.message}"
        render json: {
          success: false,
          message: "#{Constants::ERROR_AI_SEARCH}: #{e.message}",
          related_issues: []
        }, status: :internal_server_error
      rescue StandardError => e
        Rails.logger.error "Error finding related issues: #{e.message}\n#{e.backtrace.join("\n")}"
        render json: {
          success: false,
          message: "#{Constants::ERROR_GENERIC}: #{e.message}",
          related_issues: []
        }, status: :internal_server_error
      end
    end

    private

    # Tìm issue từ params và set vào instance variable
    # Sử dụng trong before_action cho các action cần issue
    #
    # @raise [JSON] Error response nếu issue không tồn tại
    def find_issue
      @issue = Issue.find(params[:issue_id])
    rescue ActiveRecord::RecordNotFound
      render_error(Constants::ERROR_ISSUE_NOT_FOUND, :not_found)
    end

    # Render JSON error response với message và status code
    #
    # @param message [String] Thông báo lỗi
    # @param status [Symbol] HTTP status code (ví dụ: :forbidden, :not_found)
    def render_error(message, status)
      render json: { success: false, message: message }, status: status
    end

    # Gửi thông báo email khi issue được cập nhật
    # Sử dụng Redmine Mailer để gửi notification
    # Không làm fail request nếu gửi thông báo thất bại
    #
    # @param journal [Journal] Journal entry đã được tạo
    def send_notification(journal)
      Mailer.deliver_issue_edit(journal)
    rescue StandardError => e
      Rails.logger.error "Error sending notification: #{e.message}"
      # Don't fail the request if notification fails
    end
  end
end
