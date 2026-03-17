module CustomFeatures
  # Cấu hình cho Custom Features Plugin
  module Config
    # URL mặc định của API backend
    DEFAULT_API_BASE_URL = 'http://backend:8000'

    # Timeout của API (tính bằng giây)
    DEFAULT_TIMEOUT = 360

    # Các đường dẫn API tìm kiếm
    SEARCH_PATHS = {
      rag: '/api/search/rag',
      generate: '/api/search/generate',
      related_issues: '/api/search/issues',
      list_projects: '/api/ingest/sources/projects'
    }.freeze

    # Khóa cài đặt plugin
    PLUGIN_SETTINGS_KEY = 'custom_features'
    SETTING_RAG_API_BASE_URL = 'rag_api_base_url'

    # Khóa biến môi trường
    ENV_RAG_SEARCH_API_BASE = 'RAG_SEARCH_API_BASE'
    ENV_RAG_BACKEND_URL = 'RAG_BACKEND_URL'

    # HTTP headers mặc định
    DEFAULT_HEADERS = {
      'Content-Type' => 'application/json',
      'Accept' => 'application/json'
    }.freeze

    # Lấy URL base của API từ nhiều nguồn khác nhau
    # Ưu tiên: base_url param > plugin settings > environment variables > default
    #
    # @param base_url [String, nil] URL base được truyền vào (optional)
    # @return [String] URL base của API
    #   Ưu tiên kiểm tra:
    #   1. base_url parameter (nếu có)
    #   2. Plugin setting: rag_api_base_url
    #   3. Environment variable: RAG_SEARCH_API_BASE
    #   4. Environment variable: RAG_BACKEND_URL
    #   5. DEFAULT_API_BASE_URL
    def self.api_base_url(base_url: nil)
      return base_url if base_url.present?

      plugin_settings = fetch_plugin_settings
      return plugin_settings[SETTING_RAG_API_BASE_URL] if plugin_settings[SETTING_RAG_API_BASE_URL].present?
      return ENV[ENV_RAG_SEARCH_API_BASE] if ENV[ENV_RAG_SEARCH_API_BASE].present?
      return ENV[ENV_RAG_BACKEND_URL] if ENV[ENV_RAG_BACKEND_URL].present?

      DEFAULT_API_BASE_URL
    end

    # Đảm bảo URL có dấu gạch chéo ở cuối
    # Nếu URL rỗng, trả về default URL với dấu gạch chéo
    #
    # @param url [String, nil] URL cần normalize
    # @return [String] URL đã được normalize (có dấu gạch chéo ở cuối)
    def self.normalize_url(url)
      return "#{DEFAULT_API_BASE_URL}/" if url.blank?

      url.end_with?('/') ? url : "#{url}/"
    end

    private

    # Lấy plugin settings từ Redmine Setting
    # Xử lý lỗi và trả về empty hash nếu có lỗi
    #
    # @return [Hash] Hash chứa plugin settings hoặc {} nếu có lỗi
    def self.fetch_plugin_settings
      Setting.plugin_custom_features
    rescue StandardError
      {}
    end
  end
end

