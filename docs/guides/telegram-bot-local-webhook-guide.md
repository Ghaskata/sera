# SERA Telegram Bot — Local Run aur Webhook Setup Guide

## Pehle important baat

SERA ke current `main.py` mein **Telegram long polling already implemented** hai. Isliye local development ke liye aapko webhook ki zaroorat nahi hai. Current process ek hi time par FastAPI server, Telegram polling, Google OAuth callback, aur Google-source scheduler start karta hai.

Telegram ke `getUpdates` long polling aur `setWebhook` webhook modes mutually exclusive hain. Agar webhook active rahega to polling kaam nahi karegi, aur polling start karne se pehle webhook delete karna hoga [1](https://core.telegram.org/bots/api).

Webhook mode ke liye current repository mein ek additional FastAPI webhook route aur polling/webhook mode switch add karna padega. Is guide mein dono approaches diye gaye hain.

---

## 1. Required accounts aur tools

Aapko ye cheezein chahiye:

| Requirement | Purpose |
|---|---|
| Telegram bot token | BotFather se bot authenticate karne ke liye |
| Python 3.12+ | SERA backend run karne ke liye |
| Docker | PostgreSQL + pgvector database ke liye |
| Gemini API key | Embeddings aur answer generation ke liye |
| Google OAuth Web Client | Google sign-in aur Drive/Gmail/Calendar access ke liye |
| ngrok ya Cloudflare Tunnel | Local machine ko public HTTPS callback dene ke liye |

Telegram Bot API requests `https://api.telegram.org/bot<TOKEN>/METHOD_NAME` format use karti hain. Token ko URL ya public code mein expose na karein [1](https://core.telegram.org/bots/api).

---

## 2. Repository clone aur Python environment

```bash
gh repo clone Ghaskata/sera
cd sera/backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Windows PowerShell par activation command:

```powershell
.venv\Scripts\Activate.ps1
```

---

## 3. Telegram bot create karein

Telegram mein `@BotFather` open karein:

1. `/newbot` send karein.
2. Bot ka display name dein, jaise `Sera Assistant`.
3. Username dein jo `bot` par end hota ho, jaise `sera_personal_bot`.
4. BotFather jo token de, usse securely save karein.
5. Token ko GitHub, screenshot, chat, ya frontend code mein commit na karein.

Optional commands BotFather ke `/setcommands` se set kiye ja sakte hain:

```text
start - Start Sera and connect Google
login - Sign in with Google
connect_google - Connect Google account
connect_gmail - Connect Gmail
connect_calendar - Connect Google Calendar
insights - Show repeated work patterns
why - Explain an automation candidate
```

---

## 4. Database start karein

`backend/docker-compose.yml` mein PostgreSQL + pgvector service ka naam `db` hai:

```bash
cd sera/backend
docker compose up -d db

docker compose ps
```

Database migration run karein:

```bash
alembic upgrade head
```

Agar Docker available nahi hai, to external PostgreSQL/pgvector use karke `.env` mein `DATABASE_URL` update karein.

---

## 5. `.env` configure karein

```bash
cp .env.example .env
```

Minimum values:

```dotenv
DATABASE_URL=postgresql+asyncpg://sera:sera@localhost:5432/sera

TELEGRAM_BOT_TOKEN=123456789:REPLACE_WITH_BOTFATHER_TOKEN

GOOGLE_CLIENT_ID=REPLACE_WITH_GOOGLE_OAUTH_CLIENT_ID
GOOGLE_CLIENT_SECRET=REPLACE_WITH_GOOGLE_OAUTH_CLIENT_SECRET
GOOGLE_OAUTH_REDIRECT_URI=https://YOUR_PUBLIC_TUNNEL/oauth/google/callback

GEMINI_API_KEY=REPLACE_WITH_GEMINI_KEY
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBED_MODEL=text-embedding-004

TOKEN_ENCRYPTION_KEY=REPLACE_WITH_FERNET_KEY
DRIVE_SYNC_INTERVAL_MINUTES=15
RAG_MIN_SIMILARITY=0.55
RAG_TOP_K=5
```

Encryption key generate karne ke liye:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Is key ko change na karein jab tak aap intentionally sab connected Google accounts ko re-authenticate nahi karwana chahte. Existing encrypted OAuth tokens purani key ke bina decrypt nahi honge.

---

## 6. Google OAuth local callback setup

SERA ka Google callback route hai:

```text
/oauth/google/callback
```

Google Cloud Console mein:

1. Ek Google Cloud project select/create karein.
2. Google Drive API enable karein. Gmail aur Calendar connect karne ke liye unke respective APIs bhi enable karein.
3. OAuth consent screen configure karein.
4. Testing mode mein apne Google account ko test user ke roop mein add karein.
5. Credentials → Create Credentials → OAuth client ID → Web application select karein.
6. Authorized redirect URI mein exact tunnel callback add karein:

```text
https://YOUR_TUNNEL_DOMAIN/oauth/google/callback
```

Google redirect URI exact match honi chahiye. `http://localhost:8000/...` ko public Google OAuth callback ke liye use na karein.

Google user-data scopes sensitive ho sakte hain aur public app ke liye verification requirements aa sakti hain. Isliye SERA provider-specific narrow read scopes use karta hai [2](https://developers.google.com/identity/protocols/oauth2/scopes).

---

# Part A — Local development with long polling

## 7. Existing webhook delete karein

Local polling start karne se pehle webhook remove karein. `.env` se token load karke command run karein:

```bash
set -a
source .env
set +a

curl -sS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook" \
  -d "drop_pending_updates=true"
```

Expected response roughly:

```json
{"ok":true,"result":true,"description":"Webhook was deleted"}
```

Status verify karein:

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

Expected `url` empty honi chahiye.

## 8. SERA backend start karein

```bash
cd sera/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Ab Telegram mein bot open karke:

```text
/start
```

SERA aapko Google sign-in link dega. Google consent complete karke Telegram par return karein, phir question bhejein.

## 9. Local polling troubleshooting

### `Conflict: terminated by other getUpdates request`

Iska matlab usually do bot processes polling kar rahe hain. Saare duplicate `uvicorn` processes stop karein:

```bash
pkill -f 'uvicorn app.main:app' || true
```

Phir webhook delete karke ek hi process start karein:

```bash
curl -sS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook" \
  -d "drop_pending_updates=true"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### `/start` par Google URL issue

Check karein ki `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, aur `GOOGLE_OAUTH_REDIRECT_URI` filled hain. Google Console mein redirect URI aur `.env` value character-by-character same honi chahiye.

### Database connection error

```bash
docker compose ps
docker compose logs db
```

`DATABASE_URL` ka username, password, database name, aur port compose file se match karein.

---

# Part B — Local webhook with ngrok

## 10. Webhook ke liye tunnel start karein

Pehle FastAPI app ko port 8000 par chalayein. Doosre terminal mein:

```bash
ngrok http 8000
```

Aapko URL milega, example:

```text
https://abc123.ngrok-free.app
```

Is URL ke through dono routes available honge:

```text
https://abc123.ngrok-free.app/oauth/google/callback
https://abc123.ngrok-free.app/telegram/webhook
```

Telegram webhooks ke liye public URL HTTPS hona chahiye. Telegram ki webhook documentation supported public ports aur TLS requirements explain karti hai [3](https://core.telegram.org/bots/webhooks).

---

## 11. Current repository mein webhook support add karein

Current code polling start karta hai:

```python
await bot_app.updater.start_polling()
```

Webhook mode ke liye is line ko conditionally run karna hoga, aur FastAPI mein Telegram POST route add karna hoga.

### 11.1 Configuration fields add karein

`backend/app/config.py` ke `Settings` class mein add karein:

```python
telegram_mode: str = "polling"
telegram_webhook_base_url: str = ""
telegram_webhook_path: str = "/telegram/webhook"
telegram_webhook_secret: str = ""
```

`.env` mein:

```dotenv
TELEGRAM_MODE=webhook
TELEGRAM_WEBHOOK_BASE_URL=https://abc123.ngrok-free.app
TELEGRAM_WEBHOOK_PATH=/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=replace-with-a-long-random-secret
```

Secret generate karne ke liye:

```bash
openssl rand -hex 32
```

### 11.2 Webhook route create karein

File banayein: `backend/app/api/routes/telegram.py`

```python
from fastapi import APIRouter, HTTPException, Request
from telegram import Update

from app.config import settings

router = APIRouter(tags=["telegram"])


@router.post(settings.telegram_webhook_path)
async def telegram_webhook(request: Request):
    expected = settings.telegram_webhook_secret
    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if expected and received != expected:
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

    application = getattr(request.app.state, "telegram_application", None)
    if application is None:
        raise HTTPException(status_code=503, detail="Telegram application is not ready")

    payload = await request.json()
    update = Update.de_json(payload, application.bot)
    await application.process_update(update)
    return {"ok": True}
```

### 11.3 Router register karein

`backend/app/main.py` mein import update karein:

```python
from app.api.routes import connectors, health, oauth, telegram
```

Aur router include karein:

```python
app.include_router(telegram.router)
```

### 11.4 Lifespan mein polling/webhook switch add karein

`main.py` ke lifespan mein application ko `app.state` par expose karein aur polling ko conditional banayein:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_app = build_application()
    await bot_app.initialize()
    await bot_app.start()
    app.state.telegram_application = bot_app

    if settings.telegram_mode == "webhook":
        webhook_url = f"{settings.telegram_webhook_base_url.rstrip('/')}{settings.telegram_webhook_path}"
        await bot_app.bot.set_webhook(
            url=webhook_url,
            secret_token=settings.telegram_webhook_secret or None,
            drop_pending_updates=True,
        )
    else:
        await bot_app.updater.start_polling()

    scheduler = build_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        if settings.telegram_mode == "polling":
            await bot_app.updater.stop()
        else:
            await bot_app.bot.delete_webhook(drop_pending_updates=False)
        await bot_app.stop()
        await bot_app.shutdown()
```

Is snippet ke liye `main.py` mein ye import bhi ensure karein:

```python
from app.config import settings
```

Webhook mode mein `start_polling()` aur `set_webhook()` ko ek saath run na karein.

---

## 12. Webhook mode start karein

`.env` mein:

```dotenv
TELEGRAM_MODE=webhook
TELEGRAM_WEBHOOK_BASE_URL=https://abc123.ngrok-free.app
TELEGRAM_WEBHOOK_PATH=/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=your-long-random-secret
GOOGLE_OAUTH_REDIRECT_URI=https://abc123.ngrok-free.app/oauth/google/callback
```

Phir:

```bash
cd sera/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Application startup par SERA Telegram ke `setWebhook` method ko call karega. Agar aap manually set karna chahte hain:

```bash
set -a
source .env
set +a

WEBHOOK_URL="${TELEGRAM_WEBHOOK_BASE_URL}${TELEGRAM_WEBHOOK_PATH}"

curl -sS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}" \
  -d "drop_pending_updates=true"
```

Webhook status:

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

Healthy response mein `url` aapke webhook URL ke equal hogi. `pending_update_count` aur `last_error_message` debugging ke liye useful fields hain [1](https://core.telegram.org/bots/api).

Telegram mein bot ko message bhejkar test karein:

```text
/start
```

ngrok terminal mein incoming `POST /telegram/webhook` request dikhni chahiye, aur uvicorn logs mein update processing dikhni chahiye.

---

## 13. Webhook manually test karna

Secret header ke saath minimal update POST kar sakte hain:

```bash
curl -i -X POST \
  "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
  --data '{"update_id":123456789}'
```

Expected response:

```json
{"ok":true}
```

Invalid secret par expected response `403` hona chahiye.

Real message processing test karne ke liye Telegram app se `/start` bhejna better hai, kyunki manually generated update mein valid chat/message/user object nahi hota.

---

## 14. Webhook stop karke polling par wapas aana

`.env` mein:

```dotenv
TELEGRAM_MODE=polling
```

Webhook delete karein:

```bash
set -a
source .env
set +a

curl -sS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook" \
  -d "drop_pending_updates=true"
```

Phir backend restart karein:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 15. Recommended development workflow

| Situation | Recommended mode |
|---|---|
| Daily local coding | Long polling |
| Google OAuth local testing | Long polling + ngrok only for Google callback |
| Testing Telegram inbound HTTPS delivery | Webhook + ngrok/Cloudflare Tunnel |
| Production deployment | Webhook + permanent HTTPS domain |
| Multiple developers using same bot | One active polling/webhook process only |

Local development mein **long polling simplest** hai. Webhook tab use karein jab aap inbound HTTPS behavior, deployment, proxy, secret-header verification, ya production-like flow test karna chahte hain.

## References

[1]: https://core.telegram.org/bots/api "Telegram Bot API"

[2]: https://developers.google.com/identity/protocols/oauth2/scopes "OAuth 2.0 Scopes for Google APIs"

[3]: https://core.telegram.org/bots/webhooks "Telegram Webhook Guide"
