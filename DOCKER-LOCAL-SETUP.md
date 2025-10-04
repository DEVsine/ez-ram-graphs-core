# 🐳 Docker Local Setup

Simple guide for running ez_ram in Docker containers alongside your local development environment.

## Quick Start

```bash
# 1. Copy environment file
cp .env.docker .env

# 2. Edit .env with your settings (API keys, passwords, etc.)

# 3. Start everything
./quick-start.sh

# OR use make commands
make build
make up
```

## Port Configuration

Docker containers use **different ports** to avoid conflicts with local development:

| Service    | Docker Port | Local Port | Access URL            |
| ---------- | ----------- | ---------- | --------------------- |
| Django     | 8001        | 8000       | http://localhost:8001 |
| PostgreSQL | 25432       | 5432       | localhost:25432       |
| Neo4j HTTP | 7500        | 7474       | http://localhost:7500 |
| Neo4j Bolt | 7690        | 7687       | bolt://localhost:7690 |

**This means you can run both Docker AND local development simultaneously!**

## Common Commands

### Using Make (Recommended)

```bash
make help           # Show all available commands
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make logs           # View all logs
make logs-web       # View Django logs only
make shell          # Open Django shell
make bash           # Open bash in web container
make migrate        # Run migrations
make makemigrations # Create migrations
make superuser      # Create Django superuser
make test           # Run tests
make clean          # Remove containers and volumes
```

### Using Docker Compose Directly

```bash
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose logs -f            # View logs
docker-compose ps                 # Check status
docker-compose exec web bash     # Access web container
docker-compose restart            # Restart all services
```

## Environment Variables

Key variables in `.env`:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web

# PostgreSQL
POSTGRES_DB=ez_ram
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password

# Neo4j
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# AI APIs (optional)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Ports (optional - defaults shown)
PORT=8001
POSTGRES_PORT=25432
NEO4J_HTTP_PORT=7500
NEO4J_BOLT_PORT=7690
```

## Connecting to Services

### From Your Local Machine

```python
# Django - http://localhost:8001

# PostgreSQL
psql -h localhost -p 25432 -U postgres -d ez_ram

# Neo4j Browser
# Open: http://localhost:7500
# Bolt URL: bolt://localhost:7690
```

### From Inside Docker Containers

```python
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432  # Internal port

# Neo4j
NEO4J_BOLT_URL=bolt://neo4j:7687  # Internal port
```

## Troubleshooting

### Port Already in Use

If you get port conflicts, check what's using the port:

```bash
# macOS/Linux
lsof -i :8001
lsof -i :25432

# Then kill the process or change the port in .env
```

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs web
docker-compose logs postgres
docker-compose logs neo4j

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U postgres

# Check if Neo4j is ready
docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1"
```

### Clean Start

```bash
# Remove everything and start fresh
make clean
make build
make up
```

## Development Workflow

1. **Start Docker services** (databases only if you want):

   ```bash
   docker-compose up -d postgres neo4j
   ```

2. **Run Django locally** on port 8000:

   ```bash
   python manage.py runserver
   ```

3. **Or run everything in Docker**:
   ```bash
   docker-compose up -d
   # Access at http://localhost:8001
   ```

## Files Overview

- `docker-compose.yml` - Service definitions
- `Dockerfile` - Django app image
- `docker-entrypoint.sh` - Startup script
- `.env` - Environment variables (create from `.env.docker`)
- `.env.docker` - Template for Docker environment
- `Makefile` - Convenient shortcuts
- `quick-start.sh` - Automated setup script

## Next Steps

After setup:

1. Create a superuser:

   ```bash
   make superuser
   # OR
   docker-compose exec web python manage.py createsuperuser
   ```

2. Access the admin:

   - URL: http://localhost:8001/admin
   - Login with your superuser credentials

3. Check the API:

   - Health check: http://localhost:8001/health/
   - API endpoints: http://localhost:8001/api/

4. View Neo4j data:
   - Browser: http://localhost:7475
   - Login: neo4j / password (from .env)
