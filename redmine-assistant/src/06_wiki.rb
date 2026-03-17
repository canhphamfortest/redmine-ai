# /usr/src/redmine/init/06_wiki.rb
# Wiki pages initialization

def ensure_wiki_home(project, title: "Home", text: nil)
  text ||= wiki_text_ml(project.name, page: title)
  
  # FIX: Tạo Wiki với start_page đúng
  wiki = project.wiki
  unless wiki
    wiki = Wiki.create!(project: project, start_page: title)
    ok "Created wiki for #{project.identifier} with start_page: #{title}"
  end
  
  # Đảm bảo start_page trỏ đúng
  if wiki.start_page != title
    wiki.update!(start_page: title)
    ok "Updated wiki start_page to: #{title}"
  end
  
  page = WikiPage.find_by(wiki_id: wiki.id, title: title)
  
  if page
    content = page.content || WikiContent.create!(page: page, text: text, author: User.current)
    if content.text.to_s.strip.empty?
      content.update!(text: text)
      ok "Updated wiki page '#{title}' in #{project.identifier}"
    end
  else
    page = WikiPage.create!(wiki: wiki, title: title)
    WikiContent.create!(page: page, text: text, author: User.current)
    ok "Created wiki page '#{title}' in #{project.identifier}"
  end
  
  page
end

def ensure_wiki_page(project, title, text = nil, comment = "")
  text ||= wiki_text_ml(project.name, page: title)
  
  # Đảm bảo wiki tồn tại
  wiki = project.wiki
  unless wiki
    # FIX: Tạo wiki với start_page = "Home"
    wiki = Wiki.create!(project: project, start_page: "Home")
    ok "Created wiki for #{project.identifier}"
  end
  
  page = WikiPage.find_by(wiki: wiki, title: title)
  
  if page
    # Update existing page
    if page.content
      page.content.update!(text: text, comments: comment)
    else
      WikiContent.create!(page: page, text: text, comments: comment, author: User.current)
    end
  else
    # Create new page
    page = WikiPage.create!(wiki: wiki, title: title)
    WikiContent.create!(page: page, text: text, comments: comment, author: User.current)
    ok "Created wiki page '#{title}' in #{project.identifier}"
  end
  
  page
end

# -------------------------
# Wiki page templates
# -------------------------

WIKI_PAGES = [
  { title: "Home", use_helper: true },
  { title: "Getting-Started", template: :getting_started },
  { title: "Architecture", template: :architecture },
  { title: "API-Reference", template: :api_reference },
  { title: "Deployment-Guide", template: :deployment },
  { title: "FAQ", template: :faq },
  { title: "Troubleshooting", use_helper: true },
  { title: "Code-Review-Guidelines", use_helper: true },
  { title: "Security-Best-Practices", use_helper: true },
  { title: "Performance-Optimization", use_helper: true },
  { title: "Testing-Strategy", use_helper: true }
]

# [Keep all wiki template functions from the original file]
# Copy tất cả các hàm wiki_template_* từ file gốc vào đây

def wiki_template_getting_started(project_name)
  <<~WIKI
  # Getting Started - #{project_name}
  
  ## 🇬🇧 Prerequisites (EN)
  
  ### Required Software
  - Git 2.30+
  - Ruby 3.1+ or Node.js 18+
  - PostgreSQL 14+
  - Redis 7+
  - Docker & Docker Compose
  
  ### Environment Setup
  1. Clone the repository:
     ```bash
     git clone https://github.com/yourorg/#{project_name.downcase.gsub(' ', '-')}.git
     cd #{project_name.downcase.gsub(' ', '-')}
     ```
  
  2. Install dependencies:
     ```bash
     bundle install  # For Ruby
     npm install     # For Node.js
     ```
  
  3. Configure environment:
     ```bash
     cp .env.example .env
     # Edit .env with your settings
     ```
  
  4. Setup database:
     ```bash
     rails db:create db:migrate db:seed
     ```
  
  5. Start development server:
     ```bash
     rails server
     # or
     npm run dev
     ```
  
  ### Verification
  - Access http://localhost:3000
  - Login with default credentials (see .env file)
  - Check all services are running: `docker ps`
  
  ---
  
  ## 🇻🇳 Yêu cầu (VI)
  
  ### Phần mềm Cần thiết
  - Git 2.30+
  - Ruby 3.1+ hoặc Node.js 18+
  - PostgreSQL 14+
  - Redis 7+
  - Docker & Docker Compose
  
  ### Thiết lập Môi trường
  1. Clone repository
  2. Cài đặt dependencies
  3. Cấu hình environment
  4. Setup database
  5. Khởi động development server
  
  ---
  
  ## 🇯🇵 前提条件 (JA)
  
  ### 必要なソフトウェア
  - Git 2.30+
  - Ruby 3.1+ または Node.js 18+
  - PostgreSQL 14+
  - Redis 7+
  - Docker & Docker Compose
  WIKI
