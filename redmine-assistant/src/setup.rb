# frozen_string_literal: true

puts "🚀 Starting Redmine initialization script..."

# --- Enable REST API ---
if Setting.rest_api_enabled != true
  Setting.rest_api_enabled = true
  puts "✅ Enabled REST API in Redmine settings."
else
  puts "🔧 REST API already enabled."
end

# --- Update admin password ---
admin = User.find_by(login: 'admin')
if admin
  admin.password = 'admin123'
  admin.password_confirmation = 'admin123'
  admin.must_change_passwd = false
  admin.save!(validate: false)
  puts "✅ Updated admin password."
else
  puts "⚠️ Admin user not found — skipped password update."
end

# --- Ensure admin API key exists ---
admin_token = nil
if admin
  token = Token.where(user_id: admin.id, action: 'api').first
  unless token
    token = Token.create!(user: admin, action: 'api')
    puts "🔑 Created new API key for admin."
  else
    puts "🔑 Admin already has API key."
  end
  admin_token = token.value
end

# --- Create demo users (demo1 .. demo5) ---
(1..5).each do |i|
  login = "demo#{i}"
  user = User.find_by(login: login)
  if user
    puts "👤 User '#{login}' already exists — skipped."
  else
    user = User.new(
      firstname: "Demo#{i}",
      lastname: "User",
      mail: "demo#{i}@example.com",
      login: login,
      language: 'en'
    )
    user.password = 'demo123'
    user.password_confirmation = 'demo123'
    user.save!(validate: false)
    puts "✅ Created user #{login}"
  end
end


# --- Create roles ---
['Developer', 'Tester'].each do |role_name|
  role = Role.find_by(name: role_name)
  if role
    puts "🛠️ Role '#{role_name}' already exists — skipped."
  else
    role = Role.new(name: role_name, assignable: true)
    # Optional: cấp quyền cơ bản cho role
    role.permissions = [
      :view_issues,
      :add_issues,
      :edit_issues,
      :add_issue_notes,
      :view_files,
      :view_documents
    ]
    role.save!
    puts "✅ Created role '#{role_name}' with default permissions."
  end
end


# --- Create issue statuses ---
['New', 'In Progress', 'Resolved', 'Closed'].each do |status|
  IssueStatus.find_or_create_by!(name: status)
  puts "✅ Ensured issue status '#{status}' exists."
end

# --- Create trackers (Bug, Developing) ---
['Bug', 'Developing'].each do |tracker_name|
  if Tracker.exists?(name: tracker_name)
    puts "🧩 Tracker '#{tracker_name}' already exists — skipped."
  else
    Tracker.create!(
      name: tracker_name,
      default_status: IssueStatus.find_by(name: 'New')
    )
    puts "✅ Created tracker '#{tracker_name}'."
  end
end


# --- Create issue priorities ---
priorities = [
  { name: 'Low', position: 1 },
  { name: 'Normal', position: 2, is_default: true },
  { name: 'High', position: 3 },
  { name: 'Urgent', position: 4 },
  { name: 'Immediate', position: 5 }
]

priorities.each do |p|
  pr = IssuePriority.find_by(name: p[:name])
  if pr
    puts "🎚️ Issue Priority '#{p[:name]}' already exists — skipped."
  else
    IssuePriority.create!(p)
    puts "✅ Created Issue Priority '#{p[:name]}'."
  end
end

puts "🎉 Redmine setup completed successfully!"

# --- Print admin API key at the end ---
if admin_token
  puts "\n=========================================="
  puts "🔐 ADMIN API ACCESS KEY:"
  puts "👉 #{admin_token}"
  puts "==========================================\n\n"
else
  puts "⚠️ No admin token found!"
end
