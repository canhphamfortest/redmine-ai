module CustomFeatures
  module Services
    # Service để tìm issues liên quan sử dụng AI
    class RelatedIssuesFinder
      include Constants

      # Khởi tạo RelatedIssuesFinder
      # @param current_issue [Issue] Issue hiện tại cần tìm issues liên quan
      # @param search_client [SearchClient, nil] SearchClient instance (optional, sẽ dùng singleton nếu nil)
      def initialize(current_issue, search_client: nil)
        @current_issue = current_issue
        @search_client = search_client || CustomFeatures::SearchClient.instance
      end

      # Tìm issues liên quan cho issue hiện tại
      # Flow: Get existing relations -> Call AI API -> Process & filter -> Return results
      #
      # @param exclude_ids [Array<Integer>] Mảng các issue IDs cần loại trừ (mặc định: [])
      #   Nếu không truyền, sẽ tự động lấy từ existing relations
      # @return [Array<Hash>] Mảng các issues liên quan đã được format, sắp xếp theo similarity
      def find(exclude_ids: [])
        Rails.logger.info "[RelatedIssuesFinder] Finding related issues for issue ##{@current_issue.id}"

        # Bước 1: Lấy các ID quan hệ hiện có để loại trừ
        # Tránh hiển thị lại các issues đã có quan hệ
        existing_relation_ids = exclude_ids.presence || get_existing_relation_ids

        # Bước 2: Gọi AI API để tìm issues liên quan
        # AI sẽ phân tích nội dung issue và tìm các issues tương tự
        api_response = call_ai_api

        # Bước 3: Xử lý và lọc kết quả
        # - Normalize API response
        # - Lọc bỏ excluded IDs và issue hiện tại
        # - Load và format issues từ database
        # - Validate permissions và project
        related_issues = process_api_response(api_response, existing_relation_ids)

        Rails.logger.info "[RelatedIssuesFinder] Found #{related_issues.length} related issues"
        related_issues
      rescue CustomFeatures::SearchClient::SearchError => e
        Rails.logger.error "[RelatedIssuesFinder] API call failed: #{e.message}"
        []
      rescue StandardError => e
        Rails.logger.error "[RelatedIssuesFinder] Error: #{e.message}\n#{e.backtrace.first(5).join("\n")}"
        []
      end

      private

      # Lấy danh sách IDs của các issues đã có quan hệ với issue hiện tại
      # @return [Array<Integer>] Mảng các issue IDs
      def get_existing_relation_ids
        @current_issue.relations.map { |r| r.other_issue(@current_issue).id }
      end

      # Gọi AI API để tìm issues liên quan
      # @return [Hash] Response từ AI API
      def call_ai_api
        Rails.logger.info "[RelatedIssuesFinder] Calling API endpoint for issue ##{@current_issue.id}"

        response = @search_client.find_related_issues(
          issue_id: @current_issue.id,
          top_k: Constants::RELATED_ISSUES_TOP_K
        )

        Rails.logger.info "[RelatedIssuesFinder] API response received"
        Rails.logger.debug "[RelatedIssuesFinder] Full API response: #{response.to_json}"

        response
      end

      # Xử lý response từ AI API và lọc kết quả
      # Pipeline: Extract data -> Normalize -> Filter -> Load & Format
      #
      # @param api_response [Hash] Response từ AI API, chứa key 'related_issues'
      # @param exclude_ids [Array<Integer>] Mảng các issue IDs cần loại trừ
      # @return [Array<Hash>] Mảng các issues đã được format và lọc
      def process_api_response(api_response, exclude_ids)
        # Bước 1: Extract related_issues từ API response
        related_issues_data = api_response['related_issues'] || []

        if related_issues_data.empty?
          Rails.logger.info "[RelatedIssuesFinder] No related issues found from API"
          return []
        end

        # Bước 2: Chuyển đổi API response sang định dạng nội bộ
        # Normalize similarity scores về khoảng 0-1
        issue_data_with_scores = normalize_api_response(related_issues_data)

        # Bước 3: Lọc bỏ các ID bị loại trừ và issue hiện tại
        # Tránh duplicate và self-reference
        issue_data_with_scores = filter_excluded_issues(issue_data_with_scores, exclude_ids)

        if issue_data_with_scores.empty?
          Rails.logger.info "[RelatedIssuesFinder] No issues remaining after filtering"
          return []
        end

        # Bước 4: Load issues từ database, validate permissions, và format
        # Chỉ lấy issues trong cùng project và có quyền truy cập
        format_issues(issue_data_with_scores)
      end

      # Chuẩn hóa API response sang định dạng nội bộ
      # @param related_issues_data [Array<Hash>] Dữ liệu issues từ API
      # @return [Array<Hash>] Mảng các issues đã được normalize với issue_id và similarity_score
      def normalize_api_response(related_issues_data)
        related_issues_data.map do |item|
          {
            issue_id: item['issue_id'],
            similarity_score: normalize_similarity_score(item)
          }
        end
      end

      # Chuẩn hóa similarity score về khoảng 0-1
      # @param item [Hash] Item từ API response
      # @return [Float] Similarity score đã được normalize (0-1)
      def normalize_similarity_score(item)
        score = item['similarity_score'] || item['similarity_percentage']
        return 0.5 if score.nil?

        # Nếu score là phần trăm (> 1), chuyển đổi về khoảng 0-1
        score > SIMILARITY_SCORE_THRESHOLD ? score / 100.0 : score.to_f
      end

      # Lọc bỏ các issues bị loại trừ và issue hiện tại
      # @param issue_data_with_scores [Array<Hash>] Mảng các issues với scores
      # @param exclude_ids [Array<Integer>] Mảng các issue IDs cần loại trừ
      # @return [Array<Hash>] Mảng các issues sau khi lọc
      def filter_excluded_issues(issue_data_with_scores, exclude_ids)
        issue_data_with_scores.reject do |item|
          exclude_ids.include?(item[:issue_id]) || item[:issue_id] == @current_issue.id
        end
      end

      # Format và load issues từ database
      # Process từng issue: Load -> Validate project -> Format -> Add to results
      #
      # @param issue_data_with_scores [Array<Hash>] Mảng các issues với scores từ API
      # @return [Array<Hash>] Mảng các issues đã được format, sắp xếp theo similarity score (giảm dần)
      def format_issues(issue_data_with_scores)
        related_issues = []
        
        # Loại bỏ duplicate issues (có thể có nếu API trả về trùng)
        unique_issues = issue_data_with_scores.uniq { |item| item[:issue_id] }

        Rails.logger.info "[RelatedIssuesFinder] Processing #{unique_issues.length} unique issues"

        unique_issues.each do |item|
          # Giới hạn số lượng kết quả tối đa
          break if related_issues.length >= Constants::RELATED_ISSUES_MAX_RESULTS

          # Load issue từ database và kiểm tra quyền truy cập
          issue = load_issue(item[:issue_id])
          next unless issue

          # Lọc theo project: chỉ lấy issues trong cùng project
          # Đảm bảo tính nhất quán và tránh cross-project relations không mong muốn
          next unless issue.project_id == @current_issue.project_id

          # Validate và format issue với similarity score
          formatted_issue = format_issue(issue, item[:similarity_score])
          related_issues << formatted_issue if formatted_issue
        end

        # Sắp xếp theo similarity score (giảm dần) để hiển thị issues liên quan nhất trước
        related_issues.sort_by { |issue| -(issue[:similarity_score] || 0) }
      end

      # Load issue từ database và kiểm tra quyền truy cập
      # @param issue_id [Integer] ID của issue cần load
      # @return [Issue, nil] Issue object hoặc nil nếu không tìm thấy hoặc không có quyền
      def load_issue(issue_id)
        issue = Issue.find_by(id: issue_id)

        unless issue
          Rails.logger.warn "[RelatedIssuesFinder] Issue ##{issue_id} not found in database"
          return nil
        end

        unless issue.visible?
          Rails.logger.warn "[RelatedIssuesFinder] Issue ##{issue_id} not visible to current user"
          return nil
        end

        issue
      rescue StandardError => e
        Rails.logger.error "[RelatedIssuesFinder] Error loading issue ##{issue_id}: #{e.message}"
        nil
      end

      # Format issue với similarity score và percentage
      # @param issue [Issue] Issue object cần format
      # @param similarity_score [Float] Similarity score (0-1)
      # @return [Hash, nil] Hash chứa thông tin issue đã format hoặc nil nếu không hợp lệ
      def format_issue(issue, similarity_score)
        # Validate các trường bắt buộc
        return nil unless issue.id.present? && issue.subject.present?

        formatted = Formatters::IssueFormatter.format(issue)
        formatted[:similarity_score] = similarity_score
        formatted[:similarity_percentage] = calculate_similarity_percentage(similarity_score)

        Rails.logger.info "[RelatedIssuesFinder] Added issue ##{issue.id} (similarity: #{similarity_score})"
        formatted
      end

      # Tính similarity percentage từ similarity score
      # @param similarity_score [Float, nil] Similarity score (0-1) hoặc percentage (> 1)
      # @return [Float] Similarity percentage (0-100)
      def calculate_similarity_percentage(similarity_score)
        return 0 if similarity_score.nil?

        # Chuyển đổi similarity score (0-1) sang phần trăm (0-100)
        # Nếu score đã là phần trăm (> 1), giữ nguyên
        if similarity_score > Constants::SIMILARITY_SCORE_THRESHOLD
          similarity_score.to_f
        else
          (similarity_score.to_f * 100).round(1)
        end
      end
    end
  end
end

