"""
Axie Ronin Explorer API

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.models import init_db, close_db
from src.api.routes import axies, market, breeding, wallets, valuation, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    print(f"Network: {settings.ronin_network} (Chain ID: {settings.ronin_chain_id})")

    # Initialize database (creates tables if they don't exist)
    # This ensures auth_challenges and other tables exist
    # In production, consider using Alembic migrations for more control
    try:
        await init_db()
        print("Database tables initialized.")
    except Exception as e:
        print(f"Warning: Database initialization error: {e}")
        # Continue anyway - tables might already exist

    yield

    # Shutdown
    await close_db()
    print("Shutdown complete.")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title="Axie Ronin Explorer API",
    description="""
    API for exploring the Ronin blockchain and analyzing Axie Infinity data.

    ## Features

    * **Axie Search** - Search and filter Axies by class, purity, parts, and price
    * **Market Data** - Get listings, sales history, floor prices, and market stats
    * **Breeding Simulator** - Calculate breeding outcomes and find optimal pairs
    * **Wallet Tracking** - Track wallet holdings and trading history
    * **Gene Analysis** - Parse and analyze Axie genes
    * **Valuation** - Fair market value estimation using hedonic pricing models
    * **Deal Detection** - Identify undervalued listings and snipe opportunities

    ## Authentication

    Most endpoints are public. Rate limiting applies:
    * Anonymous: 100 requests/minute

    **Wallet Authentication** (for write operations):
    1. POST `/api/v1/auth/challenge` - Get a challenge message
    2. Sign the message with your Ronin wallet
    3. POST `/api/v1/auth/verify` - Submit signature to get JWT token
    4. Use token in Authorization header: `Bearer <token>`
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
# In production, set CORS_ORIGINS env var to restrict to specific domains
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Check if the API is running."""
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(axies.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(breeding.router, prefix="/api/v1")
app.include_router(wallets.router, prefix="/api/v1")
app.include_router(valuation.router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """API root - returns basic info."""
    return {
        "name": "Axie Ronin Explorer API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
