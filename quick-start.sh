#!/bin/bash
# Quick start script for ez_ram Docker setup

set -e

echo "🚀 ez_ram Docker Quick Start"
echo "=============================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.docker .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file and update the following:"
    echo "   - SECRET_KEY (generate a secure random string)"
    echo "   - Database passwords"
    echo "   - API keys (OPENAI_API_KEY, GEMINI_API_KEY)"
    echo ""
    read -p "Press Enter to continue after editing .env file, or Ctrl+C to exit..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🔨 Building Docker images..."
docker compose build

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "📊 Service status:"
docker compose ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "📍 Access points:"
echo "   - Django Application: http://localhost:8001"
echo "   - Django Admin: http://localhost:8001/admin"
echo "   - Neo4j Browser: http://localhost:7500"
echo ""
echo "🔑 Default credentials (if configured in .env):"
echo "   - Django Admin: admin / admin123"
echo "   - Neo4j: neo4j / password"
echo ""
echo "ℹ️  Port Configuration (Docker vs Local):"
echo "   - Django:     localhost:8001 (Docker) vs localhost:8000 (Local)"
echo "   - PostgreSQL: localhost:25432 (Docker) vs localhost:5432 (Local)"
echo "   - Neo4j HTTP: localhost:7500 (Docker) vs localhost:7474 (Local)"
echo "   - Neo4j Bolt: localhost:7690 (Docker) vs localhost:7687 (Local)"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Stop services: docker compose down"
echo "   - Restart services: docker compose restart"
echo "   - Django shell: docker compose exec web python manage.py shell"
echo "   - Run migrations: docker compose exec web python manage.py migrate"
echo "   - Create superuser: docker compose exec web python manage.py createsuperuser"

