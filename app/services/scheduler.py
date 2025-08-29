import logging
import random
import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, Set, Optional
from telegram import Bot
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import User, Message, Chat
from ..services.ai_service import GeminiService
from ..services.vector_store import VectorStore
from ..config import settings

logger = logging.getLogger(__name__)


class DailyMessageScheduler:
    """Scheduler for sending daily messages to random users"""
    
    def __init__(self, bot: Bot, ai_service: GeminiService, vector_store: VectorStore):
        self.bot = bot
        self.ai_service = ai_service
        self.vector_store = vector_store
        self.running = False
        self.last_message_dates: Dict[int, datetime] = {}  # chat_id -> last message date
        self.scheduled_hour = 14  # 2 PM by default
        self.scheduled_minute = 0
        
    async def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info("Daily message scheduler started")
        
        while self.running:
            try:
                await self._check_and_send_daily_messages()
                # Sleep for 1 hour before checking again
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(3600)
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Daily message scheduler stopped")
    
    async def _check_and_send_daily_messages(self):
        """Check if it's time to send daily messages"""
        now = datetime.now()
        current_time = now.time()
        scheduled_time = time(self.scheduled_hour, self.scheduled_minute)
        
        # Check if it's within the scheduled hour (with 1 hour tolerance)
        if abs((current_time.hour * 60 + current_time.minute) - 
               (scheduled_time.hour * 60 + scheduled_time.minute)) > 60:
            return
        
        # Get all active group chats
        async with get_session() as session:
            # Get all group chats where bot has sent messages
            result = await session.execute(
                select(Message.chat_id).distinct()
                .where(
                    and_(
                        Message.chat_id < 0,  # Negative IDs are groups
                        Message.created_at > now - timedelta(days=7)  # Active in last 7 days
                    )
                )
            )
            active_chat_ids = [row[0] for row in result.fetchall()]
        
        for chat_id in active_chat_ids:
            # Check if we already sent a message today
            last_sent = self.last_message_dates.get(chat_id)
            if last_sent and last_sent.date() == now.date():
                continue
            
            try:
                await self._send_daily_message_to_chat(chat_id)
                self.last_message_dates[chat_id] = now
            except Exception as e:
                logger.error(f"Error sending daily message to chat {chat_id}: {e}")
    
    async def _send_daily_message_to_chat(self, chat_id: int):
        """Send a daily message to a random user in the chat"""
        async with get_session() as session:
            # Get active users from the last 7 days
            result = await session.execute(
                select(User)
                .join(Message, Message.user_id == User.telegram_id)
                .where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.created_at > datetime.now() - timedelta(days=7),
                        User.is_bot == False
                    )
                )
                .group_by(User.telegram_id)
                .having(func.count(Message.id) > 3)  # Users with at least 3 messages
            )
            active_users = result.scalars().all()
            
            if not active_users:
                logger.info(f"No active users found in chat {chat_id}")
                return
            
            # Pick a random user
            selected_user = random.choice(active_users)
            
            # Get recent messages from this user for context
            result = await session.execute(
                select(Message)
                .where(
                    and_(
                        Message.chat_id == chat_id,
                        Message.user_id == selected_user.telegram_id,
                        Message.created_at > datetime.now() - timedelta(days=3)
                    )
                )
                .order_by(Message.created_at.desc())
                .limit(5)
            )
            recent_messages = result.scalars().all()
            
            # Get chat context
            chat_context = await self.vector_store.get_chat_context(chat_id, limit=10)
            
            # Generate a personalized message
            await self._generate_and_send_message(
                chat_id, 
                selected_user, 
                recent_messages,
                chat_context
            )
    
    async def _generate_and_send_message(self, chat_id: int, user: User, 
                                        recent_messages: list, chat_context: list):
        """Generate and send a personalized message to the user"""
        # Prepare context about the user
        user_context = "\n".join([
            f"- {msg.created_at.strftime('%Y-%m-%d %H:%M')}: {msg.text[:100]}"
            for msg in recent_messages[:5]
        ])
        
        # Create a prompt for the AI
        prompt = f"""
        Ты дружелюбный бот в групповом чате. Раз в день ты выбираешь случайного участника 
        и отправляешь ему персонализированное сообщение.
        
        Сегодня ты выбрал пользователя @{user.username or user.first_name}.
        
        Последние сообщения этого пользователя:
        {user_context}
        
        Контекст чата:
        {str(chat_context)[:1000]}
        
        Напиши дружелюбное, позитивное сообщение этому пользователю. 
        Можешь:
        - Похвалить за что-то конкретное из его сообщений
        - Задать интересный вопрос по теме его интересов
        - Поделиться интересным фактом, связанным с его темами
        - Пожелать хорошего дня с учетом его активности
        
        Важно:
        - Обращайся к пользователю по имени или username
        - Будь конкретным, ссылайся на его реальные сообщения
        - Сообщение должно быть коротким (1-3 предложения)
        - Будь дружелюбным и позитивным
        - НЕ используй слишком много эмодзи (максимум 1-2)
        """
        
        try:
            # Generate message
            message = await self.ai_service.generate_response(
                message=prompt,
                temperature=0.9,
                max_tokens=200
            )
            
            # Send the message
            username = f"@{user.username}" if user.username else user.first_name
            full_message = f"{username}, {message}"
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=full_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent daily message to {username} in chat {chat_id}")
            
            # Store the message in database
            async with get_session() as session:
                db_message = Message(
                    telegram_message_id=0,  # We don't have the message ID here
                    chat_id=chat_id,
                    user_id=self.bot.id,
                    text=full_message,
                    is_bot_mentioned=False,
                    raw_data={'type': 'daily_message', 'target_user': user.telegram_id}
                )
                session.add(db_message)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error generating/sending daily message: {e}")
    
    async def force_send_daily_message(self, chat_id: int):
        """Force send a daily message (for testing)"""
        logger.info(f"Force sending daily message to chat {chat_id}")
        await self._send_daily_message_to_chat(chat_id)