end

def wiki_template_architecture(project_name)
  <<~WIKI
  # Architecture - #{project_name}
  
  ## 🇬🇧 System Design (EN)
  
  ### High-Level Architecture
  ```
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │   Client    │─────▶│  API Gateway │─────▶│   Backend   │
  │  (React)    │      │   (Nginx)    │      │   (Rails)   │
  └─────────────┘      └─────────────┘      └─────────────┘
                                                      │
                                                      ▼
                              ┌─────────────┬─────────────┬─────────────┐
                              │  PostgreSQL │    Redis    │   S3/Minio  │
                              │  (Primary)  │   (Cache)   │  (Storage)  │
                              └─────────────┴─────────────┴─────────────┘
  ```
  
  ### Components
  - **API Gateway**: Request routing, rate limiting, SSL termination
  - **Backend Service**: Business logic, authentication, background jobs
  - **Database Layer**: PostgreSQL (primary), Redis (cache), S3 (files)
  
  ---
  
  ## 🇻🇳 Thiết kế Hệ thống (VI)
  
  Hệ thống sử dụng kiến trúc microservices với các thành phần độc lập.
  
  ---
  
  ## 🇯🇵 システム設計 (JA)
  
  システムはマイクロサービスアーキテクチャを採用しています。
  WIKI
end

