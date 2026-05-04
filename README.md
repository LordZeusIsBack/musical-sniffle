# Therapy Chatbot Backend (FastAPI)

FastAPI backend for a privacy-aware therapy chatbot that **does not store raw conversation text**. It only stores:
- pseudonymous user identifiers
- emotional state vectors (`[d, sh, s, a]`)
- minimal conversation metadata (title + timestamps)

## Features
- Async FastAPI + SQLAlchemy + PostgreSQL
- `pgvector` emotional state storage
- JWT auth (signup/login/logout)
- Conversation management with optional `conversation_id`
- Mathematical vector state updates with clipping and decay
- SSE token streaming endpoint
- OpenAI API integration via `httpx`

## Emotional Model

State vector:

`V = [d, sh, s, a]`

Update rule per message:

`V_next = (1 - lambda) * V_current + alpha * S`

Signal:

`Si = w1 * sentiment + w2 * negativity + w3 * keyword_score`

Then clip each component to `[-1, 1]`.

## Project Structure

```
app/
  main.py
  config.py
  database.py
  models.py
  schemas.py
  routers/
    auth.py
    chat.py
  services/
    auth.py
    emotion.py
    llm.py
    safety.py
```

## Setup

1. Create virtual environment and install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy env file:

```bash
cp .env.example .env
```

3. Ensure PostgreSQL is running and reachable via `DATABASE_URL`.

4. Run API:

```bash
uvicorn app.main:app --reload
```

On startup, the app will:
- create DB if it doesn't exist
- enable extension `vector`
- create tables automatically

## API Endpoints

### Auth
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`

### Chat
- `POST /chat/message` - accepts `{ message, conversation_id? }`
- `GET /chat/stream?message=...&conversation_id=...` - SSE response
- `GET /chat/conversations`
- `GET /chat/state`

### Utility
- `GET /health`

## Privacy/Security Notes
- No plaintext conversation history is persisted.
- No raw user messages are written to DB.
- Users are identified with pseudonymous HMAC IDs.
- Passwords hashed with bcrypt.

## Streaming Example

```bash
curl -N -H "Authorization: Bearer <token>" \
  "http://127.0.0.1:8000/chat/stream?message=I%20feel%20overwhelmed"
```
