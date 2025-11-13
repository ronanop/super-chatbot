.PHONY: help install build start stop restart logs clean test deploy

help:
	@echo "Cache Digitech Chatbot - Makefile Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install all dependencies"
	@echo "  make build         - Build frontend widget"
	@echo ""
	@echo "Development:"
	@echo "  make dev           - Start in development mode"
	@echo "  make dev-frontend  - Start frontend dev server"
	@echo ""
	@echo "Production:"
	@echo "  make start         - Start production server"
	@echo "  make stop          - Stop server"
	@echo "  make restart       - Restart server"
	@echo "  make logs          - View logs"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start Docker containers"
	@echo "  make docker-down   - Stop Docker containers"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make test          - Run tests"
	@echo "  make deploy        - Deploy to production"

install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd chatbot-widget && npm install

build:
	@echo "Building frontend widget..."
	cd chatbot-widget && npm run build

dev:
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "Starting frontend dev server..."
	cd chatbot-widget && npm run dev

start:
	@echo "Starting production server..."
	@if [ -f start.sh ]; then bash start.sh; else uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4; fi

stop:
	@echo "Stopping server..."
	@pkill -f "uvicorn app.main:app" || true

restart: stop start

logs:
	@tail -f logs/app.log 2>/dev/null || docker-compose logs -f backend

docker-build:
	@echo "Building Docker image..."
	docker build -t chatbot-backend:latest .

docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down

clean:
	@echo "Cleaning build artifacts..."
	rm -rf chatbot-widget/dist
	rm -rf chatbot-widget/node_modules
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

test:
	@echo "Running tests..."
	pytest tests/ -v

deploy:
	@echo "Deploying to production..."
	@echo "1. Building frontend..."
	$(MAKE) build
	@echo "2. Building Docker image..."
	$(MAKE) docker-build
	@echo "3. Deploying containers..."
	$(MAKE) docker-up
	@echo "✅ Deployment complete!"
	@echo "Check status: docker-compose ps"
	@echo "View logs: docker-compose logs -f"

