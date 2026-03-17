# /usr/src/redmine/init/01_i18n_helpers.rb
# Multilingual content generators (EN/VI/JA)

# ===== Language samples =====
ISSUE_TEMPLATES = {
  bug: [
    {
      en: "Cannot save form",
      vi: "Không lưu được form",
      ja: "フォームを保存できません",
      desc_en: "When submitting the form with special characters, validation fails silently",
      desc_vi: "Khi gửi form có ký tự đặc biệt, validation thất bại không có thông báo",
      desc_ja: "特殊文字を含むフォームを送信すると、バリデーションが静かに失敗します",
      steps_en: ["Open form page", "Enter special characters (@#$%) in name field", "Click Save button", "Form doesn't submit, no error shown"],
      steps_vi: ["Mở trang form", "Nhập ký tự đặc biệt (@#$%) vào trường tên", "Click nút Lưu", "Form không được gửi, không có thông báo lỗi"],
      steps_ja: ["フォームページを開く", "名前フィールドに特殊文字(@#$%)を入力", "保存ボタンをクリック", "フォームが送信されず、エラーも表示されない"]
    },
    {
      en: "Fix layout glitches",
      vi: "Sửa lỗi giao diện",
      ja: "レイアウトの不具合修正",
      desc_en: "Navigation menu overlaps with content on mobile devices",
      desc_vi: "Menu điều hướng bị chồng lên nội dung trên thiết bị di động",
      desc_ja: "モバイルデバイスでナビゲーションメニューがコンテンツと重なる",
      steps_en: ["Open app on mobile browser", "Navigate to dashboard", "Menu covers content area", "Cannot interact with buttons"],
      steps_vi: ["Mở app trên trình duyệt di động", "Điều hướng đến dashboard", "Menu che phủ vùng nội dung", "Không thể tương tác với các nút"],
      steps_ja: ["モバイルブラウザでアプリを開く", "ダッシュボードに移動", "メニューがコンテンツエリアを覆う", "ボタンを操作できない"]
    },
    {
      en: "Memory leak detected",
      vi: "Phát hiện rò rỉ bộ nhớ",
      ja: "メモリリークを検出",
      desc_en: "Application memory usage grows continuously during long sessions",
      desc_vi: "Mức sử dụng bộ nhớ của ứng dụng tăng liên tục trong phiên làm việc dài",
      desc_ja: "長時間のセッション中にアプリケーションのメモリ使用量が継続的に増加",
      steps_en: ["Start application", "Monitor memory usage", "Perform normal operations for 2+ hours", "Memory increases from 200MB to 2GB"],
      steps_vi: ["Khởi động ứng dụng", "Giám sát mức dùng bộ nhớ", "Thực hiện các thao tác bình thường trong 2+ giờ", "Bộ nhớ tăng từ 200MB lên 2GB"],
      steps_ja: ["アプリケーションを起動", "メモリ使用量を監視", "2時間以上通常の操作を実行", "メモリが200MBから2GBに増加"]
    },
    {
      en: "Database migration needed",
      vi: "Cần migration database",
      ja: "データベース移行が必要",
      desc_en: "Schema changes require proper migration to avoid data loss",
      desc_vi: "Thay đổi schema cần migration đúng cách để tránh mất dữ liệu",
      desc_ja: "スキーマ変更にはデータ損失を避けるための適切な移行が必要",
      steps_en: ["Review schema changes", "Create migration script", "Test on staging environment", "Backup production database"],
      steps_vi: ["Xem xét thay đổi schema", "Tạo script migration", "Test trên môi trường staging", "Backup database production"],
      steps_ja: ["スキーマ変更をレビュー", "マイグレーションスクリプトを作成", "ステージング環境でテスト", "本番データベースをバックアップ"]
    },
    {
      en: "Security vulnerability found",
      vi: "Phát hiện lỗ hổng bảo mật",
      ja: "セキュリティ脆弱性発見",
      desc_en: "SQL injection vulnerability in search endpoint allows unauthorized data access",
      desc_vi: "Lỗ hổng SQL injection trong endpoint tìm kiếm cho phép truy cập dữ liệu trái phép",
      desc_ja: "検索エンドポイントのSQLインジェクション脆弱性により不正なデータアクセスが可能",
      steps_en: ["Access /api/search endpoint", "Inject SQL in query parameter", "Database returns sensitive data", "Immediate patch required"],
      steps_vi: ["Truy cập endpoint /api/search", "Inject SQL vào tham số query", "Database trả về dữ liệu nhạy cảm", "Cần vá ngay lập tức"],
      steps_ja: ["/api/searchエンドポイントにアクセス", "クエリパラメータにSQLをインジェクション", "データベースが機密データを返す", "即座のパッチが必要"]
    },
        # Template mới 1: Performance issue
    {
      en: "Page load extremely slow",
      vi: "Trang tải cực kỳ chậm",
      ja: "ページの読み込みが非常に遅い",
      desc_en: "Dashboard takes over 10 seconds to load on first visit",
      desc_vi: "Dashboard mất hơn 10 giây để tải lần đầu truy cập",
      desc_ja: "初回訪問時にダッシュボードの読み込みに10秒以上かかる",
      steps_en: ["Clear browser cache", "Navigate to /dashboard", "Wait for page load", "Observe 10+ second delay"],
      steps_vi: ["Xóa cache trình duyệt", "Truy cập /dashboard", "Đợi trang tải", "Thấy độ trễ 10+ giây"],
      steps_ja: ["ブラウザキャッシュをクリア", "/dashboardに移動", "ページ読み込みを待つ", "10秒以上の遅延を確認"]
    },
    
    # Template mới 2: UI/UX bug
    {
      en: "Button not responding to clicks",
      vi: "Nút bấm không phản hồi",
      ja: "ボタンがクリックに応答しない",
      desc_en: "Submit button appears clickable but does nothing when clicked",
      desc_vi: "Nút Submit có vẻ có thể click nhưng không làm gì khi bấm",
      desc_ja: "送信ボタンはクリック可能に見えるが、クリックしても何も起こらない",
      steps_en: ["Go to form page", "Fill in all required fields", "Click Submit button", "Nothing happens"],
      steps_vi: ["Vào trang form", "Điền đầy đủ các trường bắt buộc", "Click nút Submit", "Không có gì xảy ra"],
      steps_ja: ["フォームページに移動", "必須フィールドをすべて入力", "送信ボタンをクリック", "何も起こらない"]
    },
    
    # Template mới 3: Authentication issue
    {
      en: "Session expires too quickly",
      vi: "Phiên làm việc hết hạn quá nhanh",
      ja: "セッションの有効期限が早すぎる",
      desc_en: "Users are logged out after 5 minutes of inactivity, expected 30 minutes",
      desc_vi: "Người dùng bị đăng xuất sau 5 phút không hoạt động, mong đợi 30 phút",
      desc_ja: "5分間操作しないとログアウトされる、30分が期待値",
      steps_en: ["Login to system", "Leave tab idle for 6 minutes", "Try to interact", "Session expired error"],
      steps_vi: ["Đăng nhập hệ thống", "Để tab không hoạt động 6 phút", "Thử tương tác", "Lỗi phiên hết hạn"],
      steps_ja: ["システムにログイン", "タブを6分間放置", "操作を試みる", "セッション期限切れエラー"]
    },
    
    # Template mới 4: Data consistency
    {
      en: "Data not syncing across tabs",
      vi: "Dữ liệu không đồng bộ giữa các tab",
      ja: "タブ間でデータが同期されない",
      desc_en: "Changes made in one browser tab are not reflected in other open tabs",
      desc_vi: "Thay đổi thực hiện ở tab này không hiển thị ở các tab khác đang mở",
      desc_ja: "あるブラウザタブで行った変更が他の開いているタブに反映されない",
      steps_en: ["Open app in two browser tabs", "Make changes in tab 1", "Check tab 2", "Old data still showing"],
      steps_vi: ["Mở app trong 2 tab trình duyệt", "Thay đổi ở tab 1", "Kiểm tra tab 2", "Vẫn hiển thị dữ liệu cũ"],
      steps_ja: ["アプリを2つのブラウザタブで開く", "タブ1で変更", "タブ2を確認", "古いデータが表示されたまま"]
    },
    
    # Template mới 5: Mobile issue
    {
      en: "Touch gestures not working on mobile",
      vi: "Thao tác chạm không hoạt động trên mobile",
      ja: "モバイルでタッチジェスチャーが機能しない",
      desc_en: "Swipe and pinch-to-zoom gestures fail on iOS Safari",
      desc_vi: "Thao tác vuốt và phóng to bằng hai ngón tay không hoạt động trên iOS Safari",
      desc_ja: "iOS Safariでスワイプとピンチズームのジェスチャーが失敗する",
      steps_en: ["Open app on iPhone Safari", "Try to swipe left/right", "Try pinch-to-zoom", "Gestures don't work"],
      steps_vi: ["Mở app trên iPhone Safari", "Thử vuốt trái/phải", "Thử phóng to bằng 2 ngón", "Thao tác không hoạt động"],
      steps_ja: ["iPhone SafariでアプリをOpen", "左右にスワイプを試す", "ピンチズームを試す", "ジェスチャーが動作しない"]
    },
    
    # Template mới 6: File upload issue
    {
      en: "Large file upload fails silently",
      vi: "Upload file lớn thất bại không báo lỗi",
      ja: "大きなファイルのアップロードが静かに失敗する",
      desc_en: "Files over 5MB fail to upload with no error message shown",
      desc_vi: "File trên 5MB không upload được nhưng không có thông báo lỗi",
      desc_ja: "5MB以上のファイルがアップロード失敗してもエラーメッセージが表示されない",
      steps_en: ["Select file larger than 5MB", "Click upload button", "Progress bar reaches 100%", "File not saved, no error"],
      steps_vi: ["Chọn file lớn hơn 5MB", "Click nút upload", "Thanh tiến trình đạt 100%", "File không được lưu, không có lỗi"],
      steps_ja: ["5MB以上のファイルを選択", "アップロードボタンをクリック", "プログレスバーが100%に達する", "ファイルが保存されず、エラーなし"]
    },
    
    # Template mới 7: Browser compatibility
    {
      en: "Feature broken in Firefox",
      vi: "Tính năng bị lỗi trên Firefox",
      ja: "Firefoxで機能が壊れている",
      desc_en: "Drag-and-drop functionality works in Chrome but fails in Firefox",
      desc_vi: "Tính năng kéo-thả hoạt động trên Chrome nhưng lỗi trên Firefox",
      desc_ja: "ドラッグ&ドロップ機能はChromeでは動作するがFirefoxでは失敗する",
      steps_en: ["Open in Firefox 120+", "Try to drag item", "Drop in target area", "Item snaps back to origin"],
      steps_vi: ["Mở trên Firefox 120+", "Thử kéo item", "Thả vào vùng đích", "Item quay lại vị trí ban đầu"],
      steps_ja: ["Firefox 120+で開く", "アイテムをドラッグ", "ターゲットエリアにドロップ", "アイテムが元の位置に戻る"]
    }
  ],
  task: [
    {
      en: "Improve pipeline",
      vi: "Cải thiện pipeline",
      ja: "パイプラインの改善",
      desc_en: "Current CI/CD pipeline takes 45 minutes, needs optimization",
      desc_vi: "Pipeline CI/CD hiện tại mất 45 phút, cần tối ưu hóa",
      desc_ja: "現在のCI/CDパイプラインは45分かかり、最適化が必要",
      steps_en: ["Analyze current pipeline stages", "Identify bottlenecks", "Implement parallel testing", "Cache dependencies"],
      steps_vi: ["Phân tích các giai đoạn pipeline hiện tại", "Xác định điểm nghẽn", "Triển khai test song song", "Cache dependencies"],
      steps_ja: ["現在のパイプラインステージを分析", "ボトルネックを特定", "並列テストを実装", "依存関係をキャッシュ"]
    },
    {
      en: "Refactor API",
      vi: "Tái cấu trúc API",
      ja: "APIのリファクタ",
      desc_en: "API endpoints need restructuring for better maintainability and performance",
      desc_vi: "Các endpoint API cần tái cấu trúc để dễ bảo trì và hiệu suất tốt hơn",
      desc_ja: "APIエンドポイントは保守性とパフォーマンスの向上のために再構築が必要",
      steps_en: ["Document current API structure", "Design new endpoint hierarchy", "Implement backward compatibility", "Update API documentation"],
      steps_vi: ["Tài liệu hóa cấu trúc API hiện tại", "Thiết kế cấu trúc endpoint mới", "Triển khai tương thích ngược", "Cập nhật tài liệu API"],
      steps_ja: ["現在のAPI構造を文書化", "新しいエンドポイント階層を設計", "後方互換性を実装", "APIドキュメントを更新"]
    },
    {
      en: "Add unit tests",
      vi: "Thêm unit test",
      ja: "単体テストを追加",
      desc_en: "Critical modules lack test coverage, target is 80% coverage",
      desc_vi: "Các module quan trọng thiếu test coverage, mục tiêu là 80%",
      desc_ja: "重要なモジュールにテストカバレッジが不足、目標は80%",
      steps_en: ["Identify uncovered modules", "Write test cases for core functions", "Set up test fixtures", "Run coverage report"],
      steps_vi: ["Xác định các module chưa có test", "Viết test case cho các hàm cốt lõi", "Thiết lập test fixtures", "Chạy báo cáo coverage"],
      steps_ja: ["未カバーのモジュールを特定", "コア機能のテストケースを作成", "テストフィクスチャをセットアップ", "カバレッジレポートを実行"]
    },
    {
      en: "Update dependencies",
      vi: "Cập nhật phụ thuộc",
      ja: "依存関係を更新",
      desc_en: "Several packages have security updates and new features available",
      desc_vi: "Một số package có cập nhật bảo mật và tính năng mới",
      desc_ja: "いくつかのパッケージにセキュリティ更新と新機能が利用可能",
      steps_en: ["Check outdated packages", "Review changelogs", "Update in development environment", "Run full test suite"],
      steps_vi: ["Kiểm tra các package cũ", "Xem xét changelog", "Cập nhật trong môi trường dev", "Chạy toàn bộ test suite"],
      steps_ja: ["古いパッケージをチェック", "変更履歴をレビュー", "開発環境で更新", "完全なテストスイートを実行"]
    },
    {
      en: "Optimize query",
      vi: "Tối ưu truy vấn",
      ja: "クエリ最適化",
      desc_en: "Dashboard query takes 8 seconds, needs indexing and optimization",
      desc_vi: "Truy vấn dashboard mất 8 giây, cần đánh index và tối ưu",
      desc_ja: "ダッシュボードクエリに8秒かかり、インデックス化と最適化が必要",
      steps_en: ["Profile slow queries", "Add database indexes", "Rewrite complex joins", "Implement query caching"],
      steps_vi: ["Profile các query chậm", "Thêm index database", "Viết lại các join phức tạp", "Triển khai cache query"],
      steps_ja: ["遅いクエリをプロファイル", "データベースインデックスを追加", "複雑なジョインを書き直し", "クエリキャッシングを実装"]
    },
     {
      en: "Set up monitoring alerts",
      vi: "Thiết lập cảnh báo giám sát",
      ja: "監視アラートの設定",
      desc_en: "Configure alerting for key system metrics: CPU, memory, disk, response time",
      desc_vi: "Cấu hình cảnh báo cho các chỉ số hệ thống chính: CPU, bộ nhớ, disk, thời gian phản hồi",
      desc_ja: "主要なシステムメトリクスのアラート設定：CPU、メモリ、ディスク、応答時間",
      steps_en: ["Define alert thresholds", "Set up Prometheus rules", "Configure Slack notifications", "Test alert triggers"],
      steps_vi: ["Định nghĩa ngưỡng cảnh báo", "Thiết lập rules Prometheus", "Cấu hình thông báo Slack", "Test trigger cảnh báo"],
      steps_ja: ["アラート閾値を定義", "Prometheusルールを設定", "Slack通知を設定", "アラートトリガーをテスト"]
    },
    
    # Template task mới 2
    {
      en: "Implement caching layer",
      vi: "Triển khai lớp caching",
      ja: "キャッシング層の実装",
      desc_en: "Add Redis caching for frequently accessed data to reduce database load",
      desc_vi: "Thêm Redis caching cho dữ liệu thường xuyên truy cập để giảm tải database",
      desc_ja: "頻繁にアクセスされるデータにRedisキャッシングを追加してデータベース負荷を軽減",
      steps_en: ["Identify hot queries", "Design cache key structure", "Implement cache warming", "Add cache invalidation logic"],
      steps_vi: ["Xác định các query nóng", "Thiết kế cấu trúc cache key", "Triển khai cache warming", "Thêm logic invalidation cache"],
      steps_ja: ["ホットクエリを特定", "キャッシュキー構造を設計", "キャッシュウォーミングを実装", "キャッシュ無効化ロジックを追加"]
    },
    
    # Template task mới 3
    {
      en: "Create admin dashboard",
      vi: "Tạo dashboard quản trị",
      ja: "管理ダッシュボードの作成",
      desc_en: "Build comprehensive admin panel for system monitoring and user management",
      desc_vi: "Xây dựng panel quản trị toàn diện cho giám sát hệ thống và quản lý người dùng",
      desc_ja: "システム監視とユーザー管理のための包括的な管理パネルを構築",
      steps_en: ["Design dashboard layout", "Implement real-time metrics", "Add user management features", "Create audit log viewer"],
      steps_vi: ["Thiết kế layout dashboard", "Triển khai metrics thời gian thực", "Thêm tính năng quản lý user", "Tạo trình xem audit log"],
      steps_ja: ["ダッシュボードレイアウトを設計", "リアルタイムメトリクスを実装", "ユーザー管理機能を追加", "監査ログビューアーを作成"]
    },
    
    # Template task mới 4
    {
      en: "Write integration tests",
      vi: "Viết integration tests",
      ja: "統合テストを作成",
      desc_en: "Add comprehensive integration tests for critical user workflows",
      desc_vi: "Thêm integration tests toàn diện cho các luồng người dùng quan trọng",
      desc_ja: "重要なユーザーワークフローの包括的な統合テストを追加",
      steps_en: ["Map critical user journeys", "Write test scenarios", "Set up test fixtures", "Integrate with CI pipeline"],
      steps_vi: ["Map các hành trình user quan trọng", "Viết test scenarios", "Thiết lập test fixtures", "Tích hợp với CI pipeline"],
      steps_ja: ["重要なユーザージャーニーをマップ", "テストシナリオを作成", "テストフィクスチャを設定", "CIパイプラインに統合"]
    },
    
    # Template task mới 5
    {
      en: "Upgrade third-party libraries",
      vi: "Nâng cấp thư viện bên thứ ba",
      ja: "サードパーティライブラリのアップグレード",
      desc_en: "Update all dependencies to latest stable versions for security and features",
      desc_vi: "Cập nhật tất cả dependencies lên phiên bản ổn định mới nhất cho bảo mật và tính năng",
      desc_ja: "セキュリティと機能のためにすべての依存関係を最新の安定版に更新",
      steps_en: ["Audit current dependencies", "Check breaking changes", "Update package.json/Gemfile", "Run full test suite"],
      steps_vi: ["Kiểm tra dependencies hiện tại", "Kiểm tra breaking changes", "Cập nhật package.json/Gemfile", "Chạy full test suite"],
      steps_ja: ["現在の依存関係を監査", "破壊的変更を確認", "package.json/Gemfileを更新", "完全なテストスイートを実行"]
    }
  ]
}

