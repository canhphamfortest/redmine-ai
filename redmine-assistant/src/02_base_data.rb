# /usr/src/redmine/init/02_base_data.rb
# Initialize base Redmine data: trackers, statuses, priorities, roles

# -------------------------
# Lookups
# -------------------------

def find_user_by_login(login)
  User.find_by(login: login)
end

def find_role_by_name(name)
  Role.find_by(name: name)
end

def ensure_tracker(name)
  tracker = Tracker.find_by(name: name)
  if tracker
    ok "Tracker '#{name}' already exists"
  else
    tracker = Tracker.create!(
      name: name,
      default_status: IssueStatus.find_by(name: 'New') || IssueStatus.first
    )
    ok "Created tracker '#{name}'"
  end
  tracker
end

def ensure_status(name, attrs = {})
  status = IssueStatus.find_by(name: name)
  if status
    status.update!(attrs) unless attrs.empty?
  else
    status = IssueStatus.create!(attrs.merge(name: name))
    ok "Created status '#{name}'"
  end
  status
end

def priority_by_name(name)
  if defined?(IssuePriority)
    IssuePriority.find_by(name: name)
  else
    Enumeration.where(type: "IssuePriority").find_by(name: name)
  end
end

def ensure_priority(name, position, is_default: false)
  priority = priority_by_name(name)
  if priority
    ok "Priority '#{name}' already exists"
  else
    attrs = { name: name, position: position, is_default: is_default }
    if defined?(IssuePriority)
      IssuePriority.create!(attrs)
    else
      Enumeration.create!(attrs.merge(type: "IssuePriority"))
    end
    ok "Created priority '#{name}'"
  end
  priority_by_name(name)
end

# -------------------------
# Execute initialization
# -------------------------

say "Initializing base data..."

# Trackers
TRACKERS = %w[Bug Developing Feature Support Task]
TRACKERS.each { |name| ensure_tracker(name) }

# Statuses
STATUS_SEQUENCE = [
  { name: "New", is_closed: false },
  { name: "In Progress", is_closed: false },
  { name: "Resolved", is_closed: false },
  { name: "Feedback", is_closed: false },
  { name: "Closed", is_closed: true },
  { name: "Rejected", is_closed: true }
]
STATUS_SEQUENCE.each { |s| ensure_status(s[:name], s) }

# Priorities
PRIORITIES = [
  { name: "Low", position: 1 },
  { name: "Normal", position: 2, is_default: true },
  { name: "High", position: 3 },
  { name: "Urgent", position: 4 },
  { name: "Immediate", position: 5 }
]
PRIORITIES.each { |p| ensure_priority(p[:name], p[:position], is_default: p[:is_default] || false) }

# Verify roles
role_dev = find_role_by_name("Developer")
role_tester = find_role_by_name("Tester")
warnx("Role 'Developer' not found - please run setup.rb first") unless role_dev
warnx("Role 'Tester' not found - please run setup.rb first") unless role_tester

ok "Base data initialization completed"