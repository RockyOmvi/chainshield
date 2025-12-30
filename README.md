# ChainShield

AI-Powered Crypto Security & Transaction Intelligence Platform

## Quick Start

```bash
# Start services
docker-compose up -d

# Run migrations
cd backend
alembic upgrade head

# Seed database
python scripts/seed_database.py

# Start server
uvicorn app.main:app --reload
```

## API Documentation

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Features

- 🔍 Wallet risk analysis
- 📊 Transaction monitoring
- 🤖 AI-powered explanations
- 🚨 Real-time alerts
- 📈 Multi-chain support

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic v2
- **Database**: PostgreSQL, Redis
- **Blockchain**: Multi-provider (Alchemy, Infura, Public RPC)
- **Auth**: JWT + API Key
- **DevOps**: Docker, GitHub Actions

## Environment Variables

See `.env.example` for configuration options.

## Testing

```bash
cd backend
pytest -v --cov=app
```

## License

MIT
