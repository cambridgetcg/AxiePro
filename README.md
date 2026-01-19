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

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL (or Docker)
- Redis (or Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your database credentials and API keys

# Run database migrations
alembic upgrade head

# Start the server
uvicorn src.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template (optional - defaults work for local dev)
cp .env.example .env.local

# Start the development server
npm run dev
```

The frontend runs on `http://localhost:3000` and automatically proxies API requests to the backend at `http://localhost:8000`.

## Environment Variables

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/axie_explorer

# Redis Cache
REDIS_URL=redis://localhost:6379

# External APIs
GOLDRUSH_API_KEY=your_goldrush_key
SKYMAVIS_API_KEY=your_skymavis_key

# App Settings
DEBUG=true
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# CORS (comma-separated domains, or * for development)
CORS_ORIGINS=*
```

### Frontend (.env.local)

```env
# Leave empty to use Next.js proxy (recommended for local development)
NEXT_PUBLIC_API_URL=

# For production deployments, set to your backend URL:
# NEXT_PUBLIC_API_URL=https://api.axiepro.io
```

## Production Deployment

### Frontend (Vercel)

1. Connect your repository to Vercel
2. Set environment variable in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL` = Your deployed backend URL (e.g., `https://api.axiepro.io`)

### Backend (AWS)

The infrastructure is managed via AWS CDK. See [infrastructure/README.md](infrastructure/README.md) for deployment instructions.

Key services:
- **App Runner** - Hosts the FastAPI backend
- **Aurora PostgreSQL** - Database
- **ElastiCache Redis** - Caching
- **Lambda** - Scheduled jobs (price ingestion, deal detection)

## License

MIT
