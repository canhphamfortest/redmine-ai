# Routes cho Custom Features plugin
# Redmine sẽ tự động load file này khi plugin được kích hoạt
#
# Routes được định nghĩa ở đây sẽ được merge vào routes của Redmine
# Tất cả routes đều yêu cầu user đăng nhập (trừ khi được đánh dấu public)

# Custom Search routes
# Cho phép tìm kiếm sử dụng AI (RAG search)
get 'custom_search', to: 'custom_search#index', as: 'custom_search'
post 'custom_search', to: 'custom_search#search'

# Custom Features routes
# Lấy thông tin issue (proxy endpoint cho JavaScript)
# GET /issues/:issue_id/get_issue_info
get 'issues/:issue_id/get_issue_info', to: 'custom_features/custom_features#get_issue_info', as: 'get_issue_info'

# Tạo draft note với checklist được tạo bởi AI
# POST /issues/:issue_id/create_draft_note
post 'issues/:issue_id/create_draft_note', to: 'custom_features/custom_features#create_draft_note', as: 'create_draft_note'

# Tìm issues liên quan sử dụng AI
# GET /issues/:issue_id/find_related_issues
get 'issues/:issue_id/find_related_issues', to: 'custom_features/custom_features#find_related_issues', as: 'find_related_issues'