# ===== Note/Journal templates =====
JOURNAL_TEMPLATES = {
  investigation: {
    en: "Started investigating this issue. Initial analysis suggests it's related to %{component}.",
    vi: "Bắt đầu điều tra vấn đề này. Phân tích ban đầu cho thấy liên quan đến %{component}.",
    ja: "この問題の調査を開始しました。初期分析では%{component}に関連していることが示唆されています。"
  },
  progress: {
    en: "Made progress on this. Found that %{finding}. Will continue tomorrow.",
    vi: "Đã có tiến triển. Phát hiện ra %{finding}. Sẽ tiếp tục vào ngày mai.",
    ja: "進展がありました。%{finding}ことが判明しました。明日続けます。"
  },
  blocker: {
    en: "Blocked by %{blocker}. Need assistance from %{team} team.",
    vi: "Bị chặn bởi %{blocker}. Cần hỗ trợ từ team %{team}.",
    ja: "%{blocker}によってブロックされています。%{team}チームからの支援が必要です。"
  },
  solution: {
    en: "Found solution: %{solution}. Testing in progress.",
    vi: "Tìm thấy giải pháp: %{solution}. Đang trong quá trình test.",
    ja: "解決策が見つかりました:%{solution}。テスト中です。"
  },
  review: {
    en: "Code review completed. Minor changes requested: %{changes}.",
    vi: "Hoàn thành review code. Yêu cầu thay đổi nhỏ: %{changes}.",
    ja: "コードレビューが完了しました。軽微な変更を要求:%{changes}。"
  },
  completed: {
    en: "Issue resolved and verified in %{environment}. Ready for deployment.",
    vi: "Vấn đề đã được giải quyết và xác minh trong %{environment}. Sẵn sàng deploy.",
    ja: "%{environment}で問題が解決され、検証されました。デプロイの準備が整いました。"
  },
    meeting: {
    en: "Discussed in %{team} meeting. Action items: %{action}.",
    vi: "Đã thảo luận trong cuộc họp %{team}. Công việc cần làm: %{action}.",
    ja: "%{team}ミーティングで議論しました。アクションアイテム：%{action}。"
  },
  
  testing: {
    en: "Testing completed in %{environment}. Result: %{result}.",
    vi: "Hoàn thành testing trong %{environment}. Kết quả: %{result}.",
    ja: "%{environment}でテスト完了。結果：%{result}。"
  },
  
  deployment: {
    en: "Deployed to %{environment} at %{time}. Status: %{status}.",
    vi: "Đã deploy lên %{environment} lúc %{time}. Trạng thái: %{status}.",
    ja: "%{time}に%{environment}へデプロイしました。ステータス：%{status}。"
  },
  
  assigned: {
    en: "Assigned to %{assignee}. Priority: %{priority}.",
    vi: "Đã gán cho %{assignee}. Độ ưu tiên: %{priority}.",
    ja: "%{assignee}に割り当てました。優先度：%{priority}。"
  },
  
  waiting: {
    en: "Waiting for %{dependency} to be completed. ETA: %{eta}.",
    vi: "Đang đợi %{dependency} hoàn thành. Thời gian dự kiến: %{eta}.",
    ja: "%{dependency}の完了を待っています。予定：%{eta}。"
  },
  
  escalated: {
    en: "Escalated to %{team} team due to %{reason}.",
    vi: "Đã chuyển lên team %{team} do %{reason}.",
    ja: "%{reason}のため%{team}チームにエスカレートしました。"
  }
}

