# Squared

Split bills the fair way. Snap a receipt, let Squared read the line items, assign
who had what, and it works out **exact tax and tip per person** — then nets everyone
down to the **fewest possible payments** and keeps balances in sync in real time.

## Features

- **Receipt OCR** — Tesseract pipeline extracts line items; you review and correct before splitting.
- **Exact tax & tip** — proportional allocation with cent-exact rounding (no lost pennies).
- **Smart settle-up** — a greedy debt-simplification algorithm collapses who-owes-whom into a
  minimal set of transfers, and shows how many transactions it saved.
- **Real-time sync** — balances update live across everyone in a group over WebSockets.
- **Reminders** — idempotent, scheduled nudges to settle outstanding debts.
- **Pay your way** — deep links to Venmo / PayPal / Cash App (Squared tracks, it doesn't move money).

## Tech

- **Backend:** FastAPI (Python), Postgres, SQLAlchemy + Alembic
- **Frontend:** React + TypeScript (Vite)
- **Auth:** Google OAuth2 → app JWT
- **Real-time:** WebSockets · **Scheduling:** APScheduler

## Project layout

```
backend/    FastAPI app, models, services (allocation, settlement, ocr), tests
frontend/   React + TypeScript client
docker-compose.yml   local Postgres
```

## Getting started

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in values as you go

# Run the API (works immediately — health + compute endpoints need no database)
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

Run the tests:

```bash
cd backend && source .venv/bin/activate && pytest
```

### Database (for the persistent features)

```bash
docker compose up -d db
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /compute to the backend)
```

## Status

Early build. The core money logic — exact tax/tip allocation and greedy debt
simplification — is implemented and unit-tested, and exposed via the `/compute`
endpoints with a small demo in the frontend. Auth, groups, persistence, OCR, and
real-time sync are being layered on next.
