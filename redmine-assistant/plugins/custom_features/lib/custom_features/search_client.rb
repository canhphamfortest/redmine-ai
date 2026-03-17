require 'net/http'
require 'json'
require 'uri'

module CustomFeatures
  # Client để giao tiếp với AI search service
  # Sử dụng HTTP requests để gọi các API endpoints của AI backend
  # Hỗ trợ RAG search và tìm issues liên quan
  class SearchClient
    # Lỗi khi gọi AI search service thất bại
    # Được raise khi có lỗi kết nối, timeout, hoặc response không hợp lệ
    class SearchError < StandardError; end

    # Lấy instance singleton
    # @return [SearchClient] Instance của SearchClient
    def self.instance
      @instance ||= new
    end

    # Reset singleton instance (dùng khi settings thay đổi)
    # @return [void]
    def self.reset_instance!
      @instance = nil
    end

    # Khởi tạo SearchClient
    # Không cache base_url, sẽ đọc động từ Config mỗi lần request
    #
    # @param base_url [String, nil] URL base của API (optional)
    #   Nếu nil, sẽ sử dụng URL từ Config (plugin settings hoặc env vars)
    def initialize(base_url: nil)
      @base_url_override = base_url
      
      Rails.logger.info "[SearchClient] Initialized (URL will be read dynamically from Config)"
    end

    # Thực hiện RAG search (Retrieval-Augmented Generation)
    # Gửi query đến AI service và nhận về answer cùng với các chunks và sources
    #
    # @param query [String] Câu truy vấn tìm kiếm
    # @param list_project_ids [Array<Integer>, nil] Danh sách project IDs để filter kết quả (optional)
    # @param user_id [Integer, String, nil] ID của user thực hiện search (optional)
    # @return [Hash] Kết quả tìm kiếm từ AI service, chứa:
    #   - answer: Câu trả lời từ AI
    #   - retrieved_chunks: Mảng các chunks tìm được
    #   - sources: Mảng các nguồn tham khảo
    # @raise [SearchError] Nếu có lỗi khi gọi API
    def rag_search(query:, list_project_ids: nil, user_id: nil)
      payload = {
        query: query
      }
      
      # Thêm list_project_ids nếu có
      if list_project_ids.present?
        payload[:list_project_ids] = list_project_ids.join(',')
        Rails.logger.info "[SearchClient] RAG search with project filter: #{list_project_ids.inspect}"
      end
      
      # Thêm user_id nếu có
      if user_id.present?
        payload[:user_id] = user_id.to_s
        Rails.logger.info "[SearchClient] RAG search with user_id: #{user_id}"
      end
      
      Rails.logger.info "[SearchClient] RAG search called with query length: #{query.length}"
      Rails.logger.debug "[SearchClient] RAG search payload: #{payload.inspect}"
      
      result = request_json(:post, Config::SEARCH_PATHS[:rag], payload)
      
      Rails.logger.info "[SearchClient] RAG search response received with keys: #{result.keys.inspect}"
      Rails.logger.debug "[SearchClient] RAG search full response: #{result.inspect}"
      
      result
    end

    # Generate text bằng AI trực tiếp (không có vector search và reranking)
    # Gửi prompt đến AI service và nhận về answer, bỏ qua retrieval
    #
    # @param prompt [String] Prompt đầy đủ để gửi đến AI
    # @param user_id [Integer, String, nil] ID của user thực hiện request (optional)
    # @return [Hash] Kết quả từ AI service, chứa:
    #   - answer: Câu trả lời từ AI
    #   - sources: Mảng rỗng (không có retrieval)
    #   - retrieved_chunks: Mảng rỗng (không có retrieval)
    # @raise [SearchError] Nếu có lỗi khi gọi API
    def generate_text(prompt:, user_id: nil)
      payload = {
        prompt: prompt
      }
      
      # Thêm user_id nếu có
      if user_id.present?
        payload[:user_id] = user_id.to_s
        Rails.logger.info "[SearchClient] Generate text with user_id: #{user_id}"
      end
      
      Rails.logger.info "[SearchClient] Generate text called with prompt length: #{prompt.length}"
      Rails.logger.debug "[SearchClient] Generate text payload: #{payload.inspect}"
      
      result = request_json(:post, Config::SEARCH_PATHS[:generate], payload)
      
      Rails.logger.info "[SearchClient] Generate text response received with keys: #{result.keys.inspect}"
      Rails.logger.debug "[SearchClient] Generate text full response: #{result.inspect}"
      
      result
    end

    # Tìm các issues liên quan đến issue hiện tại
    # Sử dụng AI để phân tích nội dung và tìm các issues có liên quan về mặt ngữ nghĩa
    #
    # @param issue_id [Integer] ID của issue hiện tại
    # @param top_k [Integer] Số lượng kết quả tối đa từ AI (mặc định: 20)
    # @return [Hash] Kết quả tìm kiếm issues liên quan, chứa:
    #   - related_issues: Mảng các issues liên quan với similarity_score
    # @raise [SearchError] Nếu có lỗi khi gọi API
    def find_related_issues(issue_id:, top_k: 20)
      path = "#{Config::SEARCH_PATHS[:related_issues]}/#{issue_id}/related?top_k=#{top_k}"
      request_json(:get, path)
    end

    # Lấy danh sách projects có dữ liệu trong AI server
    # Gọi API /api/ingest/sources/projects để lấy danh sách project IDs
    #
    # @return [Array<Integer>] Mảng các project IDs có dữ liệu trong AI server
    # @raise [SearchError] Nếu có lỗi khi gọi API
    def list_projects
      path = Config::SEARCH_PATHS[:list_projects]
      result = request_json(:get, path)
      
      Rails.logger.info "[SearchClient] List projects response received"
      Rails.logger.debug "[SearchClient] List projects full response: #{result.inspect}"
      
      # Extract project_ids from response
      projects = result['projects'] || []
      project_ids = projects.map { |p| p['project_id'] }.compact
      
      Rails.logger.info "[SearchClient] Found #{project_ids.length} projects with data: #{project_ids.inspect}"
      
      project_ids
    end

    private

    # Lấy base URL động từ Config (không cache)
    # Đọc lại settings mỗi lần để đảm bảo dùng giá trị mới nhất
    # @return [String] Base URL đã được normalize
    def base_url
      url = @base_url_override || Config.api_base_url
      Config.normalize_url(url)
    end

    # Log chi tiết request trước khi gửi
    # @param method [Symbol] HTTP method (:get, :post)
    # @param uri [URI] URI object
    # @param path [String] API path
    def log_request_details(method, uri, path)
      Rails.logger.info "[SearchClient] Making #{method.to_s.upcase} request to: #{uri}"
      Rails.logger.debug "[SearchClient] Full URL: #{uri.to_s}"
      Rails.logger.debug "[SearchClient] Base URL: #{base_url}"
      Rails.logger.debug "[SearchClient] Path: #{path}"
    end

    # Tạo HTTP request object
    # @param method [Symbol] HTTP method (:get, :post)
    # @param uri [URI] URI object
    # @param payload [Hash, nil] Payload cho POST request (optional)
    # @return [Net::HTTPRequest] HTTP request object
    def build_http_request(method, uri, payload = nil)
      case method
      when :post
        req = Net::HTTP::Post.new(uri.request_uri, default_headers)
        req.body = payload.to_json if payload
        Rails.logger.debug "[SearchClient] Request body: #{req.body[0..500]}..." if req.body
        req
      when :get
        Net::HTTP::Get.new(uri.request_uri, default_headers)
      else
        raise ArgumentError, "Unsupported method: #{method}"
      end
    end

    # Cấu hình HTTP connection
    # @param uri [URI] URI object
    # @return [Net::HTTP] HTTP connection object
    def configure_http_connection(uri)
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = uri.scheme == 'https'
      http.open_timeout = Config::DEFAULT_TIMEOUT
      http.read_timeout = Config::DEFAULT_TIMEOUT
      http
    end

    # Thực thi HTTP request và log response
    # @param http [Net::HTTP] HTTP connection
    # @param request [Net::HTTPRequest] HTTP request object
    # @return [Net::HTTPResponse] HTTP response object
    def execute_request(http, request)
      Rails.logger.info "[SearchClient] Sending request to #{http.address}:#{http.port}#{request.path}"
      
      start_time = Time.now
      response = http.request(request)
      elapsed = ((Time.now - start_time) * 1000).round(2)
      
      Rails.logger.info "[SearchClient] Response received in #{elapsed}ms, status: #{response.code}"
      Rails.logger.debug "[SearchClient] Response headers: #{response.to_hash.inspect}"
      Rails.logger.debug "[SearchClient] Response body length: #{response.body.length} bytes"
      
      response
    end

    # Gửi HTTP request và nhận JSON response
    # @param method [Symbol] HTTP method (:get, :post)
    # @param path [String] API path
    # @param payload [Hash, nil] Payload cho POST request (optional)
    # @return [Hash] JSON response đã được parse
    # @raise [SearchError] Nếu có lỗi xảy ra
    def request_json(method, path, payload = nil)
      uri = build_uri(path)
      log_request_details(method, uri, path)
      
      http = configure_http_connection(uri)
      request = build_http_request(method, uri, payload)
      response = execute_request(http, request)
      
      handle_response(response)
    rescue JSON::ParserError => e
      Rails.logger.error "[SearchClient] JSON parse error: #{e.message}"
      raise SearchError, "Phản hồi không hợp lệ từ AI service: #{e.message}"
    rescue StandardError => e
      Rails.logger.error "[SearchClient] Request failed: #{e.class} - #{e.message}"
      Rails.logger.error "[SearchClient] Backtrace: #{e.backtrace.first(5).join("\n")}"
      raise SearchError, "Không thể kết nối tới AI service: #{e.message}"
    end

    # Xử lý HTTP response
    # @param response [Net::HTTPResponse] HTTP response object
    # @return [Hash] JSON response đã được parse
    # @raise [SearchError] Nếu response không thành công
    def handle_response(response)
      if response.is_a?(Net::HTTPSuccess)
        body = response.body.presence || '{}'
        JSON.parse(body)
      else
        raise SearchError, build_error_message(response)
      end
    end

    # Xây dựng thông báo lỗi từ response
    # @param response [Net::HTTPResponse] HTTP response object
    # @return [String] Thông báo lỗi
    def build_error_message(response)
      detail =
        begin
          parsed = JSON.parse(response.body.to_s)
          parsed['detail'] || parsed['error'] || parsed['message'] || response.body
        rescue JSON::ParserError
          response.body
        end

      "AI service trả về lỗi (#{response.code}): #{detail}"
    end

    # Xây dựng URI từ path
    # Đọc base_url động mỗi lần để đảm bảo dùng settings mới nhất
    # @param path [String] API path
    # @return [URI] URI object
    # @raise [SearchError] Nếu URL không hợp lệ
    def build_uri(path)
      URI.join(base_url, path.sub(%r{^/}, ''))
    rescue URI::InvalidURIError => e
      raise SearchError, "URL AI service không hợp lệ: #{e.message}"
    end

    # Lấy default HTTP headers
    # @return [Hash] Hash chứa default headers
    def default_headers
      Config::DEFAULT_HEADERS
    end
  end
end


