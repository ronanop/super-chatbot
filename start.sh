#!/bin/bash
# Production startup script for Cache Digitech Chatbot

set -e

echo "🚀 Starting Cache Digitech Chatbot..."

# Load environment variables
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "⚠️  Warning: .env file not found. Using environment variables."
fi

# Validate required environment variables
REQUIRED_VARS=("DATABASE_URL" "GEMINI_API_KEY" "PINECONE_API_KEY" "PINECONE_INDEX" "SESSION_SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables:"
    printf '   - %s\n' "${MISSING_VARS[@]}"
    echo ""
    echo "Please set these variables in your .env file or environment."
    exit 1
fi

# Set defaults
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-4}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Build frontend widget if dist doesn't exist
if [ ! -d "chatbot-widget/dist" ]; then
    echo "📦 Building frontend widget..."
    cd chatbot-widget
    npm install
    npm run build
    cd ..
fi

# Run database migrations (if using Alembic)
# Uncomment if you add Alembic migrations:
# echo "🔄 Running database migrations..."
# alembic upgrade head

# Start the application
echo "🌟 Starting application on ${HOST}:${PORT} with ${WORKERS} workers..."
echo ""

if [ "${ENVIRONMENT}" = "development" ]; then
    echo "🔧 Development mode: Using uvicorn with auto-reload"
    uvicorn app.main:app \
        --host "${HOST}" \
        --port "${PORT}" \
        --reload \
        --log-level "${LOG_LEVEL,,}"
else
    echo "🏭 Production mode: Using uvicorn with ${WORKERS} workers"
    uvicorn app.main:app \
        --host "${HOST}" \
        --port "${PORT}" \
        --workers "${WORKERS}" \
        --log-level "${LOG_LEVEL,,}" \
        --access-log \
        --no-use-colors
fi