def wiki_template_api_reference(project_name)
  <<~WIKI
  # API Reference - #{project_name}
  
  ## 🇬🇧 Authentication (EN)
  
  All API requests require JWT token authentication:
  ```
  Authorization: Bearer <your_jwt_token>
  ```
  
  ### Get Auth Token
  ```http
  POST /api/v1/auth/login
  Content-Type: application/json
  
  {
    "email": "user@example.com",
    "password": "secure_password"
  }
  ```
  
  **Response**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900
  }
  ```
  
  ---
  
  ## 🇬🇧 Issues API (EN)
  
  ### List Issues
  ```http
  GET /api/v1/issues?page=1&per_page=25&status=open
  ```
  
  **Query Parameters**:
  - `page` (integer): Page number (default: 1)
  - `per_page` (integer): Items per page (default: 25, max: 100)
  - `status` (string): Filter by status (open, closed, all)
  - `priority` (string): Filter by priority
  
  **Response**:
  ```json
  {
    "issues": [
      {
        "id": 1,
        "subject": "[BUG] Cannot save form",
        "status": "open",
        "priority": "high"
      }
    ],
    "total": 150,
    "page": 1
  }
  ```
  
  ---
  
  ## 🇻🇳 API Issues (VI)
  
  ### Lấy Danh sách Issues
  ```http
  GET /api/v1/issues?page=1&per_page=25
  ```
  
  ---
  
  ## 🇯🇵 Issues API (JA)
  
  ### 課題一覧取得
  ```http
  GET /api/v1/issues?page=1&per_page=25
  ```
  WIKI
end

def wiki_template_deployment(project_name)
  <<~WIKI
  # Deployment Guide - #{project_name}
  
  ## 🇬🇧 Production Deployment (EN)
  
  ### Prerequisites
  - Kubernetes cluster (v1.25+)
  - kubectl configured
  - Docker registry access
  - Database backup completed
  
  ### Deployment Steps
  
  #### 1. Build Docker Image
  ```bash
  docker build -t registry.example.com/#{project_name.downcase}:v1.2.3 .
  docker push registry.example.com/#{project_name.downcase}:v1.2.3
  ```
  
  #### 2. Database Migration
  ```bash
  kubectl create job --from=cronjob/db-migrate migrate-v1.2.3
  kubectl logs -f job/migrate-v1.2.3
  ```
  
  #### 3. Update Deployment
  ```bash
  kubectl set image deployment/#{project_name.downcase} \\
    app=registry.example.com/#{project_name.downcase}:v1.2.3
  kubectl rollout status deployment/#{project_name.downcase}
  ```
  
  ### Rollback
  ```bash
  kubectl rollout undo deployment/#{project_name.downcase}
  ```
  
  ---
  
  ## 🇻🇳 Triển khai Production (VI)
  
  ### Các Bước Triển khai
  1. Build Docker image
  2. Database migration
  3. Update deployment
  4. Health check
  
  ---
  
  ## 🇯🇵 本番デプロイ (JA)
  
  ### デプロイ手順
  1. Dockerイメージのビルド
  2. データベースマイグレーション
  3. デプロイメント更新
  WIKI
end

def wiki_template_faq(project_name)
  <<~WIKI
  # FAQ - #{project_name}
  
  ## 🇬🇧 Frequently Asked Questions (EN)
  
  ### General Questions
  
  **Q: How do I reset my password?**
  A: Click "Forgot Password" on the login page. You'll receive a reset link via email.
  
  **Q: How do I report a bug?**
  A: Go to Issues → New Issue, select "Bug" tracker, fill in details and submit.
  
  **Q: Who do I contact for access issues?**
  A: Contact your project manager or email support@example.com
  
  ### Technical Questions
  
  **Q: What browsers are supported?**
  A: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
  
  **Q: How do I upload attachments?**
  A: Drag and drop files or click "Choose Files". Max size: 10MB.
  
  **Q: Can I use the API programmatically?**
  A: Yes. Generate an API key in My Account → API access key.
  
  ---
  
  ## 🇻🇳 Câu hỏi Thường gặp (VI)
  
  **Q: Làm sao để reset mật khẩu?**
  A: Click "Quên mật khẩu" trên trang đăng nhập.
  
  **Q: Làm sao để báo lỗi?**
  A: Vào Issues → Issue mới, chọn tracker "Bug".
  
  ---
  
  ## 🇯🇵 よくある質問 (JA)
  
  **Q: パスワードをリセットするには?**
  A: ログインページの「パスワードを忘れた」をクリック。
  
  **Q: バグを報告するには?**
  A: 課題 → 新しい課題、「Bug」を選択。
  WIKI
end

# -------------------------
# Execute wiki setup
# -------------------------

def setup_wiki_pages
  say "Setting up wiki pages..."
  
  # Lưu user hiện tại
  current_user = User.current
  User.current = seed_author! if User.current.nil?
  
  ($projects_data || []).each do |data|
    project = data[:project]
    
    # FIX: Tạo Home page đầu tiên
    ensure_wiki_home(project, title: "Home")
    
    # Sau đó tạo các pages khác
    WIKI_PAGES.each do |page_def|
      title = page_def[:title]
      next if title == "Home"  # Skip vì đã tạo ở trên
      
      if page_def[:use_helper]
        # Use helper function from 01_i18n_helpers.rb
        text = wiki_text_ml(project.name, page: title)
        ensure_wiki_page(project, title, text, "Auto-generated by seeder")
      elsif page_def[:template]
        # Use local template function
        template_method = "wiki_template_#{page_def[:template]}"
        if respond_to?(template_method)
          text = send(template_method, project.name)
          ensure_wiki_page(project, title, text, "Auto-generated by seeder")
        else
          ensure_wiki_page(project, title)
        end
      else
        ensure_wiki_page(project, title)
      end
    end
  end
  
  # Restore user
  User.current = current_user
  
  ok "Wiki pages setup completed"
end

ok "Wiki helper loaded"