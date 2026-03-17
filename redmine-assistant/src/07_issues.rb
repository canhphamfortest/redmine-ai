# /usr/src/redmine/init/07_issues.rb
# Generate multilingual issues with distribution weights

# Distribution weights
TRACKER_WEIGHTS = {
  "Bug" => 0.40,
  "Developing" => 0.35,
  "Feature" => 0.15,
  "Task" => 0.10
}

PRIORITY_WEIGHTS = {
  "Low" => 0.10,
  "Normal" => 0.50,
  "High" => 0.25,
  "Urgent" => 0.10,
  "Immediate" => 0.05
}

STATUS_WEIGHTS = {
  "New" => 0.30,
  "In Progress" => 0.40,
  "Resolved" => 0.15,
  "Feedback" => 0.05,
  "Closed" => 0.10
}

def seed_author!
  SEED_AUTHOR || User.find_by(login: 'admin') || User.first || raise("No user found for seeding")
end

def with_seed_user
  prev = User.current
  User.current = seed_author!
  yield
ensure
  User.current = prev
end

# --- Đảm bảo tracker được bật cho project ---
def ensure_project_trackers!(project, tracker_names)
  needed = Tracker.where(name: tracker_names).to_a
  return if needed.empty?

  # Bật các tracker cần thiết cho project (union)
  new_list = (project.trackers.to_a + needed).uniq
  if new_list.size != project.trackers.size
    project.trackers = new_list
    project.save!
  end
end

# --- Lấy Activity cho TimeEntry (và tạo nếu thiếu) ---
def ensure_time_entry_activity!
  if defined?(TimeEntryActivity)
    TimeEntryActivity.where(active: true).order(:id).first ||
      TimeEntryActivity.create!(name: 'Development', active: true, position: 1)
  else
    # Redmine < 5 hoặc dạng cũ
    Enumeration.where(type: "TimeEntryActivity", active: true).order(:id).first ||
      Enumeration.create!(type: "TimeEntryActivity", name: 'Development', active: true, position: 1)
  end
end

# --- Đảm bảo user là member của project (để log time/assign issue) ---
def ensure_member!(project, user, role_name: 'Developer')
  return if !user || project.users.exists?(user.id)

  role = Role.find_by(name: role_name) || Role.givable.first || Role.first
  return unless role
  
  begin
    Member.create!(project: project, user: user, roles: [role])
    ok "Added #{user.login} as member of #{project.identifier}"
  rescue => e
    warnx "Could not add #{user.login} to #{project.identifier}: #{e.message}"
  end
end

# --- Ngày an toàn: due >= start ---
def safe_dates(start_within_days: 60, max_duration_days: 30)
  start_date = Date.today - rand(0..start_within_days)
  due_date   = start_date + rand(1..[max_duration_days, 1].max)
  [start_date, due_date]
end

# --- Lấy priority theo tên ---
def priority_by_name(name)
  if defined?(IssuePriority)
    IssuePriority.find_by(name: name)
  else
    Enumeration.where(type: "IssuePriority").find_by(name: name)
  end
end

# --- Tạo journals/notes cho issue (FIXED VERSION) ---
def create_journals_for_issue(issue, assignees, journal_count_range: 1..5)
  puts "[JOURNAL] Starting for issue ##{issue.id}"
  
  # # Check 1: Hàm generate_journal_note có tồn tại không?
  # unless respond_to?(:generate_journal_note)
  #   puts "[JOURNAL] ERROR: generate_journal_note method not found"
  #   return
  # end
  
  count = rand(journal_count_range)
  puts "[JOURNAL] Will create #{count} journals"
  
  if count <= 0
    puts "[JOURNAL] Count is 0, skipping"
    return
  end
  
  # Check 2: Có users để tạo journal không?
  possible_users = [issue.author, issue.assigned_to].compact
  possible_users += assignees.sample(3) if assignees && assignees.any?
  possible_users = possible_users.uniq.compact
  
  if possible_users.empty?
    puts "[JOURNAL] ERROR: No users available for journal creation"
    return
  end
  
  puts "[JOURNAL] Found #{possible_users.length} possible users: #{possible_users.map(&:login).join(', ')}"
  
  # Check 3: User.current có giá trị không?
  original_user = User.current
  puts "[JOURNAL] Current user: #{User.current&.login || 'nil'}"
  
  # Tạo journals theo thứ tự thời gian
  created_count = 0
  count.times do |i|
    user = possible_users.sample
    
    # FIX 1: Set User.current để journal có author
    User.current = user
    
    # FIX 2: Tính toán thời gian chính xác hơn
    # Lấy khoảng thời gian từ issue created đến hiện tại
    days_since_creation = (Date.today - issue.created_on.to_date).to_i
    
    # Nếu issue mới tạo hôm nay, dùng giờ thay vì ngày
    if days_since_creation <= 0
      # Issue tạo hôm nay, thêm 1-8 giờ sau khi tạo issue
      time_offset = rand(1..8) * 3600  # 1-8 hours in seconds
      created_at = issue.created_on + time_offset
    else
      # Issue cũ hơn, random trong khoảng thời gian
      created_days_ago = rand(0..days_since_creation)
      created_at = issue.created_on + (created_days_ago * 24 * 60 * 60) + rand(1..86400)
    end
    
    # Chọn loại note phù hợp với tiến độ
    note_type = if i == 0
                  :investigation
                elsif i == count - 1 && issue.status.is_closed
                  :completed
                elsif issue.status.is_closed
                  :solution
                else
                  [:progress, :blocker, :solution, :review, :meeting, :testing].sample
                end
    
    puts "[JOURNAL] Creating journal #{i+1}/#{count} - type: #{note_type}, user: #{user.login}"
    
    begin
      # FIX 3: Tạo journal với đầy đủ thông tin
      journal = Journal.new(
        journalized: issue,
        user: user,
        notes: generate_journal_note(note_type),
        created_on: created_at
      )
      
      # FIX 4: Save và validate
      if journal.save
        created_count += 1
        puts "[JOURNAL] ✓ Journal ##{journal.id} created successfully"
      else
        puts "[JOURNAL] ✗ Journal save failed: #{journal.errors.full_messages.join(', ')}"
      end
      
    rescue => e
      puts "[JOURNAL] ✗ Exception: #{e.message}"
      puts e.backtrace.first(3).join("\n")
    end
  end
  
  # Restore original user
  User.current = original_user
  
  puts "[JOURNAL] Completed: #{created_count}/#{count} journals created for issue ##{issue.id}"
  puts "[JOURNAL] Issue now has #{issue.journals.count} total journals"
  
  created_count
