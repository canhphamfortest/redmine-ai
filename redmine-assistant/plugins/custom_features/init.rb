# Plugin registration cho Custom Features
# File này được Redmine tự động load khi plugin được kích hoạt
Redmine::Plugin.register :custom_features do
  name 'Custom Features Plugin'
  author 'CanhPN'
  description 'Plugin tùy chỉnh thêm button và text vào Related issues, Note section, và tính năng search'
  version '1.0.0'
  url 'https://example.com'
  author_url 'https://example.com'

  # Quyền để sử dụng custom search
  # public: true cho phép cả user chưa đăng nhập sử dụng (nếu cần)
  permission :use_custom_search, { custom_search: [:index, :search] }, public: true

  # Cấu hình settings cho plugin
  # Settings sẽ xuất hiện trong Administration > Plugins > Custom Features Plugin
  settings default: {
    'rag_api_base_url' => 'http://backend:8000',
    'enabled_projects' => []
  }, partial: 'custom_features/settings'
end

# ===== Load Dependencies =====
# Thứ tự load quan trọng: constants và config phải load trước các module khác

# Load constants và configuration trước (các module khác phụ thuộc vào đây)
require_relative 'lib/custom_features/constants'
require_relative 'lib/custom_features/config'
require_relative 'lib/custom_features/errors'

# Load hooks và search client (cần constants và config)
require_relative 'lib/custom_features/hooks'
require_relative 'lib/custom_features/search_client'

# Load services (cần constants, config, và search_client)
require_relative 'lib/custom_features/services/issue_content_builder'
require_relative 'lib/custom_features/services/checklist_parser'
require_relative 'lib/custom_features/services/checklist_generator'
require_relative 'lib/custom_features/services/related_issues_finder'

# Load formatters (cần constants)
require_relative 'lib/custom_features/formatters/issue_formatter'
require_relative 'lib/custom_features/formatters/search_result_formatter'

