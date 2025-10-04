#!/bin/bash
set -e

echo "Starting ez_ram application..."

# Function to wait for a service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service_name at $host:$port..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $attempt -eq $max_attempts ]; then
            echo "ERROR: $service_name at $host:$port is not available after $max_attempts attempts"
            exit 1
        fi
        echo "Attempt $attempt/$max_attempts: $service_name is unavailable - sleeping"
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo "$service_name at $host:$port is ready!"
}

# Wait for PostgreSQL if configured
if [ -n "$POSTGRES_HOST" ]; then
    wait_for_service "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
fi

# Wait for Neo4j if configured (extract host from bolt URL)
if [ -n "$NEO4J_BOLT_URL" ]; then
    # Extract host and port from bolt URL (basic parsing)
    NEO4J_HOST=$(echo "$NEO4J_BOLT_URL" | sed -E 's|bolt://([^:]+@)?([^:]+):.*|\2|')
    NEO4J_PORT=$(echo "$NEO4J_BOLT_URL" | sed -E 's|.*:([0-9]+)|\1|')
    if [ -n "$NEO4J_HOST" ] && [ -n "$NEO4J_PORT" ]; then
        wait_for_service "$NEO4J_HOST" "$NEO4J_PORT" "Neo4j"
    fi
fi

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if environment variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
END
fi

echo "Starting application server..."

# Execute the main command
exec "$@"