JOURNAL_PARAMS = {
  component: ["authentication module", "database layer", "API gateway", "caching system", "frontend router"],
  finding: ["the root cause is a race condition", "memory is not being freed properly", "cache is stale", "validation logic is incorrect"],
  blocker: ["missing API documentation", "environment not ready", "dependency conflict", "database permissions"],
  team: ["DevOps", "Backend", "Frontend", "QA", "Security"],
  solution: ["add proper error handling", "implement retry logic", "use connection pooling", "optimize algorithm"],
  changes: ["add null checks", "improve variable naming", "add comments", "extract helper function"],
  environment: ["staging", "QA environment", "pre-production", "local testing"],
  action: ["update documentation", "schedule follow-up", "review implementation", "notify stakeholders"],
  result: ["all tests passed", "found 3 minor issues", "performance improved by 40%", "ready for production"],
  time: ["14:30", "09:00", "16:45", "11:20"],
  status: ["successful", "in progress", "monitoring", "stable"],
  assignee: ["John", "Sarah", "Mike", "Emily"],
  priority: ["high", "normal", "urgent"],
  dependency: ["backend API", "database migration", "third-party service", "code review"],
  eta: ["2 hours", "tomorrow", "end of week", "next sprint"],
  reason: ["complexity", "security concerns", "requires expertise", "time constraints"]
}

