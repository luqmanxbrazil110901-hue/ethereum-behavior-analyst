# Ethereum Behavior Analyst

Real-time Ethereum wallet classification and scoring system. Monitors wallet addresses, classifies them by type/behavior, and presents results in a web dashboard. All blockchain data comes from a self-hosted Geth node.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Access to Geth node at `100.100.0.126:8547` (must be on the `100.100.0.0/21` subnet)

### Deploy

```bash
# Clone and start
git clone https://github.com/YOUR_USERNAME/ethereum-behavior-analyst.git
cd ethereum-behavior-analyst

# Copy and edit environment variables (optional - defaults work if on subnet)
cp .env.example .env

# Start all services
docker compose up -d --build
```

That's it. Services will be available at:
- **Dashboard**: http://localhost:3000
- **API**: http://localhost:3001
- **API Docs**: http://localhost:3001/docs

The database schema is automatically created on first run, and known labels (exchanges, bridges, toxic addresses) are automatically seeded.

### Analyze Wallets

```bash
# Analyze a single address
curl -X POST http://localhost:3001/api/wallets/analyze \
  -H "Content-Type: application/json" \
  -d '{"address": "0x28c6c06298d514db089934071355e5743bf21d60"}'

# Bulk analyze
curl -X POST http://localhost:3001/api/wallets/bulk-analyze \
  -H "Content-Type: application/json" \
  -d '{"addresses": ["0x28c6c06298d514db089934071355e5743bf21d60", "0x2910543af39aba0cd09dbb2d50200b3e800a63d2"]}'
```

## Architecture

```
[Geth Node]  -->  [Block Indexer]  -->  [PostgreSQL]  -->  [REST API]  -->  [Dashboard]
                  [On-Demand Fetcher]    [Classification Engine]
```

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React dashboard with Nginx |
| API | 3001 | FastAPI backend |
| PostgreSQL | 5432 | Database |

## Services

- **Block Indexer**: Subscribes to new blocks via WebSocket, indexes transactions for watchlisted addresses
- **Classification Engine**: Scores wallets by type (User/Exchange/Bot/Malicious/Bridge), tier, frequency, purity
- **REST API**: Serves classified wallet data, accepts new addresses for analysis
- **Dashboard**: Table view with sidebar filters, real-time updates, CSV export, manual review workflow

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/wallets | List wallets (with filters, pagination, sorting) |
| GET | /api/wallets/:address | Get wallet detail |
| POST | /api/wallets/analyze | Analyze a single address |
| POST | /api/wallets/bulk-analyze | Analyze multiple addresses |
| PUT | /api/wallets/:address/review | Manual review override |
| GET | /api/wallets/export?format=csv | Export filtered wallets as CSV |
| GET | /api/stats | Dashboard statistics |
| GET | /api/labels | List known labels |
| POST | /api/labels | Add known label |
| DELETE | /api/labels/:address | Remove known label |
| GET | /api/health | Health check |

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| ETH_RPC_HTTP | http://100.100.0.126:8547 | Geth HTTP RPC |
| ETH_RPC_WS | ws://100.100.0.126:8548 | Geth WebSocket |
| ETH_BEACON_API | http://100.100.0.126:5052 | Lighthouse Beacon API |
| POSTGRES_* | ethanalyst/ethanalyst_secret | Database credentials |

## Stopping

```bash
docker compose down        # Stop services (keep data)
docker compose down -v     # Stop and delete database
```
