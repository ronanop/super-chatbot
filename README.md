# AskCache.ai - AI-Powered RAG Chatbot
**Made with ❤️ by Rishabh Gaur (@ronanop)**

A comprehensive, production-ready AI chatbot solution powered by Google Gemini, featuring RAG (Retrieval-Augmented Generation), knowledge base management, web crawling, and a beautiful admin panel.

No Need of N8N or readymade RAG builds : Pure coding

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-19.2-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Deployment](#-deployment)
- [API Documentation](#-api-documentation)
- [Admin Panel](#-admin-panel)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### Core Features
- 🤖 **AI-Powered Chatbot** - Powered by Google Gemini 2.5 Flash
- 📚 **Knowledge Base Management** - Upload PDFs and crawl websites
- 🔍 **RAG (Retrieval-Augmented Generation)** - Context-aware responses using Pinecone vector database
- 🌐 **Web Crawler** - Intelligent web scraping with JavaScript rendering support
- 💬 **English Language Support** - Optimized for English conversations
- 🎤 **Voice Input** - Speech-to-text functionality
- 📊 **Analytics Dashboard** - Real-time statistics and charts
- 🔐 **Secure Admin Panel** - Session-based authentication

### Advanced Features
- 📝 **Custom Instructions** - Configure chatbot behavior via admin panel
- 🎨 **UI Customization** - Customize chatbot appearance (colors, icons, branding)
- 📥 **Export Transcripts** - Download chat sessions as JSON
- 📈 **Real-time Progress** - Track ingestion and crawling progress
- 🔄 **Session Management** - Track user sessions and conversations
- 📧 **Lead Capture** - Collect user information after 3rd message
- 🎯 **Smart Context Retrieval** - Automatic knowledge base prioritization

## 🛠 Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.9+
- **LLM**: Google Gemini 2.5 Flash
- **Vector Database**: Pinecone
- **Database**: PostgreSQL 12+
- **ORM**: SQLAlchemy 2.0+
- **Session Management**: Starlette Sessions
- **Document Processing**: PyPDF2, pdfplumber
- **Web Scraping**: Selenium, BeautifulSoup4, Playwright

### Frontend
- **Framework**: React 19.2
- **Build Tool**: Vite 7.2
- **Styling**: Tailwind CSS 3.4
- **Voice Input**: Web Speech API

### Infrastructure
- **Server**: Uvicorn/Gunicorn
- **Deployment**: Docker, Cloud Run, AWS App Runner
- **CDN**: CloudFront/Cloud CDN (for frontend)

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Python** 3.9 or higher
- **Node.js** 18+ and npm
- **PostgreSQL** 12+ (or use managed service)
- **Git**
- **Google Cloud Account** (for Gemini API)
- **Pinecone Account** (free tier available)

### API Keys Required
- Google Gemini API Key ([Get it here](https://ai.google.dev/))
- Pinecone API Key ([Get it here](https://www.pinecone.io/))
- PostgreSQL Database URL

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd finalbot
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

#### Install Python Dependencies

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary
pip install google-generativeai pinecone-client
pip install python-dotenv pydantic email-validator
pip install pypdf2 pdfplumber langchain langchain-text-splitters
pip install selenium beautifulsoup4 playwright
pip install itsdangerous starlette
```

Or create a `requirements.txt`:

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
google-generativeai>=0.3.0
pinecone>=5.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic[email]>=2.0.0
langchain>=0.1.0
langchain-text-splitters>=0.0.1
pypdf2>=3.0.0
pdfplumber>=0.10.0
selenium>=4.15.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
itsdangerous>=2.1.0
starlette>=0.27.0
jinja2>=3.1.0
aiofiles>=23.2.0
```

Then install:
```bash
pip install -r requirements.txt
```

#### Install Playwright Browsers (for web scraping)

```bash
playwright install chromium
```

### 3. Frontend Setup

```bash
cd chatbot-widget
npm install
```

### 4. Database Setup

#### Create PostgreSQL Database

```sql
CREATE DATABASE chatbot_db;
```

#### Initialize Database Tables

```bash
# From project root with venv activated
python -m app.db.init_db
```

### 5. Environment Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/chatbot_db

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=models/gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=chatbot-index

# Admin Panel
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here
SESSION_SECRET_KEY=your_random_secret_key_here

# CORS (optional)
ALLOWED_ORIGINS=*

# Widget Source URL (optional)
WIDGET_IFRAME_SRC=http://localhost:5173
```

### 6. Initialize Pinecone Index

The index will be created automatically on first use, or you can create it manually:

```python
from app.vectorstore.pinecone_store import _ensure_index
_ensure_index()
```

## ⚙️ Configuration

### Backend Configuration

All configuration is done via environment variables (`.env` file). Key settings:

- **DATABASE_URL**: PostgreSQL connection string
- **GEMINI_API_KEY**: Your Google Gemini API key
- **PINECONE_API_KEY**: Your Pinecone API key
- **ADMIN_USERNAME/PASSWORD**: Admin panel credentials
- **SESSION_SECRET_KEY**: Random secret for session encryption

### Frontend Configuration

Edit `chatbot-widget/src/config.js` to set the API base URL:

```javascript
const API_BASE_URL = "http://localhost:8000";
```

Or set via environment variable:
```bash
# Create chatbot-widget/.env
VITE_API_BASE_URL=http://localhost:8000
```

## 🎯 Usage

### Starting the Backend

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode (multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Starting the Frontend

```bash
cd chatbot-widget
npm run dev

# For network access
npm run dev -- --host 0.0.0.0 --port 5173
```

### Building Frontend for Production

```bash
cd chatbot-widget
npm run build
```

The built files will be in `chatbot-widget/dist/` directory.

### Access Points

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin
- **Frontend Widget**: http://localhost:5173

## 📚 API Documentation

### Chat Endpoint

**POST** `/chat`

Send a message to the chatbot.

```json
{
  "message": "What services do you offer?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "reply": "We offer...",
  "session_id": "generated-session-id",
  "prompt_for_info": false
}
```

### User Info Endpoint

**POST** `/user-info`

Submit user information (triggered after 3rd message).

```json
{
  "session_id": "session-id",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890"
}
```

### Health Check

**GET** `/health`

Returns server status.

## 🎛 Admin Panel

### Accessing Admin Panel

1. Navigate to `http://localhost:8000/admin`
2. You'll be redirected to login page
3. Enter your admin credentials

### Features

#### Dashboard
- View statistics (users, sessions, messages)
- Real-time charts (sessions over time, message distribution)
- Recent chat sessions

#### Knowledge Base Management
- Upload PDF documents
- Crawl websites and extract content
- Organize documents into folders
- View, rename, and delete documents
- Real-time ingestion progress

#### User Management
- View all registered users
- See user contact information
- View associated chat sessions

#### Chat Sessions
- Browse all chat sessions
- View full transcripts
- Download transcripts as JSON
- Filter by user

#### Bot UI Customization
- Customize chatbot name and icon
- Change colors (primary, secondary, backgrounds)
- Configure widget position and size
- Add custom CSS
- Preview changes

#### Settings
- Configure API base URL
- Set custom chatbot instructions
- Auto-detect network IP

## 🚢 Deployment

### Option 1: Docker Deployment

#### Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Build and Run

```bash
docker build -t chatbot-backend .
docker run -p 8000:8000 --env-file .env chatbot-backend
```

### Option 2: Google Cloud Run

#### Create app.yaml

```yaml
runtime: python39
instance_class: F2
automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6
env_variables:
  DATABASE_URL: "your-cloud-sql-connection"
  GEMINI_API_KEY: "your-key"
  PINECONE_API_KEY: "your-key"
```

#### Deploy

```bash
gcloud app deploy
```

### Option 3: AWS App Runner

1. Push code to GitHub
2. Create App Runner service
3. Configure environment variables
4. Deploy

### Option 4: VPS Deployment

#### Using Systemd

Create `/etc/systemd/system/chatbot.service`:

```ini
[Unit]
Description=Chatbot API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/chatbot
Environment="PATH=/var/www/chatbot/.venv/bin"
ExecStart=/var/www/chatbot/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Enable and Start

```bash
sudo systemctl enable chatbot
sudo systemctl start chatbot
```

### Frontend Deployment

#### Option 1: Static Hosting (S3 + CloudFront)

```bash
cd chatbot-widget
npm run build
aws s3 sync dist/ s3://your-bucket-name
aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

#### Option 2: Netlify/Vercel

```bash
cd chatbot-widget
npm run build
# Deploy dist/ folder to Netlify/Vercel
```

#### Option 3: Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/chatbot-widget/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Database Setup (Production)

#### Google Cloud SQL

```bash
gcloud sql instances create chatbot-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1
```

#### AWS RDS

Create PostgreSQL RDS instance via AWS Console or CLI.

### Environment Variables (Production)

Set these in your deployment platform:

- `DATABASE_URL` - Managed PostgreSQL connection string
- `GEMINI_API_KEY` - Your Gemini API key
- `PINECONE_API_KEY` - Your Pinecone API key
- `ADMIN_USERNAME` - Admin username
- `ADMIN_PASSWORD` - Strong admin password
- `SESSION_SECRET_KEY` - Random 32+ character string
- `ALLOWED_ORIGINS` - Comma-separated list of allowed origins

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Error

**Error**: `sqlalchemy.exc.OperationalError`

**Solution**:
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL format: `postgresql+psycopg2://user:pass@host:port/db`
- Check firewall rules

#### 2. Gemini API Error

**Error**: `ModuleNotFoundError: No module named 'google'`

**Solution**:
```bash
pip install google-generativeai
```

#### 3. Pinecone Connection Error

**Error**: `pinecone.exceptions.PineconeException`

**Solution**:
- Verify PINECONE_API_KEY is correct
- Check PINECONE_ENVIRONMENT matches your region
- Ensure index exists

#### 4. Frontend Can't Connect to Backend

**Error**: `Failed to fetch`

**Solution**:
- Check CORS settings in backend
- Verify API_BASE_URL in frontend config
- Ensure backend is running on correct port
- Check firewall rules

#### 5. Admin Panel Login Not Working

**Error**: Redirect loop or authentication failure

**Solution**:
- Verify ADMIN_USERNAME and ADMIN_PASSWORD in .env
- Check SESSION_SECRET_KEY is set
- Clear browser cookies
- Restart server

#### 6. Web Scraping Fails

**Error**: No content scraped

**Solution**:
- Install Playwright browsers: `playwright install chromium`
- Check if website blocks scraping
- Verify URLs are accessible
- Check logs in admin panel

### Performance Issues

#### Slow Response Times

1. **Check Gemini API quota** - Upgrade if hitting limits
2. **Optimize database queries** - Add indexes
3. **Use connection pooling** - Configure SQLAlchemy pool
4. **Add caching** - Cache common queries
5. **Scale horizontally** - Add more workers/instances

See [SCALING_GUIDE.md](SCALING_GUIDE.md) for detailed scaling strategies.

## 📊 Monitoring

### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

### Logs

Backend logs are available in:
- Terminal output (development)
- Admin panel logs section
- System logs (production)

### Metrics to Monitor

- Request latency (p50, p95, p99)
- Error rates
- Gemini API response times
- Database query times
- Concurrent user count
- Memory usage

## 🔒 Security Considerations

1. **Environment Variables**: Never commit `.env` file
2. **Session Secret**: Use strong random string (32+ characters)
3. **Admin Password**: Use strong, unique password
4. **CORS**: Restrict ALLOWED_ORIGINS in production
5. **HTTPS**: Always use HTTPS in production
6. **Database**: Use managed database with encryption
7. **API Keys**: Rotate keys regularly
8. **Rate Limiting**: Implement rate limiting for production

## 📖 Additional Documentation

- [Scaling Guide](SCALING_GUIDE.md) - How to scale the application
- [Custom Crawler Integration](CUSTOM_CRAWLER_INTEGRATION.md) - Integrate custom crawlers
- [Frontend-Backend Connection](FRONTEND_BACKEND_CONNECTION.md) - Network setup guide

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini for LLM capabilities
- Pinecone for vector database
- FastAPI for the excellent web framework
- React team for the frontend framework

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section

## 🎯 Roadmap

- [ ] Multi-tenant support
- [ ] Advanced analytics
- [ ] Custom model fine-tuning
- [ ] Webhook integrations
- [ ] Mobile app support
- [ ] Multi-language admin panel
- [ ] Advanced caching strategies
- [ ] GraphQL API

---