# ===== Content generators =====

def get_issue_template(tracker_name)
  type = tracker_name.downcase == "bug" ? :bug : :task
  ISSUE_TEMPLATES[type].sample
end

# FIX: Trả về cả template để subject và description dùng chung
def get_issue_content(tracker_name, subj_prefix = nil)
  template = get_issue_template(tracker_name)
  prefix = tracker_name == "Bug" ? (subj_prefix || "[BUG]") : (subj_prefix || "[TASK]")
  
  {
    template: template,
    subject: "#{prefix} #{template[:en]} | #{template[:vi]} | #{template[:ja]}",
    description: build_description(tracker_name, template)
  }
end

def subject_ml(tracker_name, subj_prefix = nil)
  # Deprecated: Use get_issue_content instead
  template = get_issue_template(tracker_name)
  prefix = tracker_name == "Bug" ? (subj_prefix || "[BUG]") : (subj_prefix || "[TASK]")
  "#{prefix} #{template[:en]} | #{template[:vi]} | #{template[:ja]}"
end

def description_ml(tracker_name = "Task")
  # Deprecated: Use get_issue_content instead
  template = get_issue_template(tracker_name)
  build_description(tracker_name, template)
end

def build_description(tracker_name, template)
  tech_detail = realistic_technical_paragraph
  
  en_steps = template[:steps_en].map.with_index { |step, i| "#{i + 1}. #{step}" }.join("\n")
  vi_steps = template[:steps_vi].map.with_index { |step, i| "#{i + 1}. #{step}" }.join("\n")
  ja_steps = template[:steps_ja].map.with_index { |step, i| "#{i + 1}. #{step}" }.join("\n")
  
  <<~MD
  # 🇬🇧 EN
  
  ## Description
  #{template[:desc_en]}
  
  ## Technical Details
  #{tech_detail}
  
  ## Steps to Reproduce / Implementation Plan
  #{en_steps}
  
  ## Expected Result
  The system should work as documented and meet all requirements.
  
  ## Actual Result
  Current behavior differs from expectations and needs to be addressed.
  
  ---
  
  # 🇻🇳 VI
  
  ## Mô tả
  #{template[:desc_vi]}
  
  ## Chi tiết Kỹ thuật
  #{tech_detail}
  
  ## Các bước tái hiện / Kế hoạch thực hiện
  #{vi_steps}
  
  ## Kết quả mong đợi
  Hệ thống hoạt động đúng như tài liệu và đáp ứng tất cả yêu cầu.
  
  ## Kết quả thực tế
  Hành vi hiện tại khác với kỳ vọng và cần được xử lý.
  
  ---
  
  # 🇯🇵 日本語
  
  ## 説明
  #{template[:desc_ja]}
  
  ## 技術詳細
  #{tech_detail}
  
  ## 再現手順 / 実装計画
  #{ja_steps}
  
  ## 期待される結果
  システムはドキュメント通りに動作し、すべての要件を満たす必要があります。
  
  ## 実際の結果
  現在の動作は期待と異なり、対処が必要です。
  MD