end

# --- ALTERNATIVE: Simplified version nếu trên vẫn không work ---
def create_journals_for_issue_simple(issue, assignees, count: 3)
  puts "[JOURNAL-SIMPLE] Creating #{count} journals for issue ##{issue.id}"
  
  # Ensure we have users
  users = [issue.author, issue.assigned_to].compact
  users += assignees.sample(2) if assignees
  users = users.uniq.compact
  
  return 0 if users.empty?
  
  original_user = User.current
  created = 0
  
  count.times do |i|
    user = users.sample
    User.current = user
    
    # Simple time calculation
    hours_ago = rand(1..48)
    created_at = Time.now - hours_ago.hours
    
    # Simple note types
    note_types = [:investigation, :progress, :review, :solution]
    note_type = note_types[i % note_types.length]
    
    begin
      journal = issue.journals.create!(
        user: user,
        notes: generate_journal_note(note_type),
        created_on: created_at
      )
      created += 1
      puts "[JOURNAL-SIMPLE] ✓ Created journal ##{journal.id}"
    rescue => e
      puts "[JOURNAL-SIMPLE] ✗ Error: #{e.message}"
    end
  end
  
  User.current = original_user
  puts "[JOURNAL-SIMPLE] Done: #{created}/#{count} created"
  created
end

