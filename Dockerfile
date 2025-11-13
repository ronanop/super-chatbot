# Multi-stage build for production-ready chatbot application

# Stage 1: Build frontend widget
FROM node:18-alpine AS frontend-builder

WORKDIR /app/chatbot-widget

# Copy package files
COPY chatbot-widget/package*.json ./

# Install dependencies (need dev dependencies for build)
RUN npm ci

# Copy source files
COPY chatbot-widget/ .

# Build frontend
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY --from=frontend-builder /app/chatbot-widget/dist ./chatbot-widget/dist

# Create directories for uploads and knowledge base
RUN mkdir -p uploads/header_images knowledge_base scraped

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application (workers can be overridden via environment variable)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-4}"