end

def generate_journal_note(type = nil)
  type ||= JOURNAL_TEMPLATES.keys.sample
  template = JOURNAL_TEMPLATES[type]
  
  # Replace placeholders with random params
  params = {}
  template[:en].scan(/%\{(\w+)\}/).flatten.uniq.each do |param|
    params[param.to_sym] = JOURNAL_PARAMS[param.to_sym]&.sample || "unknown"
  end
  
  en = template[:en] % params
  vi = template[:vi] % params
  ja = template[:ja] % params
  
  <<~NOTE.strip
  🇬🇧 #{en}
  
  🇻🇳 #{vi}
  
  🇯🇵 #{ja}
  NOTE
end

def faker_sentence
  if FAKER_AVAILABLE
    Faker::Lorem.sentence(word_count: 3, random_words_to_add: 2)
  else
    [
      "Issue needs investigation and resolution",
      "Please review the implementation details",
      "Consider alternative approaches",
      "Documentation update required",
      "Performance optimization needed"
    ].sample
  end
end

def realistic_technical_paragraph
  paragraphs = [
    "After analyzing the logs, it appears the issue stems from improper error handling in the async operations. The system fails to catch rejected promises, leading to unhandled exceptions that crash the worker process.",
    
    "Initial benchmarks show a 300ms delay in response time during peak hours. Profiling indicates the bottleneck is in the ORM query layer, specifically the N+1 query problem when loading related entities.",
    
    "The current implementation uses a synchronous approach which blocks the event loop. We should refactor this to use async/await patterns or worker threads to improve throughput and responsiveness.",
    
    "Security audit revealed that user input is not properly sanitized before being passed to the database query. This creates a potential SQL injection vector that needs immediate remediation.",
    
    "The caching layer is returning stale data because TTL is set too high and cache invalidation logic is not triggered on updates. This causes users to see outdated information for up to 30 minutes.",
    
    "Memory profiling shows that large objects are not being garbage collected due to circular references. We need to implement proper cleanup in the destructor and use WeakMap for event listeners.",
    
    "The API response format is inconsistent across different endpoints. Some return arrays directly while others wrap them in a data object. We need to standardize the response structure.",
    
    "Load testing revealed that the system can only handle 50 concurrent requests before response time degrades significantly. We need to implement connection pooling and optimize database queries.",
    
    "The authentication token expires too quickly causing frequent re-login requests. We should implement refresh tokens to improve user experience while maintaining security.",
    
    "Cross-browser testing showed that the UI breaks in Safari due to unsupported CSS features. We need to add vendor prefixes and fallback styles for better compatibility."
  ]
  paragraphs.sample