# --- Tạo issues cho project ---
def create_issues_for_project(project, config, assignees, watchers)
  say "Creating issues for #{project.identifier}..."

  author = seed_author!

  # Bật trackers cần thiết cho project trước khi tạo issue
  ensure_project_trackers!(project, TRACKER_WEIGHTS.keys)

  trackers   = project.trackers.where(name: TRACKER_WEIGHTS.keys).to_a
  statuses   = IssueStatus.where(name: STATUS_WEIGHTS.keys).to_a
  priorities = PRIORITY_WEIGHTS.keys.map { |n| priority_by_name(n) }.compact
  categories = project.issue_categories.to_a
  versions   = project.versions.where(status: 'open').to_a  # Chỉ lấy version đang mở

  # Bảo đảm author là member
  ensure_member!(project, author)
  
  # Bảo đảm tất cả assignees là members
  assignees.each { |u| ensure_member!(project, u) } if assignees

  existing_cnt = project.issues.count
  target_cnt   = config[:issues_target].to_i
  to_create    = [target_cnt - existing_cnt, 0].max

  if to_create == 0
    ok "Project #{project.identifier} already has #{existing_cnt} issues (target: #{target_cnt})"
    return []
  end

  say "Creating #{to_create} issues (existing: #{existing_cnt}, target: #{target_cnt})"

  created_issues = []
  batch_size = 50

  (to_create / batch_size.to_f).ceil.times do |batch_idx|
    current_batch = [batch_size, to_create - (batch_idx * batch_size)].min
    
    ActiveRecord::Base.transaction do
      current_batch.times do
        # Pick tracker/status/priority
        tracker_name = pick_weighted(TRACKER_WEIGHTS)
        tracker = trackers.find { |t| t.name == tracker_name } || trackers.first
        
        unless tracker
          warnx "Skip issue: no tracker available for #{project.identifier}"
          next
        end

        status_name = pick_weighted(STATUS_WEIGHTS)
        status = statuses.find { |s| s.name == status_name } || statuses.first

        prio_name = pick_weighted(PRIORITY_WEIGHTS)
        prio = priorities.find { |p| p.name == prio_name }
        prio ||= (defined?(IssuePriority) ? IssuePriority.default : nil)
        prio ||= (defined?(IssuePriority) ? IssuePriority.first : Enumeration.where(type: "IssuePriority").first)

        assign = assignees&.sample

        cat = categories.sample
        
        # Chỉ gán version nếu có versions hợp lệ, và chỉ 50% issues có version
        ver = (versions.any? && rand < 0.5) ? versions.sample : nil

        # FIX: Dùng get_issue_content để đảm bảo subject và description khớp
        subj_prefix = case tracker_name
                      when "Bug"      then "[BUG]"
                      when "Feature"  then "[FEATURE]"
                      when "Task"     then "[TASK]"
                      else "[DEV]"
                      end
        
        issue_content = get_issue_content(tracker_name, subj_prefix)
        subject = issue_content[:subject]
        description = issue_content[:description]

        start_date, due_date = safe_dates(start_within_days: 60, max_duration_days: 30)

        issue = Issue.new(
          project: project,
          tracker: tracker,
          status: status,
          priority: prio,
          subject: subject,
          description: description,
          assigned_to: assign,
          category: cat,
          fixed_version: ver,
          start_date: start_date,
          due_date: due_date,
          author: author
        )

        # Custom fields
        cf_values = {}
        ($issue_cf_refs || {}).each do |name, cf|
          value = if cf.field_format == 'list'
                    (cf.possible_values.presence || [cf.default_value]).sample
                  else
                    %w[dev stage prod qa].sample
                  end
          cf_values[cf.id] = value
        end
        issue.custom_field_values = cf_values unless cf_values.empty?

        begin
          issue.save!
        rescue ActiveRecord::RecordInvalid => e
          warnx "Issue creation failed: #{e.message}"
          next
        end

        # Watchers (tối đa 2, không trùng)
        if watchers && !watchers.empty?
          watchers.sample([watchers.length, 2].min).uniq.each do |u|
            begin
              Watcher.create!(watchable: issue, user: u) unless issue.watcher_users.exists?(u.id)
            rescue => _
              # Ignore watcher errors
            end
          end
        end

        # Đính kèm file (50% issues có attachments)
        if config[:attachments_per_issue] && rand < 0.5
          attach_random_files(issue, assign || author, config[:attachments_per_issue])
        end

        # Journals/Notes (60% issues có journals, 1-5 notes mỗi issue)
        create_journals_for_issue(issue, assignees, journal_count_range: 1..5)

        # Time entries (30% issues có time entries)
        if config[:time_entries_per_issue] && rand < 0.3
          create_random_time_entries(
            issue,
            project,
            assignees,
            config[:time_entries_per_issue],
            billable_cf: $billable_cf
          )
        end

        created_issues << issue
      end
    end

    ok "Batch #{batch_idx + 1} completed (#{current_batch} issues)"
  end

  ok "Created #{created_issues.length} issues for #{project.identifier} (total: #{project.issues.count})"
  created_issues
end

# --- Tạo time entries ngẫu nhiên cho issue ---
def create_random_time_entries(issue, project, assignees, count_range, billable_cf: nil)
  count = rand(count_range)
  return if count <= 0

  activity = ensure_time_entry_activity!
  return unless activity

  count.times do
    # Chọn user có thật, ưu tiên assignee hoặc author
    user = issue.assigned_to || issue.author || assignees&.sample || seed_author!
    
    # Đảm bảo user là member của project
    ensure_member!(project, user)

    te = TimeEntry.new(
      issue: issue,
      project: project,
      user: user,
      activity: activity,
      spent_on: Date.today - rand(0..30),
      hours: [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0].sample,
      comments: ["Development", "Testing", "Code review", "Bug fixing", "Documentation",
                 "Meeting", "Research", "Refactoring"].sample
    )

    if billable_cf
      te.custom_field_values = { billable_cf.id => %w[Yes No].sample }
    end

    begin
      te.save!
    rescue => e
      warnx "Time entry error for issue ##{issue.id}: #{e.message}"
    end
  end
end


# -------------------------
# Execute issues creation
# -------------------------

def generate_all_issues
  say "Generating issues for all projects..."
  
  with_seed_user do
    $all_created_issues = []
    
    ($projects_data || []).each do |data|
      project = data[:project]
      config = data[:config]
      assignees = data[:assignees]
      watchers = data[:watchers]
      
      created = create_issues_for_project(project, config, assignees, watchers)
      $all_created_issues.concat(created)
    end
  end
  
  ok "Total issues created: #{$all_created_issues.length}"
end

ok "Issues generator loaded"