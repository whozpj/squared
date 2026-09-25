[Squared - Check it out!](https://squared-ocr.netlify.app/login)

# Squared

Split bills the fair way. Snap a receipt, let Squared read the line items, assign who had
what, and it works out **exact tax and tip per person** — then nets everyone down to the
**fewest possible payments** and keeps balances in sync in real time.

**Live:** https://squared-ocr.netlify.app

## Features

- **Receipt OCR** — upload a photo and Squared extracts the line items, subtotal, tax, tip and
  total. You review and assign items before anything is saved. On a 30-receipt benchmark (half
  degraded with skew, blur, sensor noise and thermal fade) it reaches **~98% line-item F1** and
  **~91% field accuracy**, and auto-reconciles ~87%. Anything that doesn't add up is flagged for
  review instead of being guessed.
- **Exact tax & tip** — tax and tip are split in proportion to what each person ordered, with
  largest-remainder rounding so every share is cent-exact and sums to the bill total.
- **Smart settle-up** — a greedy debt-simplification algorithm collapses who-owes-whom into the
  fewest transfers (typically ~40% fewer than pairwise payoff) and shows exactly how many it saved.
- **One-tap payments** — each transfer links straight to the recipient's Venmo, PayPal or Cash App
  with the amount prefilled, or opens a prefilled email. Squared tracks payments; it never moves money.
- **Real-time sync** — balances, bills and receipt scans update live for everyone in a group over
  WebSockets.
- **Reminders** — scheduled, idempotent nudges (in-app and email) so each debtor is reminded once
  per week, never twice. Creditors can also send a reminder on demand.
- **Groups & invites** — create a group, share an invite code, and friends join in one step.
- **iOS app** — a native SwiftUI client with the same features, talking to the same API.

## Tech

- **Backend:** FastAPI (Python), PostgreSQL, SQLAlchemy + Alembic, APScheduler, WebSockets
- **OCR:** Tesseract + OpenCV preprocessing, custom receipt parser and reconciliation engine
- **Frontend:** React + TypeScript (Vite), Framer Motion
- **iOS:** SwiftUI (XcodeGen project)
- **Auth:** email sign-in with JWT sessions
- **Email:** Resend (optional)
- **Infra:** Docker, Render (API), Neon (Postgres), Netlify (web)

## How it works

1. **Scan** — the receipt image is preprocessed (deskew, upscale, adaptive threshold) and read by
   Tesseract. Both the raw and cleaned images are OCR'd and the parser keeps whichever result
   reconciles (items ≈ subtotal, subtotal + tax + tip ≈ total).
2. **Split** — each item is assigned to one or more people; shares are computed exactly and stored
   as a single source of truth per bill, with a check that they always sum to the total.
3. **Settle** — balances are derived from bills and confirmed payments, then the greedy algorithm
   repeatedly matches the largest creditor with the largest debtor, producing at most *n − 1* transfers.

## Project layout

```
backend/    FastAPI app — models, services (allocation, settlement, ocr), workers, tests
frontend/   React + TypeScript web client
ios/        Native SwiftUI app
docker-compose.yml   local Postgres
render.yaml          backend deploy blueprint
netlify.toml         frontend deploy config
```

## Running locally

### Database

```bash
docker compose up -d db          # Postgres on localhost:5434
```

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt  # also needs the tesseract binary: brew install tesseract
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

Interactive API docs: http://localhost:8001/docs

Tests (60, including a real image → OCR → reconcile end-to-end test):

```bash
cd backend && source .venv/bin/activate && pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173, proxies API calls to :8001
```

### iOS

```bash
cd ios
xcodegen generate                # creates Squared.xcodeproj from project.yml
open Squared.xcodeproj           # run on an iPhone simulator (⌘R)
```

The app talks to `http://localhost:8001` (see `API.swift`).

### OCR benchmark

```bash
cd backend && source .venv/bin/activate
python scripts/gen_ocr_corpus.py ocr_corpus   # renders 30 labeled receipts with real-world degradations
python -m app.services.ocr.eval ocr_corpus     # reports line-item F1, field accuracy, reconcile rate
```

## Deploying

Squared runs entirely on free tiers: **Neon** (Postgres), **Render** (API), **Netlify** (web).

1. **Database** — create a Neon project and copy its connection string.
2. **API** — on Render, choose *New → Blueprint* for this repo (uses `render.yaml`). Set
   `DATABASE_URL` to the Neon string and `CORS_ORIGINS` to `["https://<your-site>.netlify.app"]`.
   The Docker image bundles Tesseract and runs migrations on boot.
3. **Web** — import the repo on Netlify (uses `netlify.toml`) and set `VITE_API_BASE` to the
   Render URL.

Optional: set `RESEND_API_KEY` on Render to send reminder emails.
