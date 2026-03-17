# /usr/src/redmine/init/00_bootstrap.rb
# Bootstrap script - Load environment and common utilities

begin
  require_relative "../config/environment"
rescue LoadError
  require_relative "../../config/environment"
end
require 'fileutils'

# -------------------------
# Pretty logging
# -------------------------

def say(msg)  puts ">> #{msg}" end
def ok(msg)   puts "✅ #{msg}" end
def warnx(msg) puts "⚠️  #{msg}" end

ActiveRecord::Base.logger = nil

# -------------------------
# Set global seed author
# -------------------------

SEED_AUTHOR = begin
  u = (User.where(admin: true, status: 1).order(:id).first rescue nil)
  u ||= (User.find_by(login: 'admin') rescue nil)
  u ||= (User.where(status: 1).order(:id).first rescue nil)
  u ||= (User.first rescue nil)
  User.current = u if defined?(User) && u
  u
end

# -------------------------
# Detect Faker
# -------------------------

FAKER_AVAILABLE = begin
  require 'faker'
  true
rescue LoadError
  false
end

# -------------------------
# Config
# -------------------------

SEED_FILES_DIR = "/usr/src/redmine/init/seed_files"

ok "Bootstrap completed. Seed author: #{SEED_AUTHOR&.login || 'N/A'}"