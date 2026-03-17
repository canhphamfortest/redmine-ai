# /usr/src/redmine/init/05_attachments.rb
# File attachments helper for projects and issues

def ensure_seed_files
  FileUtils.mkdir_p(SEED_FILES_DIR)
  
  samples = [
    # English files
    ["README-en.txt", "# README (EN)
This is a seeded file for demo purposes.

## Features
- Multilingual support
- Issue tracking
- Time tracking
- Wiki documentation
"],
    ["CHANGELOG-en.md", "# CHANGELOG (EN)

## v1.0.0
- Initial release
- Basic features implemented
- Bug fixes and improvements
"],
    ["API-docs-en.md", "# API Documentation (EN)

## Endpoints
- GET /api/issues
- POST /api/issues
- PUT /api/issues/:id
"],
    
    # Vietnamese files
    ["README-vi.txt", "# README (VI)
Đây là file tạo mẫu phục vụ demo.

## Tính năng
- Hỗ trợ đa ngôn ngữ
- Theo dõi vấn đề
- Ghi nhận thời gian
- Tài liệu Wiki
"],
    ["CHANGELOG-vi.md", "# CHANGELOG (VI)

## v1.0.0
- Phát hành đầu tiên
- Triển khai tính năng cơ bản
- Sửa lỗi và cải tiến
"],
    ["API-docs-vi.md", "# Tài liệu API (VI)

## Endpoints
- GET /api/issues - Lấy danh sách issue
- POST /api/issues - Tạo issue mới
- PUT /api/issues/:id - Cập nhật issue
"],
    
    # Japanese files
    ["README-ja.txt", "# README (日本語)
デモ用のサンプルファイルです。

## 機能
- 多言語対応
- 課題追跡
- 時間記録
- Wikiドキュメント
"],
    ["CHANGELOG-ja.md", "# CHANGELOG (日本語)

## v1.0.0
- 初回リリース
- 基本機能の実装
- バグ修正と改善
"],
    ["API-docs-ja.md", "# APIドキュメント (日本語)

## エンドポイント
- GET /api/issues - 課題一覧取得
- POST /api/issues - 課題作成
- PUT /api/issues/:id - 課題更新
"],
    
    # Build & deployment files
    ["howto-build.en.md", "## Build Instructions (EN)

1. Install dependencies: `npm install`
2. Run tests: `npm test`
3. Build: `npm run build`
4. Deploy: `npm run deploy`
"],
    ["howto-build.vi.md", "## Hướng dẫn Build (VI)

1. Cài phụ thuộc: `npm install`
2. Chạy test: `npm test`
3. Build: `npm run build`
4. Triển khai: `npm run deploy`
"],
    ["howto-build.ja.md", "## ビルド手順 (JA)

1. 依存関係をインストール: `npm install`
2. テストを実行: `npm test`
3. ビルド: `npm run build`
4. デプロイ: `npm run deploy`
"],
    
    # Configuration files
    ["config-example.json", '{"env": "production", "debug": false, "port": 3000}'],
    ["deployment.yaml", "version: '3.8'\nservices:\n  app:\n    image: myapp:latest\n    ports:\n      - 3000:3000"],
    ["requirements.txt", "django>=4.0\nrequests>=2.28\npytest>=7.0"]
  ]
  
  samples.each do |fname, content|
    path = File.join(SEED_FILES_DIR, fname)
    next if File.exist?(path)
    File.write(path, content)
  end
  
  ok "Seed files ensured in #{SEED_FILES_DIR}"
end

def attach_random_files(container, author_user, count_range)
  ensure_seed_files
  files = Dir[File.join(SEED_FILES_DIR, "*")]
  return if files.empty?

  # Robust author fallback
  author = nil
  author ||= author_user if author_user && author_user.respond_to?(:id)
  author ||= SEED_AUTHOR if defined?(SEED_AUTHOR) && SEED_AUTHOR
  author ||= (User.where(admin: true, status: 1).order(:id).first rescue nil)
  author ||= (User.find_by(login: 'admin') rescue nil)
  author ||= (User.where(status: 1).order(:id).first rescue nil)
  author ||= (User.respond_to?(:current) ? User.current : nil)
  
  unless author
    warnx "Skip attachments: no valid author user available"
    return
  end

  count = rand(count_range)
  attached = 0
  
  count.times do
    path = files.sample
    File.open(path, 'rb') do |f|
      att = Attachment.new(container: container)
      att.author = author
      att.file = f
      att.filename = File.basename(path)
      att.description = "Auto-attached by seeder"
      begin
        att.save!
        attached += 1
      rescue ActiveRecord::RecordInvalid => e
        warnx "Attachment skipped (#{e.message})"
      end
    end
  end
  
  ok "Attached #{attached} files to #{container.class.name} ##{container.id}" if attached > 0
end

# Attach project files to all projects
def attach_project_files
  say "Attaching files to projects..."
  
  ($projects_data || []).each do |data|
    project = data[:project]
    assignees = data[:assignees]
    author = assignees.first || SEED_AUTHOR
    
    attach_random_files(project, author, 2..5)
  end
  
  ok "Project files attached"
end

ok "Attachments helper loaded"