# Axie Ronin Explorer

A blockchain explorer and analytics platform for the Ronin network, focused on Axie Infinity trading analysis, trait evaluation, and breeding strategy optimization.

## Project Goals

1. **Trading Analysis** - Track Axie sales, identify undervalued assets, spot market trends
2. **Trait Valuation** - Understand which body parts, genes, and combinations command premium prices
3. **Breeding Optimizer** - Calculate breeding costs vs expected offspring value
4. **Portfolio Tracking** - Monitor wallet holdings and P&L over time

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL + TimescaleDB (time-series)
- **Cache**: Redis
- **Task Queue**: Celery + Redis

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Charts**: Recharts / TradingView Lightweight Charts
- **State**: TanStack Query

### Data Sources
- **Moralis** - NFT metadata, wallet balances, token transfers
- **Sky Mavis GraphQL** - Axie traits, marketplace listings, genes
- **Chainstack/Alchemy** - Direct RPC for on-chain queries

## Project Structure

```
Ronin_API/
├── README.md
├── docs/
│   ├── 01-architecture.md      # System architecture overview
│   ├── 02-database-schema.md   # Database design & ERD
│   ├── 03-api-specification.md # REST API endpoints
│   ├── 04-frontend-design.md   # UI components & pages
│   └── 05-implementation.md    # Phased implementation plan
├── backend/
│   ├── src/
│   │   ├── api/                # FastAPI routes
│   │   ├── services/           # Business logic
│   │   ├── models/             # SQLAlchemy models
│   │   └── utils/              # Helpers (gene parser, etc.)
│   ├── tests/
│   ├── requirements.txt
│   └── docker-compose.yml
└── frontend/
    ├── src/
    │   ├── app/                # Next.js App Router pages
    │   ├── components/         # React components
    │   ├── hooks/              # Custom hooks
    │   └── lib/                # API clients, utilities
    └── package.json
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/01-architecture.md) | System design, data flow, infrastructure |
| [Database Schema](docs/02-database-schema.md) | Tables, relationships, indexes |
| [API Specification](docs/03-api-specification.md) | REST endpoints, request/response formats |
| [Frontend Design](docs/04-frontend-design.md) | Pages, components, user flows |
| [Implementation Plan](docs/05-implementation.md) | Phased roadmap with deliverables |

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

```env
# Backend (.env)
DATABASE_URL=postgresql://user:pass@localhost:5432/axie_explorer
REDIS_URL=redis://localhost:6379
MORALIS_API_KEY=your_key
SKYMAVIS_API_KEY=your_key

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## License

MIT
