#!/usr/bin/env python3
"""
Gentle Telegram Bot - Main Entry Point
A sophisticated conversational bot using Gemini Flash 2.0
"""

import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, '.')

from app.bot import GentleBot


def main():
    """Main function"""
    try:
        bot = GentleBot()
        bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()