# Gentle Telegram Bot

Интеллигентный чат-бот для Telegram с использованием Google Gemini Flash 2.0, векторной базы данных FAISS и PostgreSQL.

## 🌟 Возможности

- 🤖 **Google Gemini Flash 2.0** через OpenRouter API (бесплатный тариф)
- 💾 **SQLite с Async SQLAlchemy** для локального хранения истории
- 🔍 **FAISS векторный поиск** для контекстно-зависимых ответов
- 🎯 **Умная фильтрация ботов** - отвечает каждому 5-му сообщению от ботов
- 🌐 **Литературный русский язык** с высоким уровнем интеллекта
- 📝 **Настраиваемые промпты** в YAML формате
- 🧠 **Запоминание контекста** беседы и пользователей
- 📎 **Умные ссылки на сообщения** - автоматически ссылается на релевантные сообщения
- 🔄 **Пересылка сообщений** - может пересылать важные сообщения при необходимости
- ⚡ **Обработка удалённых сообщений** - корректно обрабатывает удалённые сообщения
- 👋 **Приветствие при добавлении в группу** - представляется при добавлении в чат

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- SQLite (автоматически создаётся)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### 2. Installation

Using uv (recommended):
```bash
# Clone the repository
git clone https://github.com/hustlestar/gentle-man-tg-bot.git
cd gentle-man-tg-bot

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Or using pip:
```bash
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

# Edit .env and add your Telegram bot token
# TELEGRAM_BOT_TOKEN=your_bot_token_here
```

The OpenRouter API key is already configured for Gemini Flash 2.0.

### 4. Database Setup

SQLite database will be created automatically in `./data/gentle_bot.db` when you run the bot.

### 5. Run the Bot

```bash
# Run directly
python main.py

# Or with Docker Compose
docker-compose up -d
```

## 🛠️ Development

### Project Structure

```
gentle-man-tg-bot/
├── app/
│   ├── models/         # SQLAlchemy models
│   ├── services/       # AI and vector services
│   ├── handlers/       # Message handlers
│   ├── bot.py         # Main bot class
│   ├── config.py      # Configuration
│   └── database.py    # Database setup
├── prompts.yaml       # Russian prompts configuration
├── requirements.txt   # Python dependencies
├── docker-compose.yml # Docker configuration
├── Dockerfile        # Docker image
└── main.py          # Entry point
```

### Bot Commands

- `/start` - Welcome message and bot information
- `/help` - Usage instructions
- `/stats` - User statistics

### Interaction

The bot responds when:
1. Mentioned via @username
2. Someone replies to its message
3. Every 5th message from other bots (configurable)

## 📚 Features

- 🌐 **Context-aware responses** - remembers conversation history
- ⌨️ **Smart bot filtering** - avoids spam in bot-heavy chats
- 🤖 **High-quality AI responses** using Gemini Flash 2.0
- 💾 **PostgreSQL database** with async operations
- 🔄 **Vector similarity search** for relevant context
- 📝 **Customizable personality** via YAML prompts

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