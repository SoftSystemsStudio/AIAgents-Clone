#!/bin/bash
# Quick start script for Gmail Cleanup API

set -e

echo "🚀 Starting Gmail Cleanup API..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Creating from template..."
    cat > .env << EOF
# Gmail Cleanup API Configuration

# JWT Secret (CHANGE THIS IN PRODUCTION!)
JWT_SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING_IN_PRODUCTION

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/gmail_cleanup

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1
EOF
    echo "✅ Created .env file. Please update JWT_SECRET_KEY and DATABASE_URL."
    echo ""
fi

# Check dependencies
echo "📦 Checking dependencies..."
python -c "import fastapi, jose, passlib" 2>/dev/null || {
    echo "Installing dependencies..."
    pip install -e . -q
}

echo "✅ Dependencies installed"
echo ""

# Start server
echo "🌐 Starting API server on http://localhost:8000"
echo "📚 API documentation: http://localhost:8000/api/docs"
echo ""

python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
