# Claude Development Instructions

## Project Setup with UV

This project uses `uv` as the package manager for faster dependency resolution and installation.

### Installing UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

### Project Dependencies

All dependencies are defined in `pyproject.toml`. To install:

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project in editable mode with all dependencies
uv pip install -e .

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### Adding New Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Update all dependencies
uv pip compile pyproject.toml -o requirements.txt
```

## Code Style

- Line length: 150 characters
- Formatter: Black
- Import sorter: isort
- Both configured in `pyproject.toml`

Format code:
```bash
black . --line-length 150
isort . --line-length 150
```

## Running Tests

```bash
# Run tests
pytest

# With coverage
pytest --cov=app

# Run type checking
mypy app/
```

## Database

Using SQLite with async SQLAlchemy. Database is created automatically at `./data/gentle_bot.db`.

## OpenRouter API

The bot uses OpenRouter as a gateway to access Google Gemini Flash 2.0:
- Endpoint: `https://openrouter.ai/api/v1`
- Model: `google/gemini-flash-2.0:free`
- Implementation: `app/services/ai_service.py`

## Environment Variables

Required in `.env`:
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `OPENROUTER_API_KEY`: OpenRouter API key (provided)
- `DATABASE_URL`: SQLite path (default: `sqlite+aiosqlite:///./data/gentle_bot.db`)

## Quick Start

```bash
# Using the run script
./run.sh

# Or manually
uv venv
source .venv/bin/activate
uv pip install -e .
python main.py
```