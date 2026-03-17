# Redmine Docker Setup

Redmine version: **5.1.2** (Alpine) - Check [docker-compose.yml](./docker-compose.yml)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Network `rag-network` must exist (created by redmine-data setup)

### 1. Start Services

```bash
docker compose up -d
```

### 2. Initialize Redmine

**Step 1: Run setup script** (enables API, sets admin password, creates API key)

```bash
docker compose exec redmine bundle exec rails runner 'load "/usr/src/redmine/init/setup.rb"'
```

**Step 2: Load master data** (projects, issues, wiki pages, etc.)

```bash
docker compose exec redmine bundle exec rails runner 'load "/usr/src/redmine/init/init.rb"'
```

> **Note:** The setup script will print the admin API access key at the end. Save it for API testing.

## 📋 Default Credentials

- **Username:** `admin`
- **Password:** `admin123`
- **API Key:** Generated dynamically (printed after running setup.rb)

## 🔗 Access

- **Redmine Web UI:** http://localhost:8080
- **MySQL Database:** localhost:3307 (user: `root`, password: `rootpass`, database: `redmine`)

## 🧪 API Testing

### Get Admin API Key

After running `setup.rb`, the API key will be printed in the output:

```
🔐 ADMIN API ACCESS KEY:
👉 <your-api-key-here>
```

### Test API

**Get issues:**
```bash
curl -H "X-Redmine-API-Key: <your-api-key>" http://localhost:8080/issues.json
```

**Create issue:**
```bash
curl -v \
  -H "X-Redmine-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"issue":{"project_id":"demo1-ait","subject":"Test Issue"}}' \
  http://localhost:8080/issues.json
```

## 📁 Project Structure

```
redmine-assistant/
├── docker-compose.yml    # Docker configuration
├── src/                  # Initialization scripts
│   ├── setup.rb         # Basic setup (API, admin, users)
│   ├── init.rb          # Master data seeder
│   └── seed_files/      # Seed data files
└── plugins/             # Redmine plugins
    └── custom_features/ # Custom search and features plugin
```

## 🔧 Configuration

- **Database:** MySQL 8.0 (utf8mb4 encoding)
- **Network:** `rag-network` (external, shared with redmine-data)
- **Ports:**
  - Redmine: `8080:3000`
  - MySQL: `127.0.0.1:3307:3306` (only accessible from localhost)

## 📝 Notes

- API key is generated dynamically on each setup
- Master data includes multilingual content (EN/VI/JA)
- Custom plugin `custom_features` provides enhanced search functionality
- Database uses utf8mb4 for full Unicode support
