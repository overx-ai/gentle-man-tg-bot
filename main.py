#!/usr/bin/env python3
"""
Gentle Telegram Bot - Main Entry Point
A sophisticated conversational bot using Gemini Flash 2.0
"""

import sys
import logging
from datetime import datetime
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
        # Try to send error notification
        import asyncio
        from telegram import Bot
        from app.config import settings
        
        async def send_error():
            try:
                bot = Bot(token=settings.telegram_bot_token)
                await bot.send_message(
                    chat_id=settings.admin_user_id,
                    text=f"💥 **Bot Crashed**\n\n"
                         f"Error: {str(e)[:200]}\n"
                         f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        asyncio.run(send_error())
        sys.exit(1)


if __name__ == "__main__":
    main()