end

# ===== Wiki content generators =====

def wiki_text_ml(project_name, page: "Home")
  case page
  when "Home"
    wiki_home_content(project_name)
  when "Troubleshooting"
    wiki_troubleshooting_content(project_name)
  when "Code-Review-Guidelines"
    wiki_code_review_content(project_name)
  when "Security-Best-Practices"
    wiki_security_content(project_name)
  when "Performance-Optimization"
    wiki_performance_content(project_name)
  when "Testing-Strategy"
    wiki_testing_content(project_name)
  else
    wiki_generic_content(project_name, page)
  end
end

def wiki_home_content(project_name)
  <<~WIKI
  # #{project_name} – Project Overview
  
  ## 🇬🇧 EN
  
  ### Project Goals
  This project aims to deliver a robust, scalable solution that meets business requirements while maintaining code quality and security standards.
  
  ### Key Features
  - RESTful API with comprehensive documentation
  - Real-time data synchronization
  - Role-based access control (RBAC)
  - Microservices architecture
  - Comprehensive test coverage (>80%)
  
  ### Technology Stack
  - **Backend**: Ruby on Rails 7.x, PostgreSQL
  - **Frontend**: React 18, TypeScript
  - **Infrastructure**: Docker, Kubernetes, AWS
  - **CI/CD**: GitHub Actions, ArgoCD
  
  ### Quick Links
  - [[Getting-Started|Getting Started Guide]]
  - [[API-Reference|API Documentation]]
  - [[Architecture|Architecture Overview]]
  - [[Deployment-Guide|Deployment Guide]]
  
  ---
  
  ## 🇻🇳 VI
  
  ### Mục tiêu Dự án
  Dự án này hướng tới việc cung cấp giải pháp mạnh mẽ, có khả năng mở rộng, đáp ứng yêu cầu kinh doanh đồng thời duy trì chất lượng code và tiêu chuẩn bảo mật.
  
  ### Tính năng Chính
  - API RESTful với tài liệu đầy đủ
  - Đồng bộ dữ liệu thời gian thực
  - Kiểm soát truy cập dựa trên vai trò (RBAC)
  - Kiến trúc microservices
  - Test coverage toàn diện (>80%)
  
  ### Công nghệ Sử dụng
  - **Backend**: Ruby on Rails 7.x, PostgreSQL
  - **Frontend**: React 18, TypeScript
  - **Hạ tầng**: Docker, Kubernetes, AWS
  - **CI/CD**: GitHub Actions, ArgoCD
  
  ### Liên kết Nhanh
  - [[Getting-Started|Hướng dẫn Bắt đầu]]
  - [[API-Reference|Tài liệu API]]
  - [[Architecture|Tổng quan Kiến trúc]]
  - [[Deployment-Guide|Hướng dẫn Triển khai]]
  
  ---
  
  ## 🇯🇵 日本語
  
  ### プロジェクト目標
  このプロジェクトは、コード品質とセキュリティ基準を維持しながら、ビジネス要件を満たす堅牢でスケーラブルなソリューションの提供を目指しています。
  
  ### 主な機能
  - 包括的なドキュメントを備えたRESTful API
  - リアルタイムデータ同期
  - ロールベースアクセス制御（RBAC）
  - マイクロサービスアーキテクチャ
  - 包括的なテストカバレッジ（>80%）
  
  ### 技術スタック
  - **バックエンド**: Ruby on Rails 7.x, PostgreSQL
  - **フロントエンド**: React 18, TypeScript
  - **インフラ**: Docker, Kubernetes, AWS
  - **CI/CD**: GitHub Actions, ArgoCD
  
  ### クイックリンク
  - [[Getting-Started|スタートガイド]]
  - [[API-Reference|APIドキュメント]]
  - [[Architecture|アーキテクチャ概要]]
  - [[Deployment-Guide|デプロイガイド]]
  WIKI
end

def wiki_troubleshooting_content(project_name)
  <<~WIKI
  # Troubleshooting Guide – #{project_name}
  
  ## 🇬🇧 Common Issues
  
  ### Database Connection Errors
  **Symptom**: `PG::ConnectionBad: could not connect to server`
  
  **Solution**:
  1. Check database service is running: `docker ps | grep postgres`
  2. Verify credentials in `config/database.yml`
  3. Ensure network connectivity: `ping db-host`
  4. Check connection pool settings
  
  ### Memory Leaks
  **Symptom**: Application memory grows continuously
  
  **Solution**:
  1. Profile with memory_profiler gem
  2. Check for circular references
  3. Review event listener cleanup
  4. Use WeakRef for caches
  
  ### Slow API Response
  **Symptom**: Response time > 2 seconds
  
  **Solution**:
  1. Enable query logging: `ActiveRecord::Base.logger.level = :debug`
  2. Check for N+1 queries with Bullet gem
  3. Add database indexes on foreign keys
  4. Implement pagination for large datasets
  
  ---
  
  ## 🇻🇳 Các Vấn đề Thường gặp
  
  ### Lỗi Kết nối Database
  **Triệu chứng**: `PG::ConnectionBad: could not connect to server`
  
  **Giải pháp**:
  1. Kiểm tra service database đang chạy: `docker ps | grep postgres`
  2. Xác minh thông tin đăng nhập trong `config/database.yml`
  3. Đảm bảo kết nối mạng: `ping db-host`
  4. Kiểm tra cấu hình connection pool
  
  ### Rò rỉ Bộ nhớ
  **Triệu chứng**: Bộ nhớ ứng dụng tăng liên tục
  
  **Giải pháp**:
  1. Profile với gem memory_profiler
  2. Kiểm tra circular references
  3. Xem xét việc cleanup event listeners
  4. Sử dụng WeakRef cho caches
  
  ---
  
  ## 🇯🇵 よくある問題
  
  ### データベース接続エラー
  **症状**: `PG::ConnectionBad: could not connect to server`
  
  **解決策**:
  1. データベースサービスが実行中か確認: `docker ps | grep postgres`
  2. `config/database.yml`の認証情報を検証
  3. ネットワーク接続を確認: `ping db-host`
  4. コネクションプール設定を確認
  WIKI
