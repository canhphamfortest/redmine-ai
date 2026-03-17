# /usr/src/redmine/init/04_projects.rb
# Create projects, memberships, categories, and versions

def ensure_project(h)
  prj = Project.find_by(identifier: h[:identifier])
  if prj
    prj.update!(name: h[:name], description: h[:description], is_public: h[:is_public])
    ok "Updated project '#{h[:identifier]}'"
  else
    prj = Project.create!(
      name: h[:name],
      identifier: h[:identifier],
      description: h[:description],
      is_public: h[:is_public]
    )
    ok "Created project '#{h[:identifier]}'"
  end
  
  if h[:modules]
    prj.enabled_module_names = h[:modules]
    prj.save!
  end
  prj
end

def ensure_membership(project, user, role)
  return unless user && role
  m = Member.find_by(project: project, user: user)
  if m
    unless m.roles.exists?(role.id)
      m.roles << role
      m.save!
      ok "Added role '#{role.name}' to #{user.login} in #{project.identifier}"
    end
  else
    Member.create!(project: project, user: user, roles: [role])
    ok "Created membership: #{user.login} as #{role.name} in #{project.identifier}"
  end
end

def ensure_category(project, name)
  cat = project.issue_categories.find_by(name: name)
  if cat
    return cat
  else
    cat = project.issue_categories.create!(name: name)
    ok "Created category '#{name}' in #{project.identifier}"
    cat
  end
end

def ensure_version(project, h)
  v = project.versions.find_by(name: h[:name])
  if v
    v.update!(description: h[:description], status: h[:status])
  else
    v = project.versions.create!(
      name: h[:name],
      description: h[:description],
      status: h[:status]
    )
    ok "Created version '#{h[:name]}' in #{project.identifier}"
  end
  v
end

# -------------------------
# Project configurations
# -------------------------

PROJECTS = [
  {
    name: "Demo Project",
    identifier: "demo-project",
    description: "Dự án demo đa ngôn ngữ (EN/VI/JA) với đầy đủ tính năng Redmine",
    is_public: true,
    modules: %w[issue_tracking time_tracking wiki files gantt calendar],
    categories: %w[Backend Frontend DevOps QA Docs Security Mobile],
    versions: [
      { name: "v1.0.0", status: "open", description: "First major release" },
      { name: "v1.1.0", status: "open", description: "Minor improvements & bug fixes" },
      { name: "v2.0.0", status: "open", description: "Major release with new features" },
      { name: "v0.9.0", status: "closed", description: "Beta version" }
    ],
    assignees: %w[demo1 demo2 demo3 demo4 demo5],
    watchers: %w[demo1 demo2 demo3],
    issues_target: 500,
    attachments_per_issue: 0..3,
    time_entries_per_issue: 0..3
  },
  {
    name: "Internal Tools",
    identifier: "internal-tools",
    description: "Công cụ nội bộ & CI/CD pipeline | 内部ツール",
    is_public: false,
    modules: %w[issue_tracking time_tracking wiki files],
    categories: %w[CLI Pipeline Infra SRE UX Monitoring Automation],
    versions: [
      { name: "sprint-2025-11", status: "open", description: "November sprint" },
      { name: "sprint-2025-12", status: "open", description: "December sprint" },
      { name: "sprint-2025-10", status: "closed", description: "October sprint (completed)" }
    ],
    assignees: %w[demo1 demo2 demo5],
    watchers: %w[demo3 demo4],
    issues_target: 300,
    attachments_per_issue: 0..2,
    time_entries_per_issue: 0..2
  },
  {
    name: "Mobile App Development",
    identifier: "mobile-app",
    description: "Cross-platform mobile application | アプリ開発",
    is_public: true,
    modules: %w[issue_tracking time_tracking wiki files gantt],
    categories: %w[iOS Android ReactNative Flutter UI/UX Backend API],
    versions: [
      { name: "v1.0-beta", status: "open", description: "Beta testing phase" },
      { name: "v1.0-rc1", status: "open", description: "Release candidate 1" }
    ],
    assignees: %w[demo2 demo3 demo4],
    watchers: %w[demo1 demo5],
    issues_target: 200,
    attachments_per_issue: 0..2,
    time_entries_per_issue: 0..3
  }
]

# -------------------------
# Execute project setup
# -------------------------

say "Setting up projects..."

$projects_data = []

PROJECTS.each do |cfg|
  say "Processing project: #{cfg[:identifier]}"
  project = ensure_project(cfg)
  
  # Categories
  (cfg[:categories] || []).each { |cat| ensure_category(project, cat) }
  
  # Versions
  (cfg[:versions] || []).each { |v| ensure_version(project, v) }
  
  # Resolve users
  assignees = (cfg[:assignees] || []).map { |l| find_user_by_login(l) }.compact
  watchers = (cfg[:watchers] || []).map { |l| find_user_by_login(l) }.compact
  
  # Memberships
  role_dev = find_role_by_name("Developer")
  role_tester = find_role_by_name("Tester")
  default_role = role_dev || role_tester
  
  if default_role
    assignees.each { |u| ensure_membership(project, u, default_role) }
  else
    warnx "No roles found - skip memberships for #{cfg[:identifier]}"
  end
  
  # Store for later use
  $projects_data << {
    project: project,
    config: cfg,
    assignees: assignees,
    watchers: watchers
  }
  
  ok "Project '#{cfg[:identifier]}' setup completed"
end

ok "All projects setup completed"