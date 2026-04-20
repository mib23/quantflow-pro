# QuantFlow Pro

[中文说明](./README.md)

QuantFlow Pro is a full-stack monorepo built to demonstrate how I design and deliver complex business software, especially systems that combine product thinking, frontend experience, backend architecture, and long-term maintainability.

This repository is not just a UI mock. It already brings core trading-platform workflows into one codebase: authentication, account overview, order entry, risk events, strategy research, async backtesting, runtime deployment, realtime updates, database migrations, tests, and containerized local setup.

## What This Project Is For

- A public portfolio project for GitHub and freelance client conversations
- A realistic foundation for a quantitative trading platform
- A showcase of engineering depth, not a one-off demo page

## What It Already Demonstrates

### 1. Real business-domain decomposition

The frontend is split into clear domains such as `auth`, `dashboard`, `trading`, `strategy`, and `risk`. The backend mirrors that with separate modules for authentication, accounts, orders, backtests, runtime operations, market data, and risk control. This makes the project easier to scale, test, and extend.

### 2. Actual full-stack integration

This is not “frontend with fake data plus a placeholder backend”. The repository already includes:

- A React + TypeScript + Vite frontend
- A FastAPI + PostgreSQL + Redis backend
- Alembic database migrations
- WebSocket realtime channels
- RQ async jobs for background work
- Docker Compose for full local orchestration

### 3. Workflows close to real trading software

The current version covers several flows that are useful for showing technical capability:

- Login and session restoration
- Account, positions, equity, and PnL overview
- Order placement, cancellation, order status, and executions
- Risk rules, risk summaries, and event streams
- Strategy list, versioning, async backtests, result inspection, and report download
- Runtime instance creation, start, stop, and restart
- Live deployment approval, logs, alerts, related orders, and related risk events

### 4. Engineering discipline, not just visual polish

The project already contains several pieces that demo repositories often skip:

- Architecture and boundary documentation
- API and event contracts
- Data model planning and migration history
- Backend test coverage
- Local seed data and demo accounts
- An optional Alpaca integration path

## Tech Stack

### Frontend

- `React 19 + TypeScript + Vite`
- `React Router` for application routing
- `TanStack Query` for server-state management
- `Zustand` for session state
- `React Hook Form + Zod` for form handling and validation
- `Recharts` for equity curves and result visualizations
- Domain-based folder structure for maintainable growth

### Backend

- `FastAPI` for REST and realtime interfaces
- `SQLAlchemy + Alembic` for data access and schema evolution
- `PostgreSQL` for core business data
- `Redis` for cache, realtime support, and queues
- `RQ` for background jobs such as backtesting
- `BrokerAdapter` abstraction for future broker integrations

### Architecture

- Full-stack monorepo for faster coordination
- Modular monolith approach for speed without losing structure
- Clear separation between page logic, data fetching, and domain concerns
- REST for configuration and queries, WebSocket for live updates
- Trading, backtesting, and runtime operations designed as separate concerns

## Main Product Areas

### Dashboard

- Account equity, cash, buying power, and daily PnL
- Equity curve, positions table, and recent risk alerts
- Backend-driven aggregated data with realtime refresh hooks

### Trade

- Market snapshot, account overview, positions, active orders, and executions
- Real order submission and cancellation requests
- Integrated risk-event feed for a realistic trading workspace

### Strategy

- Strategy creation, versioning, and version cloning
- Async backtest submission, cancel, and retry flow
- Result viewing and report download
- Runtime deployment, start/stop/restart controls, and operational visibility
- Live approval flow to reflect production-oriented design thinking

### Risk

- Risk summary, rule list, rule detail, and version history
- Rule activation and deactivation
- Recent triggered events and hard-limit overview

## Repository Structure

```text
docs/
  architecture/   # architecture, ER diagrams, API contracts
  plan/           # phased delivery plans
server/
  app/
    api/
    core/
    integrations/
    modules/
    tests/
  migrations/
src/
  app/
  entities/
  features/
  shared/
  widgets/
```

## Quick Start

### Option 1: Start the full stack with Docker

```powershell
docker compose up --build
```

Default local endpoints:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health/liveness`

### Option 2: Run frontend and backend separately

Frontend:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Backend:

```powershell
cd server
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Local Demo Notes

- In `local` and `test` environments, the backend bootstraps minimum demo data automatically
- If `QF_ALPACA_*` variables are provided, the app tries to use Alpaca paper endpoints first
- Without Alpaca credentials, it falls back to normalized demo responses for easier local showcasing

Demo accounts:

- `alex@quantflow.local / quantflow-demo`
- `trader@quantflow.local / quantflow-demo`

## Verification Commands

Frontend:

```powershell
npm run check
npm run build
```

Backend:

```powershell
cd server
pytest
```

## Documentation

- [Architecture decisions](./docs/architecture/phase-0-decisions.md)
- [Module boundaries](./docs/architecture/module-boundaries.md)
- [ER diagram](./docs/architecture/er-diagram.md)
- [API and event contracts](./docs/architecture/api-contracts.md)
- [Full implementation plan](./docs/plan/quantflow-fullstack-implementation-plan.md)

## What Kind of Work This Represents

If you need someone to build admin systems, trading tools, operational dashboards, data-heavy workspaces, strategy platforms, or other complex internal products, this repository is a practical sample of how I approach that work. It highlights:

- information architecture for complex business domains
- strong frontend and backend coordination
- the ability to turn a prototype into a scalable system foundation
- attention to testing, migrations, deployment, and long-term maintenance

## Chinese Version

For the Chinese version, see [README.md](./README.md).
