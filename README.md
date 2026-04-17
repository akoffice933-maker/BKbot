# StatBet Bot

Telegram bot for sports analytics, match probability estimation, and hedge calculation. The project is built on `aiogram 3`, uses PostgreSQL and Redis, and keeps database schema changes under Alembic migrations.

## Status

- Hedge calculator is implemented and covered by tests.
- Match analysis and predictions currently use placeholder model output.
- Live tracking, paper trading, and model statistics are scaffolded but not complete.

## Features

- `/start` registers a user and shows the project disclaimer.
- `/matches` returns upcoming matches with placeholder probabilities.
- `/analyze` returns model-style output with factors and confidence.
- `/calc_hedge` runs an FSM-based hedge calculator.
- `/track`, `/untrack`, `/status`, `/paper`, `/stats` are present as stubs for future work.
- Polymarket foundation is added for read-only market discovery and pricing.

## Hedge Calculator

The bot supports three hedge-related calculations:

- `Full Hedge`: covers the opposite outcome completely.
- `Partial Hedge`: covers a configurable share of the original exposure.
- `Lock Profit`: calculates the amount required to lock a fixed profit profile.

The service also checks whether the two odds create an arbitrage opportunity.

## Architecture

The codebase is organized into small layers:

- `src/statbet_bot/bot.py` starts the bot, initializes infrastructure, and handles shutdown.
- `src/statbet_bot/config.py` loads environment variables via `pydantic-settings`.
- `src/statbet_bot/database.py` opens PostgreSQL and Redis connections and validates that Alembic migrations were applied.
- `src/statbet_bot/handlers/` contains Telegram command handlers and FSM flow.
- `src/statbet_bot/services/` contains business logic for hedge calculations and predictions.
- `src/statbet_bot/services/polymarket.py` provides read-only access to Polymarket Gamma and CLOB APIs.
- `src/statbet_bot/models.py` contains hedge math primitives and a placeholder prediction model.
- `alembic/` contains schema migrations and Alembic runtime configuration.
- `tests/` contains unit and integration-style tests for core domain logic.

## Tech Stack

- Python 3.11+
- aiogram 3.x
- PostgreSQL
- Redis
- Alembic
- Pydantic / pydantic-settings
- pandas, scikit-learn, xgboost, shap
- httpx
- pytest / pytest-asyncio

## Repository Layout

```text
.
├── alembic/
├── src/statbet_bot/
│   ├── handlers/
│   ├── services/
│   ├── utils/
│   ├── bot.py
│   ├── config.py
│   ├── database.py
│   └── models.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── setup.py
```

## Requirements

Before starting the bot you need:

- Python installed
- PostgreSQL running
- Redis running
- A valid Telegram bot token from `@BotFather`

## Installation

### Option 1: Editable install with pip

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

### Option 2: Poetry

```powershell
poetry install
```

### Option 3: Infrastructure only via Docker

```powershell
docker-compose up -d
```

## Configuration

Create `.env` from `.env.example` and fill in real values:

```env
TELEGRAM_TOKEN=your_real_telegram_token
DATABASE_URL=postgresql://user:password@localhost/statbet
REDIS_URL=redis://localhost:6379
API_FOOTBALL_KEY=
ODDS_API_KEY=
POLYMARKET_HOST=https://clob.polymarket.com
POLYMARKET_CHAIN_ID=137
```

Important:

- `.env` should not be committed.
- The default database credentials in the example must match your actual PostgreSQL setup.

## Database Migrations

Schema management is Alembic-only.

Apply migrations before starting the bot:

```powershell
alembic upgrade head
```

If migrations were not applied, the bot fails fast on startup with an explicit schema error instead of creating tables implicitly.

## Running the Bot

If the package is installed in editable mode:

```powershell
statbet-bot
```

If you want to run directly from the repository:

```powershell
$env:PYTHONPATH = "src"
python -m statbet_bot.bot
```

## Testing

Run the test suite:

```powershell
python -m pytest -q
```

Current local status:

- Polymarket service tests are included in the local suite.

## Polymarket

The project now includes the foundation for a read-only Polymarket integration.

Current Phase 0 + 1 scope:

- Search markets through the Gamma API
- Fetch a market by slug or ID
- Fetch CLOB prices for token IDs
- Convert Polymarket share prices to decimal odds and back

Trading, wallet management, and order placement are intentionally out of scope for the current iteration.

## Current Limitations

- Prediction output is placeholder data, not a trained production model.
- Several bot commands are still stubs.
- README documents the project accurately, but deployment still depends on valid local PostgreSQL credentials.
- The bot currently targets polling mode only.

## Roadmap

- Integrate a real sports data provider.
- Replace placeholder prediction logic with trained inference pipeline.
- Implement live match tracking and user subscriptions.
- Add real paper-trading workflows and bet settlement.
- Add CI, linting, and deployment automation.
- Add `/pm` bot handlers and cross-hedge workflows for Polymarket.

## Disclaimer

This project is for analytics and experimentation. It is not financial advice, not betting advice, and not a solicitation to place wagers. Users are responsible for their own decisions and compliance with local laws and bookmaker rules.
