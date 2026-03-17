#!/usr/bin/env ruby
# /usr/src/redmine/init/init.rb
# Main Redmine seeder - Orchestrates all initialization modules
#
# Run:
#   docker compose exec redmine bundle exec rails runner /usr/src/redmine/init/init.rb
#
# This script loads all initialization modules in order:
# 00_bootstrap.rb      - Environment setup & utilities
# 01_i18n_helpers.rb   - Multilingual content generators (EN/VI/JA)
# 02_base_data.rb      - Base data (trackers, statuses, priorities)
# 03_custom_fields.rb  - Custom fields for issues and time entries
# 04_projects.rb       - Projects, categories, versions, memberships
# 05_attachments.rb    - File attachments helper
# 06_wiki.rb           - Wiki pages setup
# 07_issues.rb         - Issues generation with multilingual content
# 08_relations.rb      - Issue relations (blocks, relates, etc.)

puts "\n" + "="*60
puts "🚀 Redmine Extended Seeder - Multilingual (EN/VI/JA)"
puts "="*60 + "\n"

start_time = Time.now

# Determine the init directory
INIT_DIR = File.dirname(__FILE__)

# Load all modules in order
modules = [
  "00_bootstrap.rb",
  "01_i18n_helpers.rb",
  "02_base_data.rb",
  "03_custom_fields.rb",
  "04_projects.rb",
  "05_attachments.rb",
  "06_wiki.rb",
  "07_issues.rb",
  "08_relations.rb"
]

puts "📦 Loading modules...\n"

modules.each do |module_file|
  module_path = File.join(INIT_DIR, module_file)
  
  if File.exist?(module_path)
    puts "   Loading #{module_file}..."
    # Use 'load' instead of 'require' to ensure files are executed in order
    # and functions are available globally
    load module_path
  else
    puts "   ⚠️  Warning: #{module_file} not found, skipping..."
  end
end

puts "\n" + "-"*60
puts "🔧 Executing initialization sequence..."
puts "-"*60 + "\n"

# Execute the initialization steps
begin
  # Step 1: Attach project files (from 05_attachments.rb)
  if defined?(attach_project_files)
    attach_project_files
  end
  
  # Step 2: Setup wiki pages (from 06_wiki.rb)
  if defined?(setup_wiki_pages)
    setup_wiki_pages
  end
  
  # Step 3: Generate all issues (from 07_issues.rb)
  if defined?(generate_all_issues)
    generate_all_issues
  end
  
  # Step 4: Generate issue relations (from 08_relations.rb)
  if defined?(generate_all_relations)
    generate_all_relations
  end
  
rescue => e
  puts "\n❌ Error during initialization: #{e.message}"
  puts e.backtrace.first(10).join("\n")
  exit 1
end

# Summary
puts "\n" + "="*60
puts "✅ Initialization completed successfully!"
puts "="*60

elapsed = Time.now - start_time
puts "\n📊 Summary:"
puts "   Duration: #{elapsed.round(2)} seconds"

if defined?($projects_data)
  puts "   Projects: #{$projects_data.length}"
  $projects_data.each do |data|
    project = data[:project]
    puts "      • #{project.name} (#{project.identifier}): #{project.issues.count} issues"
  end
end

if defined?($all_created_issues)
  puts "   New issues created: #{$all_created_issues.length}"
end

puts "\n💡 Tips:"
puts "   • Login at: http://localhost:3000"
puts "   • Admin user: admin / admin123"
puts "   • Demo users: demo1..demo5 / demo123"
puts "   • To re-run: docker compose exec redmine bundle exec rails runner /usr/src/redmine/init/init.rb"

puts "\n🌏 Multilingual content:"
puts "   • All issues contain EN/VI/JA descriptions"
puts "   • Wiki pages are multilingual"
puts "   • Attachments include files in all 3 languages"

puts "\n" + "="*60 + "\n"