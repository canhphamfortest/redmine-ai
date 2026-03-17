module CustomFeatures
  # Các lớp lỗi tùy chỉnh cho Custom Features Plugin
  # Tất cả các lỗi đều kế thừa từ CustomFeaturesError để dễ dàng catch và xử lý
  module Errors
    # Lớp lỗi cơ bản cho tất cả các lỗi Custom Features
    # Tất cả các lỗi khác trong module này đều kế thừa từ class này
    class CustomFeaturesError < StandardError; end

    # Lỗi khi AI service trả về phản hồi không hợp lệ
    # Xảy ra khi response từ AI service không đúng format hoặc thiếu dữ liệu cần thiết
    #
    # @param message [String, nil] Thông báo lỗi tùy chỉnh, hoặc nil để dùng message mặc định
    class InvalidAIResponseError < CustomFeaturesError
      def initialize(message = nil)
        super(message || Constants::ERROR_AI_SERVICE_INVALID_RESPONSE)
      end
    end

    # Lỗi khi không thể kết nối tới AI service
    # Xảy ra khi không thể thiết lập kết nối HTTP hoặc timeout
    #
    # @param message [String, nil] Thông báo lỗi tùy chỉnh, hoặc nil để dùng message mặc định
    class AIServiceConnectionError < CustomFeaturesError
      def initialize(message = nil)
        super(message || Constants::ERROR_AI_SERVICE_CONNECTION)
      end
    end

    # Lỗi khi URL của AI service không hợp lệ
    # Xảy ra khi URL không đúng format hoặc không thể parse được
    #
    # @param message [String, nil] Thông báo lỗi tùy chỉnh, hoặc nil để dùng message mặc định
    class InvalidAIServiceURLError < CustomFeaturesError
      def initialize(message = nil)
        super(message || Constants::ERROR_AI_SERVICE_INVALID_URL)
      end
    end

    # Lỗi khi bị từ chối quyền truy cập
    # Xảy ra khi user không có quyền thực hiện action (xem, chỉnh sửa, etc.)
    #
    # @param message [String, nil] Thông báo lỗi tùy chỉnh, hoặc nil để dùng message mặc định
    class PermissionDeniedError < CustomFeaturesError
      def initialize(message = nil)
        super(message || Constants::ERROR_PERMISSION_DENIED)
      end
    end

    # Lỗi khi không tìm thấy issue
    # Xảy ra khi issue ID không tồn tại trong database
    #
    # @param message [String, nil] Thông báo lỗi tùy chỉnh, hoặc nil để dùng message mặc định
    class IssueNotFoundError < CustomFeaturesError
      def initialize(message = nil)
        super(message || Constants::ERROR_ISSUE_NOT_FOUND)
      end
    end

    # Lỗi khi tạo checklist thất bại
    # Xảy ra khi AI service không thể tạo checklist hoặc parse checklist thất bại
    #
    # @param message [String] Thông báo lỗi, mặc định: 'Không thể tạo checklist'
    class ChecklistGenerationError < CustomFeaturesError
      def initialize(message = 'Không thể tạo checklist')
        super(message)
      end
    end

    # Lỗi khi tìm kiếm issues liên quan thất bại
    # Xảy ra khi AI search service không thể tìm được issues liên quan
    #
    # @param message [String, nil] Thông báo lỗi tùy chỉnh, hoặc nil để dùng message mặc định
    class RelatedIssuesSearchError < CustomFeaturesError
      def initialize(message = nil)
        super(message || Constants::ERROR_AI_SEARCH)
      end
    end
  end
end

