#!/bin/bash

set -e

echo "🚀 RAG System Setup Script"
echo "=========================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created. Please edit it with your configuration.${NC}"
    echo ""
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
    echo ""
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p uploads
mkdir -p app/services
mkdir -p app/api
mkdir -p app/schedulers
mkdir -p streamlit_app/pages
mkdir -p scripts
mkdir -p tests
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Build Docker images
echo -e "${YELLOW}🔨 Building Docker images (this may take a few minutes)...${NC}"
docker-compose build
echo -e "${GREEN}✅ Docker images built successfully${NC}"
echo ""

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 15

# Check if PostgreSQL is ready
echo -e "${YELLOW}🔍 Checking PostgreSQL...${NC}"
until docker exec rag-postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
echo ""

# Check if Redis is ready
echo -e "${YELLOW}🔍 Checking Redis...${NC}"
until docker exec rag-redis redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done
echo -e "${GREEN}✅ Redis is ready${NC}"
echo ""

# Create network if it doesn't exist
echo -e "${YELLOW}🌐 Checking Docker network...${NC}"
if ! docker network ls | grep -q rag-network; then
    docker network create rag-network || true
    echo -e "${GREEN}✅ Docker network 'rag-network' created${NC}"
else
    echo -e "${GREEN}✅ Docker network 'rag-network' already exists${NC}"
fi
echo ""

# Check if Backend is running
echo -e "${YELLOW}🔍 Checking Backend service...${NC}"
sleep 5
MAX_RETRIES=20
RETRY_COUNT=0
BACKEND_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker ps | grep -q rag-backend; then
        # Try to check health endpoint from host (if curl is available)
        if command -v curl &> /dev/null; then
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Backend service is ready${NC}"
                BACKEND_READY=true
                break
            fi
        else
            # If curl not available, just check if container is running
            if docker ps --format '{{.Names}}' | grep -q rag-backend; then
                echo -e "${GREEN}✅ Backend container is running${NC}"
                BACKEND_READY=true
                break
            fi
        fi
    fi
    echo "Waiting for Backend service... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ "$BACKEND_READY" = false ]; then
    echo -e "${YELLOW}⚠️  Backend service may not be fully ready yet. Check logs with: make logs-backend${NC}"
fi
echo ""

# Check if Scheduler is running
echo -e "${YELLOW}🔍 Checking Scheduler service...${NC}"
if docker ps | grep -q rag-scheduler; then
    echo -e "${GREEN}✅ Scheduler service is running${NC}"
else
    echo -e "${YELLOW}⚠️  Scheduler service may not be ready yet${NC}"
fi
echo ""

# Initialize database
echo -e "${YELLOW}🗄️ Initializing database...${NC}"
docker exec rag-postgres psql -U postgres -d rag_db -c "SELECT 1" > /dev/null 2>&1
echo -e "${GREEN}✅ Database initialized${NC}"
echo ""

# Show service status
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo "=================================="
echo "📊 Access your services:"
echo "=================================="
echo -e "${GREEN}Streamlit UI:${NC}    http://localhost:8501"
echo -e "${GREEN}FastAPI Docs:${NC}    http://localhost:8000/docs"
echo -e "${GREEN}API Health:${NC}      http://localhost:8000/health"
echo ""
echo "=================================="
echo "🔧 Useful commands:"
echo "=================================="
echo "  make logs          - View all logs"
echo "  make logs-backend  - View backend logs"
echo "  make stats         - Show system statistics"
echo "  make down          - Stop all services"
echo "  make up            - Start all services"
echo "  make help          - Show all available commands"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Configure your system${NC}"
echo ""
echo "1. Edit .env file with required configuration:"
echo "   - OPENAI_API_KEY: Your OpenAI API key (required)"
echo "   - OPENAI_MODEL: Fallback model (default: gpt-4o-mini)"
echo "   - REDMINE_URL: Redmine instance URL (optional)"
echo "   - REDMINE_API_KEY: Redmine API key (optional)"
echo ""
echo "2. Configure OpenAI Model in Database:"
echo "   - Access Streamlit UI: http://localhost:8501"
echo "   - Go to '⚙️ OpenAI Config' tab"
echo "   - Click 'Sync Default Pricing' to create model configs"
echo "   - Select and set your default model"
echo ""
echo -e "${YELLOW}💡 Note: Model is stored in database, not .env file${NC}"
echo -e "${YELLOW}💡 Get your OpenAI API key from: https://platform.openai.com/api-keys${NC}"
echo ""