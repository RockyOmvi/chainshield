# 🛡️ ChainShield

> **Enterprise AI-Powered Crypto Security & Transaction Intelligence Platform**  
> Real-time blockchain wallet profiling, OFAC SDN sanctions enforcement, transaction monitoring, and explainable AI risk scoring.

---

## 📋 Table of Contents
- [Overview](#-overview)
- [Architecture & Tech Stack](#-architecture--tech-stack)
- [Prerequisites](#-prerequisites)
- [Environment Configuration](#-environment-configuration)
- [Docker Setup & Image Creation](#-docker-setup--image-creation)
  - [1. Building Individual Docker Images](#1-building-individual-docker-images)
  - [2. Running the Complete Stack with Docker Compose](#2-running-the-complete-stack-with-docker-compose)
  - [3. Database Migrations & Seeding in Docker](#3-database-migrations--seeding-in-docker)
  - [4. Useful Docker Commands & Troubleshooting](#4-useful-docker-commands--troubleshooting)
- [Local Development Setup (Without Docker)](#-local-development-setup-without-docker)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [API Documentation & Health Check](#-api-documentation--health-check)
- [Testing & Validation](#-testing--validation)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## 🔍 Overview

ChainShield provides real-time risk intelligence for blockchain transactions and wallet addresses via a **3-Layer Defense Engine**:
1. **Layer 1: Deterministic Rules & Sanctions** — Instant blocklist detection matching **OFAC SDN** lists (including IFSR, SDGT programs), mixer addresses, and known malicious exploit contracts.
2. **Layer 2: Behavioral Heuristics** — On-chain behavioral pattern detection (peeling chains, high-velocity structuring, sudden drainage, dormant reactivation).
3. **Layer 3: Machine Learning Anomaly Detection** — Ensemble models (RandomForest, XGBoost, Isolation Forest) with **SHAP explainability** providing human-readable risk breakdowns.

---

## 🛠️ Architecture & Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Backend API** | FastAPI, Python 3.11+, Pydantic v2 | High-performance asynchronous REST API |
| **Frontend UI** | React 18, TypeScript, Vite, Vanilla CSS | Interactive glassmorphic risk dashboard & landing page |
| **Database** | PostgreSQL 16 (asyncpg, SQLAlchemy 2.0) | Relational database for accounts, audits, and scan records |
| **Caching & Rate Limiting** | Redis 7 (alpine) | Sliding-window rate limiting & risk score caching |
| **ML / Analytics** | Scikit-learn, XGBoost, Joblib | Pre-trained risk scoring and anomaly classifiers |
| **Blockchain Client** | Web3.py, Public RPC / Alchemy | Multi-provider Ethereum & EVM network connectors |
| **Containerization** | Docker, Multi-stage Dockerfiles, Compose | Production-ready lightweight containers |

---

## ⚙️ Prerequisites

Ensure the following tools are installed on your system:
- [Docker](https://docs.docker.com/get-docker/) (v24.0+) & [Docker Compose](https://docs.docker.com/compose/) (v2.20+)
- **Python 3.11+** (for native backend development)
- **Node.js 18+** & **npm 9+** (for native frontend development)
- **Git**

---

## 🔑 Environment Configuration

ChainShield uses environment files to configure database credentials, blockchain RPC endpoints, and security keys.

### 1. Root & Backend Environment
Create the `.env` file from the provided template:

```bash
# In project root
cp .env.example .env
```

Key variables configured in `.env`:

```env
# Application
APP_NAME=chainshield
APP_ENV=development
DEBUG=true
SECRET_KEY=generate-a-secure-secret-key-for-production
API_V1_PREFIX=/api/v1

# Server
HOST=0.0.0.0
PORT=8000

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://chainshield:chainshield_dev@localhost:5432/chainshield

# Redis
REDIS_URL=redis://localhost:6379/0

# Security / JWT
JWT_SECRET_KEY=generate-a-secure-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Blockchain RPC (Ethereum Mainnet / Testnets)
PUBLIC_RPC_URL=https://ethereum-rpc.publicnode.com
ETHERSCAN_API_KEY=your_optional_etherscan_key

# Features
FEATURE_AI_EXPLANATIONS=true
FEATURE_GRAPH_ANALYSIS=true
FEATURE_REAL_TIME_ALERTS=true
```

*(When running inside Docker Compose, services communicate via their Docker network service names `postgres:5432` and `redis:6379`, configured automatically in `docker-compose.yml`.)*

---

## 🐳 Docker Setup & Image Creation

### 1. Building Individual Docker Images

You can build the backend and frontend container images separately using their respective multi-stage Dockerfiles.

#### Build the Backend Image
The backend image uses a 2-stage build (Builder stage compiles wheels, Runtime stage creates a non-root secure execution environment):

```bash
# Build backend image
docker build -t chainshield-backend:latest ./backend

# Build with custom build arguments or target
docker build -t chainshield-backend:v1.0.0 ./backend
```

#### Build the Frontend Image
The frontend image uses a 2-stage build (Node 20 compiles the Vite/TypeScript bundle, Nginx Alpine serves the static assets and proxies `/api/`):

```bash
# Build frontend image
docker build -t chainshield-frontend:latest ./frontend

# Build with custom tag
docker build -t chainshield-frontend:v1.0.0 ./frontend
```

---

### 2. Running the Complete Stack with Docker Compose

The easiest way to orchestrate all services (PostgreSQL, Redis, Backend API, and Frontend UI) is using Docker Compose.

#### Start All Services (Build + Detached Mode)
```bash
docker compose up -d --build
```

This launches:
- `chainshield-postgres`: PostgreSQL 16 on port `5432`
- `chainshield-redis`: Redis 7 on port `6379`
- `chainshield-backend`: FastAPI backend on port `8000`
- `chainshield-frontend`: React dashboard on port `5173`

#### Check Running Containers
```bash
docker compose ps
```

#### View Live Logs
```bash
# Follow logs for all services
docker compose logs -f

# Follow logs for backend only
docker compose logs -f backend

# Follow logs for frontend only
docker compose logs -f frontend
```

---

### 3. Database Migrations & Seeding in Docker

Once the containers are running and healthy, apply database migrations and seed initial administrative/test users:

```bash
# 1. Apply Alembic database migrations
docker compose exec backend alembic upgrade head

# 2. Seed initial data (default users, risk rule definitions, test accounts)
docker compose exec backend python scripts/seed_database.py
```

> **Default Seed Credentials:**
> - Admin: `admin@chainshield.io` / `ChainShield2024!`
> - Analyst: `analyst@chainshield.io` / `Analyst123!`
> - Regular User: `user@chainshield.io` / `User123!`
> - Enterprise: `enterprise@chainshield.io` / `Enterprise123!`

---

### 4. Useful Docker Commands & Troubleshooting

| Action | Command |
|---|---|
| **Stop all containers** | `docker compose stop` |
| **Start stopped containers** | `docker compose start` |
| **Stop and remove containers & networks** | `docker compose down` |
| **Clean teardown (remove volumes/database data)** | `docker compose down -v` |
| **Rebuild a single service without cache** | `docker compose build --no-cache backend` |
| **Open a shell inside backend container** | `docker compose exec -it backend /bin/bash` |
| **Open a PostgreSQL interactive shell (`psql`)** | `docker compose exec -it postgres psql -U chainshield -d chainshield` |
| **Open a Redis interactive shell (`redis-cli`)** | `docker compose exec -it redis redis-cli` |

---

## 💻 Local Development Setup (Without Docker)

If you prefer running services directly on your host machine:

### 1. Start Infrastructure (PostgreSQL & Redis)
You can quickly run just the database and cache using Docker while developing code locally:
```bash
docker compose up -d postgres redis
```

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Seed the database**:
   ```bash
   python scripts/seed_database.py
   ```

6. **Start the development server (with hot reload)**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

Backend is now running at **`http://localhost:8000`**.

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

Frontend is now accessible at **`http://localhost:5173`**.

4. **Other Frontend Commands**:
   ```bash
   # Run TypeScript check & build for production
   npm run build

   # Preview the production build locally
   npm run preview
   ```

---

## 📖 API Documentation & Health Check

Once the backend is running, interactive API documentation is automatically available:

| Resource | URL |
|---|---|
| **Swagger UI (Interactive API Docs)** | [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs) |
| **ReDoc (Detailed Specification)** | [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc) |
| **System Health Check** | [http://localhost:8000/health](http://localhost:8000/health) |
| **Frontend UI** | [http://localhost:5173](http://localhost:5173) |

### Key API Endpoints
- `POST /api/v1/auth/login` — Authenticate and receive JWT access token.
- `POST /api/v1/wallet/analyze` — Analyze wallet risk score, sanctions, and anomalies.
- `GET /api/v1/account/quota` — Retrieve real-time tier quota telemetry (used/remaining).
- `POST /api/v1/tx/analyze` — Evaluate transaction parameters and recipient address.

---

## 🧪 Testing & Validation

### Run Backend Unit & Integration Tests
```bash
cd backend
pytest -v --cov=app
```

### Testing Sanctioned Entities (OFAC SDN Validation)
To verify OFAC SDN sanctions enforcement, submit a scan for a known sanctioned address:

- **Entity**: Arash Estaki Alivand (OFAC SDN Programs: `IFSR`, `SDGT`)
- **Ethereum Address**:
  ```text
  0x532b77b33a040587e9fd1800088225f99b8b0e8a
  ```
- **Expected Result**:
  - Risk Level: **CRITICAL / SEVERE**
  - Score: **98/100**
  - Sanction Alert: Direct match with OFAC SDN list under `IFSR` and `SDGT` programs. Immediate transaction blocking recommended.

---

## 📁 Project Structure

```text
chainshield/
├── .env.example              # Global environment template
├── docker-compose.yml        # Development multi-container orchestration
├── docker-compose.staging.yml# Staging environment orchestration
│
├── backend/
│   ├── Dockerfile            # Multi-stage production Python container
│   ├── requirements.txt      # Python dependencies
│   ├── alembic.ini           # Alembic migration configuration
│   ├── alembic/              # Database migration revisions
│   ├── scripts/
│   │   └── seed_database.py  # DB seeder for users and risk thresholds
│   ├── models/               # Pre-trained ML models & scaler artifacts
│   └── app/
│       ├── main.py           # FastAPI application entrypoint
│       ├── api/              # API router endpoints (v1)
│       │   └── v1/           # auth, wallet, account, risk, admin
│       ├── core/             # Configuration, security, database engine
│       ├── models/           # SQLAlchemy database entities
│       ├── schemas/          # Pydantic request/response schemas
│       └── services/
│           ├── blockchain/   # Web3 provider & client connector
│           └── risk/         # 3-Layer Risk Engine & OFAC Sanctions
│
└── frontend/
    ├── Dockerfile            # Multi-stage production Nginx container
    ├── nginx.conf            # Nginx reverse proxy configuration
    ├── package.json          # Node dependencies and scripts
    ├── vite.config.ts        # Vite build configuration
    └── src/
        ├── main.tsx          # React application root & router
        ├── index.css         # Design system & dark glassmorphism styles
        ├── pages/
        │   ├── Landing.tsx   # Interactive landing page with live scanner
        │   └── AdminDashboard.tsx # Platform administration
        └── components/
            └── Dashboard.tsx # Main risk analysis dashboard & telemetry
```

---

## 📄 License

This project is licensed under the **MIT License** - see the LICENSE file for details.
