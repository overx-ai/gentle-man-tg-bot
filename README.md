# gentle-man-tg-bot

A Telegram bot built with the telegram-bot-template framework

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL database
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- OpenRouter API Key (get from [OpenRouter.ai](https://openrouter.ai))

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/hustlestar/gentle-man-tg-bot.git
cd gentle-man-tg-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your favorite editor
```

Required configuration:
- `TELEGRAM_BOT_TOKEN` - Your bot token from BotFather
- `DATABASE_URL` - PostgreSQL connection string

### 4. Database Setup

```bash
# Create database
createdb gentle_man_tg_bot

# Run migrations
gentle-man-tg-bot migrate
```

### 5. Run the Bot

```bash
# Start the bot
gentle-man-tg-bot

# Or with Python
python -m gentle_man_tg_bot.main
```

## 🛠️ Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=gentle_man_tg_bot
```

### Code Quality

```bash
# Format code
black gentle_man_tg_bot/
isort gentle_man_tg_bot/

# Type checking
mypy gentle_man_tg_bot/
```

### Database Migrations

```bash
# Check migration status
gentle-man-tg-bot db status

# Create new migration
gentle-man-tg-bot db revision -m "Description"

# Apply migrations
gentle-man-tg-bot db upgrade

# Rollback
gentle-man-tg-bot db downgrade
```

## 🚀 Deployment

### Using GitHub Actions

1. Set up GitHub Secrets:
   - `DEPLOY_SSH_KEY` - SSH key for server access
   - `SERVER_HOST` - Your server hostname
   - `SERVER_USER` - Server username
   - `TELEGRAM_BOT_TOKEN` - Bot token
   - `DATABASE_URL` - Production database URL
- `OPENROUTER_API_KEY` - OpenRouter API key

2. Push to main branch to trigger deployment

### Manual Deployment

```bash
# On your server
cd /path/to/deployment
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
gentle-man-tg-bot migrate
sudo systemctl restart gentle-man-tg-bot
```

## 📚 Features

- 🌐 Multi-language support (en,ru,es)
- ⌨️ Dynamic inline keyboards
- 🤖 AI-powered responses via OpenRouter

- 💾 PostgreSQL database with migrations
- 🔄 Auto-migration on startup
- 📝 Clean, extensible architecture

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

Jack Ma - hustlequeen@mail.ru

---

Built with [telegram-bot-template](https://github.com/hustlestar/tg-bot-template)