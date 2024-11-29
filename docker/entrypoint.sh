#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Wait for Redis if enabled
if [ "$REDIS_ENABLED" = "true" ]; then
    echo "Waiting for Redis..."
    while ! nc -z redis 6379; do
        sleep 0.1
    done
    echo "Redis is ready!"
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Create initial superuser if needed
if [ "$CREATE_SUPERUSER" = "true" ]; then
    echo "Creating superuser..."
    python src/scripts/create_superuser.py
fi

# Execute the main command
echo "Starting application..."
exec "$@"
