# Controller xử lý tìm kiếm tùy chỉnh sử dụng AI (RAG search)
# Cho phép người dùng tìm kiếm trong Redmine với khả năng AI để trả lời câu hỏi
class CustomSearchController < ApplicationController
  # Xóa project_id khỏi params nếu là 'all-projects' TRƯỚC TẤT CẢ before_action khác
  prepend_before_action :sanitize_project_id_param
  before_action :check_permission
  before_action :prepare_search_context, only: [:index, :search]
  
  # Lưu lại project_ids gốc và xóa khỏi params nếu chứa 'all-projects'
  def sanitize_project_id_param
    project_ids = params[:project_ids] || [params[:project_id]].compact
    
    if project_ids.include?('all-projects')
      Rails.logger.info "[CustomSearch] Detected 'all-projects', storing and removing from params"
      @original_project_ids = 'all-projects'
      params.delete(:project_ids)
      params.delete(:project_id)
    else
      @original_project_ids = project_ids
    end
  end

  # Hiển thị trang tìm kiếm
  # Render view index.html.erb
  def index
    Rails.logger.info "[CustomSearch] index action called, @accessible_projects: #{@accessible_projects.inspect}"
  end

  # Thực hiện tìm kiếm RAG và trả về kết quả
  # Hỗ trợ cả HTML và JSON format
  #
  # @return [HTML/JSON] 
  #   - HTML: Render trang index với kết quả
  #   - JSON: Response chứa:
  #     - query: Câu truy vấn tìm kiếm
  #     - results: Mảng các chunks tìm được
  #     - ai_answer: Câu trả lời từ AI
  #     - sources: Mảng các nguồn tham khảo
  #     - response_time_ms: Thời gian phản hồi (milliseconds)
  #     - error: Thông báo lỗi (nếu có)
  def search
    respond_to do |format|
      format.html { render :index }
      format.json do
        render json: {
          query: @query,
          results: @results,
          ai_answer: @ai_answer,
          sources: @sources,
          response_time_ms: @response_time_ms,
          error: @search_error
        }
      end
    end
  end

  private

  # Chuẩn bị context cho tìm kiếm
  # Khởi tạo các biến instance và thực hiện tìm kiếm nếu có query
  # Set các biến: @query, @results, @ai_answer, @sources, @response_time_ms, @search_error
  def prepare_search_context
    @query = params[:q].to_s.strip
    @results = []
    @ai_answer = nil
    @sources = []
    @response_time_ms = nil
    @search_error = nil

    # Lấy danh sách projects mà user có thể truy cập
    accessible_projects = Project.where(Project.visible_condition(User.current)).order(:name)
    
    # Xử lý project filtering
    process_project_filtering(accessible_projects)
    
    perform_search if @query.present?
  end

  # Thực hiện tìm kiếm và đo thời gian phản hồi
  # Xử lý các lỗi có thể xảy ra và set vào @search_error
  # Tính toán thời gian phản hồi và set vào @response_time_ms
  def perform_search
    start_time = Time.now
    perform_rag_search
    @response_time_ms = ((Time.now - start_time) * 1000).round(2)
  rescue CustomFeatures::SearchClient::SearchError => e
    @search_error = e.message
    Rails.logger.error("[CustomSearch] #{e.message}")
  rescue StandardError => e
    @search_error = "Đã xảy ra lỗi khi tìm kiếm: #{e.message}"
    Rails.logger.error("[CustomSearch] Lỗi không mong đợi: #{e.class} - #{e.message}")
  end

  # Thực hiện RAG search thông qua SearchClient
  # Parse response và format kết quả sử dụng SearchResultFormatter
  # Set các biến: @ai_answer, @sources, @results
  def perform_rag_search
    response = search_client.rag_search(
      query: @query, 
      list_project_ids: @list_project_ids,
      user_id: User.current.id
    )

    @ai_answer = response['answer']
    @sources = CustomFeatures::Formatters::SearchResultFormatter.format_sources(response['sources'])
    @results = CustomFeatures::Formatters::SearchResultFormatter.normalize_chunks(response['retrieved_chunks'])
  end

  # Lấy SearchClient instance (singleton pattern)
  # Sử dụng memoization để tránh tạo nhiều instance
  #
  # @return [CustomFeatures::SearchClient] SearchClient instance
  def search_client
    @search_client ||= CustomFeatures::SearchClient.instance
  end

  # Xử lý project filtering từ params
  def process_project_filtering(accessible_projects)
    @list_project_ids = nil
    @project = nil
    
    # @accessible_projects luôn là tất cả projects có dữ liệu AI (để hiển thị trong select)
    begin
      ai_project_ids = search_client.list_projects
      @accessible_projects = accessible_projects.where(id: ai_project_ids)
      Rails.logger.info "[CustomSearch] Available projects with AI data: #{ai_project_ids.inspect}"
    rescue CustomFeatures::SearchClient::SearchError => e
      # Nếu không thể kết nối AI server, hiển thị tất cả projects có thể truy cập
      @accessible_projects = accessible_projects
      Rails.logger.warn "[CustomSearch] Could not fetch AI projects, showing all accessible projects: #{e.message}"
    end
    
    # Khôi phục project_ids gốc nếu đã bị xóa
    project_ids = @original_project_ids || params[:project_ids] || [params[:project_id]].compact
    
    # Xử lý project selection
    if project_ids.present?
      if project_ids == 'all-projects' || project_ids.include?('all-projects')
        # User chọn "Tất cả" - filter theo tất cả projects có AI data
        @project = nil
        @list_project_ids = @accessible_projects.map(&:id)
        Rails.logger.info "[CustomSearch] Filtering by all available projects: #{@list_project_ids.inspect}"
      elsif project_ids.is_a?(Array) && project_ids.length > 1
        # Multiple project IDs được chọn từ multi-select
        begin
          @list_project_ids = project_ids.map(&:to_i).reject(&:zero?)
          @project = nil
          Rails.logger.info "[CustomSearch] Filtering by multiple projects: #{@list_project_ids.inspect}"
        rescue
          @list_project_ids = nil
          @project = nil
        end
      else
        # Single project ID
        begin
          project_id = project_ids.is_a?(Array) ? project_ids.first : project_ids
          @project = if project_id.to_s.match(/^\d+$/)
                       Project.find(project_id)
                     else
                       Project.find_by(identifier: project_id)
                     end
          @list_project_ids = [@project.id]
          Rails.logger.info "[CustomSearch] Filtering by single project: #{@list_project_ids.inspect}"
        rescue
          @list_project_ids = nil
          @project = nil
        end
      end
    end
  end

  # Kiểm tra quyền truy cập
  # Yêu cầu đăng nhập nếu user chưa logged in
  def check_permission
    return if User.current.logged?

    require_login
  end
end
