#!/bin/bash
# Initial setup script for gentle-man-tg-bot

set -e

echo "🚀 Setting up gentle-man-tg-bot for the first time..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "❌ Please don't run this script as root"
   exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv postgresql-client

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration!"
    read -p "Press enter when you've updated .env file..."
fi

# Create database if needed
echo "🗄️ Setting up database..."
read -p "Enter PostgreSQL database name [gentle_man_tg_bot]: " db_name
db_name=${db_name:-gentle_man_tg_bot}

createdb $db_name || echo "Database might already exist, continuing..."

# Run migrations
echo "🔄 Running database migrations..."
gentle-man-tg-bot migrate || python -m cli migrate

# Install systemd service
echo "⚙️ Installing systemd service..."
sudo cp deployment/gentle-man-tg-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gentle-man-tg-bot.service

# Start service
echo "▶️ Starting service..."
sudo systemctl start gentle-man-tg-bot.service

# Check status
echo "✅ Checking service status..."
sudo systemctl status gentle-man-tg-bot.service --no-pager

echo "✨ Setup complete!"
echo ""
echo "📌 Next steps:"
echo "1. Check logs: sudo journalctl -u gentle-man-tg-bot -f"
echo "2. Restart service: sudo systemctl restart gentle-man-tg-bot"
echo "3. Deploy updates: ./deployment/deploy.sh"