end

def wiki_code_review_content(project_name)
  <<~WIKI
  # Code Review Guidelines – #{project_name}
  
  ## 🇬🇧 Review Checklist
  
  ### Code Quality
  - [ ] Code follows style guide (Rubocop/ESLint passes)
  - [ ] No code duplication (DRY principle)
  - [ ] Functions are small and focused (single responsibility)
  - [ ] Variable names are descriptive and meaningful
  - [ ] No hardcoded values (use constants/config)
  
  ### Testing
  - [ ] Unit tests cover new functionality
  - [ ] Integration tests for API endpoints
  - [ ] Edge cases are tested
  - [ ] Test coverage is maintained (>80%)
  - [ ] All tests pass in CI pipeline
  
  ### Security
  - [ ] User input is validated and sanitized
  - [ ] SQL injection prevention (parameterized queries)
  - [ ] XSS prevention (proper escaping)
  - [ ] Authentication/authorization checks
  - [ ] Sensitive data is not logged
  
  ### Performance
  - [ ] No N+1 queries
  - [ ] Database queries are optimized
  - [ ] Appropriate indexes exist
  - [ ] Large datasets use pagination
  - [ ] Caching is implemented where appropriate
  
  ### Documentation
  - [ ] README is updated if needed
  - [ ] API documentation reflects changes
  - [ ] Complex logic has explanatory comments
  - [ ] CHANGELOG is updated
  
  ---
  
  ## 🇻🇳 Checklist Review Code
  
  ### Chất lượng Code
  - [ ] Code tuân theo style guide (Rubocop/ESLint pass)
  - [ ] Không duplicate code (nguyên tắc DRY)
  - [ ] Functions nhỏ và tập trung (single responsibility)
  - [ ] Tên biến mô tả rõ ràng và có ý nghĩa
  - [ ] Không hardcode giá trị (dùng constants/config)
  
  ### Testing
  - [ ] Unit tests cover chức năng mới
  - [ ] Integration tests cho API endpoints
  - [ ] Edge cases được test
  - [ ] Test coverage được duy trì (>80%)
  - [ ] Tất cả tests pass trong CI pipeline
  
  ---
  
  ## 🇯🇵 レビューチェックリスト
  
  ### コード品質
  - [ ] スタイルガイドに従っている（Rubocop/ESLintがパス）
  - [ ] コードの重複がない（DRY原則）
  - [ ] 関数は小さく集中している（単一責任）
  - [ ] 変数名は説明的で意味がある
  - [ ] ハードコードされた値がない（定数/設定を使用）
  WIKI
end

def wiki_security_content(project_name)
  <<~WIKI
  # Security Best Practices – #{project_name}
  
  ## 🇬🇧 Security Guidelines
  
  ### Authentication & Authorization
  - Use JWT tokens with short expiration (15 minutes)
  - Implement refresh token mechanism
  - Store passwords with bcrypt (cost factor >= 12)
  - Enforce strong password policy (min 12 chars, mixed case, numbers, symbols)
  - Implement rate limiting on auth endpoints
  
  ### Data Protection
  - Encrypt sensitive data at rest (AES-256)
  - Use TLS 1.3 for data in transit
  - Never log sensitive information (passwords, tokens, credit cards)
  - Implement proper session management
  - Use secure cookie flags (HttpOnly, Secure, SameSite)
  
  ### Input Validation
  - Validate all user input on server side
  - Use parameterized queries (prevent SQL injection)
  - Sanitize output (prevent XSS)
  - Implement CSRF protection
  - Validate file uploads (type, size, content)
  
  ### API Security
  - Implement API rate limiting
  - Use API keys for service-to-service communication
  - Validate JWT signatures
  - Implement proper CORS policies
  - Version your APIs
  
  ---
  
  ## 🇻🇳 Hướng dẫn Bảo mật
  
  ### Xác thực & Phân quyền
  - Sử dụng JWT tokens với thời gian hết hạn ngắn (15 phút)
  - Triển khai cơ chế refresh token
  - Lưu mật khẩu với bcrypt (cost factor >= 12)
  - Áp dụng chính sách mật khẩu mạnh (tối thiểu 12 ký tự, hoa/thường, số, ký tự đặc biệt)
  - Triển khai rate limiting trên auth endpoints
  
  ### Bảo vệ Dữ liệu
  - Mã hóa dữ liệu nhạy cảm khi lưu trữ (AES-256)
  - Sử dụng TLS 1.3 cho dữ liệu truyền tải
  - Không bao giờ log thông tin nhạy cảm (mật khẩu, tokens, thẻ tín dụng)
  - Triển khai quản lý session đúng cách
  - Sử dụng secure cookie flags (HttpOnly, Secure, SameSite)
  
  ---
  
  ## 🇯🇵 セキュリティガイドライン
  
  ### 認証と認可
  - 短い有効期限（15分）のJWTトークンを使用
  - リフレッシュトークンメカニズムを実装
  - bcryptでパスワードを保存（コストファクタ >= 12）
  - 強力なパスワードポリシーを適用（最小12文字、大文字小文字、数字、記号）
  - 認証エンドポイントにレート制限を実装
  WIKI
end

