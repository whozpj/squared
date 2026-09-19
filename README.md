# Squared

Split bills the fair way. Snap a receipt, let Squared read the line items, assign
who had what, and it works out **exact tax and tip per person** — then nets everyone
down to the **fewest possible payments** and keeps balances in sync in real time.

## Features

- **Receipt OCR** — Tesseract pipeline extracts line items; you review and correct before splitting.
  On a 30-receipt benchmark (half degraded with skew, blur, sensor noise and thermal fade) it hits
  **~98% line-item F1** and **~91% field accuracy** (subtotal/tax/tip/total). It auto-reconciles
  ~87%; the rest are flagged for review rather than emitted wrong — by design it never guesses a
  number that doesn't add up. (Reproduce: `python scripts/gen_ocr_corpus.py ocr_corpus && python -m app.services.ocr.eval ocr_corpus`.)
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
ios/        Native SwiftUI app (talks to the same backend)
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

### iOS app (SwiftUI)

The `ios/` folder is a native SwiftUI app that hits the same backend. The Xcode
project is generated with [XcodeGen](https://github.com/yonaskolb/XcodeGen):

```bash
cd ios
xcodegen generate      # creates Squared.xcodeproj from project.yml
open Squared.xcodeproj  # then run on an iPhone simulator (⌘R)
```

It expects the backend at `http://localhost:8001` (see `API.swift`). Local HTTP is
allowed via `NSAllowsLocalNetworking` in `Info.plist`.

## Status

Early build. The core money logic — exact tax/tip allocation and greedy debt
simplification — is implemented and unit-tested, and exposed via the `/compute`
endpoints with a small demo in the frontend. Auth, groups, persistence, OCR, and
real-time sync are being layered on next.
