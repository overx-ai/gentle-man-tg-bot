import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from .config import settings
from .database import init_database, close_database
from .services.ai_service import GeminiService
from .services.vector_store import VectorStore
from .handlers.message_handler import MessageHandler as CustomMessageHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, settings.log_level)
)
logger = logging.getLogger(__name__)

# Silence noisy loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram.ext.Application').setLevel(logging.WARNING)
logging.getLogger('telegram.ext.Updater').setLevel(logging.WARNING)


class GentleBot:
    def __init__(self):
        self.app = None
        self.ai_service = None
        self.vector_store = None
        self.message_handler = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "Добро пожаловать! Я - ваш интеллигентный собеседник.\n\n"
            "Я здесь, чтобы помочь, поддержать и вести содержательную беседу. "
            "Обращайтесь ко мне через @упоминание или отвечайте на мои сообщения.\n\n"
            "Чем могу быть полезен?"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            "📚 *Как со мной общаться:*\n\n"
            "• Упомяните меня через @ в сообщении\n"
            "• Ответьте на любое моё сообщение\n"
            "• Я запоминаю контекст нашей беседы\n\n"
            "Я стремлюсь быть полезным советником и мудрым собеседником. "
            "Задавайте любые вопросы!",
            parse_mode='Markdown'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show user statistics"""
        from .database import get_session
        from .models import User, Message
        from sqlalchemy import select, func
        
        user_id = update.effective_user.id
        
        async with get_session() as session:
            # Get user stats
            result = await session.execute(
                select(func.count(Message.id))
                .where(Message.user_id == user_id)
            )
            message_count = result.scalar() or 0
            
            await update.message.reply_text(
                f"📊 *Ваша статистика:*\n\n"
                f"• Сообщений: {message_count}\n"
                f"• ID: {user_id}\n",
                parse_mode='Markdown'
            )
    
    async def post_init(self, application: Application):
        """Initialize bot after application is built"""
        # Get bot info
        bot_info = await application.bot.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        
        # Set bot username in message handler
        if self.message_handler:
            self.message_handler.set_bot_username(bot_info.username)
        
        # Initialize database
        await init_database()
        
        # Initialize AI service session
        await self.ai_service.__aenter__()
        
        # Send startup notification to admin
        try:
            await application.bot.send_message(
                chat_id=settings.admin_user_id,
                text=f"🟢 **Bot Started**\n\n"
                     f"Bot: @{bot_info.username}\n"
                     f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                     f"Status: All systems operational",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Could not send startup notification: {e}")
    
    async def shutdown(self, application: Application):
        """Cleanup on shutdown"""
        logger.info("Shutting down bot...")
        
        # Send shutdown notification to admin
        try:
            await application.bot.send_message(
                chat_id=settings.admin_user_id,
                text=f"🔴 **Bot Stopping**\n\n"
                     f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                     f"Status: Shutting down gracefully",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Could not send shutdown notification: {e}")
        
        # Close AI service session
        if self.ai_service:
            await self.ai_service.__aexit__(None, None, None)
        
        # Save vector store
        if self.vector_store:
            await self.vector_store.save()
        
        # Close database
        await close_database()
    
    def run(self):
        """Run the bot"""
        # Initialize services
        self.ai_service = GeminiService(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url
        )
        
        self.vector_store = VectorStore(
            openai_api_key=settings.openai_embeddings_api_key,
            embedding_model=settings.openai_embedding_model,
            store_path=settings.vector_store_path
        )
        
        self.message_handler = CustomMessageHandler(
            ai_service=self.ai_service,
            vector_store=self.vector_store
        )
        
        # Create application
        self.app = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .post_init(self.post_init)
            .post_shutdown(self.shutdown)
            .build()
        )
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Add handler for new chat members (when bot is added to group)
        self.app.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                self.message_handler.handle_new_chat_members
            )
        )
        
        # Add message handler for all text messages
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.message_handler.handle_message
            )
        )
        
        # Run bot with all updates allowed and privacy mode considerations
        logger.info("Starting bot...")
        logger.info("NOTE: If bot doesn't see group messages, disable privacy mode via @BotFather:")
        logger.info("  1. Go to @BotFather")
        logger.info("  2. Send /mybots")
        logger.info("  3. Select your bot")
        logger.info("  4. Bot Settings -> Group Privacy -> Turn off")
        self.app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False
        )