def wiki_performance_content(project_name)
  <<~WIKI
  # Performance Optimization Guide – #{project_name}
  
  ## 🇬🇧 Optimization Strategies
  
  ### Database Optimization
  - Add indexes on frequently queried columns
  - Use EXPLAIN ANALYZE to profile slow queries
  - Implement connection pooling (pool size: 5-10)
  - Use database-level caching (Redis)
  - Optimize JOIN operations
  - Partition large tables
  
  ### Application Performance
  - Enable fragment caching for views
  - Use background jobs for heavy operations (Sidekiq)
  - Implement pagination (25-50 items per page)
  - Lazy load associations
  - Use counter cache for associations
  - Enable HTTP caching headers
  
  ### Frontend Performance
  - Minimize bundle size (code splitting)
  - Lazy load components
  - Optimize images (WebP format, compression)
  - Use CDN for static assets
  - Implement virtual scrolling for long lists
  - Enable service workers for offline support
  
  ### Monitoring
  - Set up APM (New Relic, DataDog)
  - Monitor response times (target: <200ms)
  - Track error rates
  - Set up alerts for anomalies
  - Regular performance audits
  
  ---
  
  ## 🇻🇳 Chiến lược Tối ưu
  
  ### Tối ưu Database
  - Thêm indexes trên các cột thường query
  - Dùng EXPLAIN ANALYZE để profile các query chậm
  - Triển khai connection pooling (pool size: 5-10)
  - Sử dụng database-level caching (Redis)
  - Tối ưu các thao tác JOIN
  - Phân vùng các bảng lớn
  
  ### Hiệu suất Ứng dụng
  - Bật fragment caching cho views
  - Sử dụng background jobs cho operations nặng (Sidekiq)
  - Triển khai pagination (25-50 items mỗi trang)
  - Lazy load associations
  - Dùng counter cache cho associations
  - Bật HTTP caching headers
  
  ---
  
  ## 🇯🇵 最適化戦略
  
  ### データベース最適化
  - 頻繁にクエリされる列にインデックスを追加
  - EXPLAIN ANALYZEで遅いクエリをプロファイル
  - コネクションプーリングを実装（プールサイズ: 5-10）
  - データベースレベルのキャッシング（Redis）を使用
  - JOIN操作を最適化
  - 大きなテーブルをパーティション化
  WIKI
end

def wiki_testing_content(project_name)
  <<~WIKI
  # Testing Strategy – #{project_name}
  
  ## 🇬🇧 Testing Approach
  
  ### Test Pyramid
  ```
         /\\
        /E2E\\         (10%)
       /------\\
      /  INT   \\      (20%)
     /----------\\
    /   UNIT     \\    (70%)
   /--------------\\
  ```
  
  ### Unit Tests
  - Test individual methods and functions
  - Mock external dependencies
  - Fast execution (<1ms per test)
  - High coverage target (>80%)
  - Run on every commit
  
  **Example**:
  ```ruby
  describe User do
    it 'validates email format' do
      user = User.new(email: 'invalid')
      expect(user).not_to be_valid
      expect(user.errors[:email]).to include('is invalid')
    end
  end
  ```
  
  ### Integration Tests
  - Test API endpoints
  - Test database interactions
  - Test service integrations
  - Moderate execution time
  
  **Example**:
  ```ruby
  describe 'POST /api/users' do
    it 'creates a new user' do
      post '/api/users', params: { email: 'test@example.com' }
      expect(response).to have_http_status(:created)
      expect(User.count).to eq(1)
    end
  end
  ```
  
  ### E2E Tests
  - Test critical user flows
  - Run in staging environment
  - Run before production deployment
  - Slower execution acceptable
  
  ---
  
  ## 🇻🇳 Chiến lược Testing
  
  ### Tháp Test
  - **Unit Tests**: 70% - Test các method và function riêng lẻ
  - **Integration Tests**: 20% - Test API endpoints và tích hợp
  - **E2E Tests**: 10% - Test các luồng người dùng quan trọng
  
  ### Unit Tests
  - Test từng method và function
  - Mock các dependency bên ngoài
  - Thực thi nhanh (<1ms mỗi test)
  - Mục tiêu coverage cao (>80%)
  - Chạy mỗi commit
  
  ---
  
  ## 🇯🇵 テスト戦略
  
  ### テストピラミッド
  - **単体テスト**: 70% - 個々のメソッドと関数をテスト
  - **統合テスト**: 20% - APIエンドポイントと統合をテスト
  - **E2Eテスト**: 10% - 重要なユーザーフローをテスト
  
  ### 単体テスト
  - 個々のメソッドと関数をテスト
  - 外部依存関係をモック
  - 高速実行（テストあたり<1ms）
  - 高いカバレッジ目標（>80%）
  - すべてのコミットで実行
  WIKI
end

def wiki_generic_content(project_name, page_title)
  <<~WIKI
  # #{page_title} – #{project_name}
  
  ## 🇬🇧 EN
  This page documents important information about #{page_title.gsub('-', ' ')} for the #{project_name} project.
  
  ### Overview
  Detailed documentation and guidelines will be added here as the project evolves.
  
  ### Resources
  - [[Home|Project wiki home]]
  - Related documentation
  - External references
  
  ---
  
  ## 🇻🇳 VI
  Trang này ghi lại thông tin quan trọng về #{page_title.gsub('-', ' ')} cho dự án #{project_name}.
  
  ### Tổng quan
  Tài liệu chi tiết và hướng dẫn sẽ được bổ sung khi dự án phát triển.
  
  ### Tài nguyên
  - [[Home|Trang chủ wiki dự án]]
  - Tài liệu liên quan
  - Tham khảo bên ngoài
  
  ---
  
  ## 🇯🇵 日本語
  このページは#{project_name}プロジェクトの#{page_title.gsub('-', ' ')}に関する重要な情報を文書化しています。
  
  ### 概要
  詳細なドキュメントとガイドラインは、プロジェクトの進化に伴って追加されます。
  
  ### リソース
  - [[Home|プロジェクトwikiホーム]]
  - 関連ドキュメント
  - 外部参照
  WIKI
end

# ===== Utility functions =====

def rand_date_within(days: 30)
  (Date.today - rand(0..days)).to_s
end

def pick_weighted(hash)
  total = hash.values.map(&:to_f).sum
  r = rand * total
  acc = 0.0
  hash.each do |k, w|
    acc += w.to_f
    return k if r <= acc
  end
  hash.keys.last
end

ok "I18N helpers loaded (EN/VI/JA support enabled with enhanced templates)"