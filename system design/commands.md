# Sera Project Commands Reference

This document contains all the commands needed for local development and production deployment.

---

## 1. Local Development Setup & Running

### Prerequisites
- Python 3.12
- Docker & Docker Compose

### Steps:
1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   # Windows (Git Bash / PowerShell):
   .venv/Scripts/activate
   # macOS / Linux:
   # source .venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start PostgreSQL with pgvector (Database):**
   ```bash
   docker compose up -d
   ```

5. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Fill in your API keys, Telegram Bot token, and encryption key in `.env`.

6. **Run Database Migrations (Alembic):**
   ```bash
   alembic upgrade head
   ```

7. **Run Ngrok (for Google OAuth callback in local dev):**
   ```bash
   ngrok http 8000
   ```
   *(Update `GOOGLE_OAUTH_REDIRECT_URI` in `.env` with the ngrok https URL + `/oauth/google/callback`)*

8. **Start Local Development Server (FastAPI + Telegram Bot Polling + Scheduler):**
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 2. Production Deployment (Docker Compose)

### Steps:
1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Configure production environment variables:**
   - Ensure `.env` is properly filled with production values (with a public domain/IP instead of ngrok).

3. **Build and Start Containers (Database + Backend):**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

4. **Run Database Migrations in Container:**
   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

5. **View Logs:**
   ```bash
   docker compose -f docker-compose.prod.yml logs -f
   ```

6. **Stop Production Containers:**
   ```bash
   docker compose -f docker-compose.prod.yml down
   ```

---

## 3. Testing

Run unit and integration tests using pytest:
```bash
cd backend
.venv/Scripts/activate
pytest
```
