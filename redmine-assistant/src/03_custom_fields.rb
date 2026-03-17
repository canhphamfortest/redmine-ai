# /usr/src/redmine/init/03_custom_fields.rb
# Setup custom fields for Issues and Time Entries

def ensure_issue_cf_text(name, default: nil)
  cf = IssueCustomField.find_by(name: name)
  if cf
    ok "Issue CF (text) '#{name}' already exists"
    return cf
  end
  
  cf = IssueCustomField.new(
    name: name,
    field_format: 'string',
    is_required: false,
    is_for_all: true,
    searchable: true,
    visible: true
  )
  cf.default_value = default if default
  cf.trackers = Tracker.all
  cf.save!
  ok "Created Issue CF (text) '#{name}'"
  cf
end

def ensure_issue_cf_list(name, possible_values, default: nil)
  cf = IssueCustomField.find_by(name: name)
  if cf
    ok "Issue CF (list) '#{name}' already exists"
    return cf
  end
  
  cf = IssueCustomField.new(
    name: name,
    field_format: 'list',
    possible_values: possible_values,
    is_required: false,
    is_for_all: true,
    editable: true,
    visible: true
  )
  cf.default_value = default if default
  cf.trackers = Tracker.all
  cf.save!
  ok "Created Issue CF (list) '#{name}'"
  cf
end

def ensure_timeentry_cf_list(name, possible_values, default: nil)
  cf = TimeEntryCustomField.find_by(name: name)
  if cf
    ok "TimeEntry CF (list) '#{name}' already exists"
    return cf
  end
  
  cf = TimeEntryCustomField.new(
    name: name,
    field_format: 'list',
    possible_values: possible_values,
    is_required: false,
    is_for_all: true,
    editable: true,
    visible: true
  )
  cf.default_value = default if default
  cf.save!
  ok "Created TimeEntry CF (list) '#{name}'"
  cf
end

# -------------------------
# Execute custom fields setup
# -------------------------

say "Setting up custom fields..."

# Issue custom fields
ISSUE_CFS = [
  { name: "Severity", type: :list, possible_values: %w[Minor Major Critical], default_value: "Minor" },
  { name: "Component", type: :list, possible_values: %w[UI API DB Build Deploy Mobile Web], default_value: "UI" },
  { name: "Env", type: :string, default_value: "prod" },
  { name: "Browser", type: :list, possible_values: %w[Chrome Firefox Safari Edge Opera], default_value: "Chrome" },
  { name: "OS", type: :list, possible_values: %w[Windows macOS Linux Android iOS], default_value: "Windows" }
]

$issue_cf_refs = {}
ISSUE_CFS.each do |cf|
  if cf[:type] == :list
    $issue_cf_refs[cf[:name]] = ensure_issue_cf_list(cf[:name], cf[:possible_values], default: cf[:default_value])
  else
    $issue_cf_refs[cf[:name]] = ensure_issue_cf_text(cf[:name], default: cf[:default_value])
  end
end

# Time entry custom fields
TIMEENTRY_CFS = [
  { name: "Billable", type: :list, possible_values: %w[Yes No], default_value: "Yes" },
  { name: "Work Type", type: :list, possible_values: %w[Development Testing Documentation Meeting Research], default_value: "Development" }
]

$billable_cf = nil
TIMEENTRY_CFS.each do |cf|
  custom_field = ensure_timeentry_cf_list(cf[:name], cf[:possible_values], default: cf[:default_value])
  $billable_cf = custom_field if cf[:name] == "Billable"
end

ok "Custom fields setup completed"