#!/bin/bash

echo "Starting Gentle Telegram Bot..."

# Create data directory if it doesn't exist
mkdir -p data

# Check if uv is installed
if command -v uv &> /dev/null; then
    echo "Using uv package manager..."
    
    # Create virtual environment if needed
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        uv venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install/update dependencies
    echo "Installing dependencies..."
    uv pip install -e . -q
else
  exit 1
fi

# Run the bot
echo "Starting bot..."
python main.py