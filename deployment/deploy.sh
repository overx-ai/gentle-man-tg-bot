#!/bin/bash
# Simple deployment script for gentle-man-tg-bot

set -e

echo "🚀 Deploying gentle-man-tg-bot..."

# Update code
echo "📦 Pulling latest changes..."
git pull origin main || git pull origin master

# Update dependencies
echo "📚 Installing dependencies..."
source venv/bin/activate || python3.11 -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
echo "🗄️ Running database migrations..."
gentle-man-tg-bot migrate || python -m cli migrate

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart gentle-man-tg-bot.service

# Check status
echo "✅ Checking service status..."
sudo systemctl status gentle-man-tg-bot.service --no-pager

echo "✨ Deployment complete!"