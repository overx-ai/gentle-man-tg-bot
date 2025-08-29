import logging
import random
from telegram import Update, Message, Bot
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TelegramError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ..models import User, Message as DBMessage, MessageReference
from ..services.ai_service import GeminiService
from ..services.vector_store import VectorStore
from ..database import get_session

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, ai_service: GeminiService, vector_store: VectorStore):
        self.ai_service = ai_service
        self.vector_store = vector_store
        self.bot_username: Optional[str] = None
        self.message_cache = {}  # Cache for recent messages
        self.relevance_threshold = 0.7  # Threshold for message relevance
    
    def set_bot_username(self, username: str):
        """Set bot username for mention detection"""
        self.bot_username = username.lower() if username else None
        logger.info(f"Bot username set to: @{self.bot_username}")
    
    async def handle_new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when bot is added to a new group"""
        if not update.message or not update.message.new_chat_members:
            return
        
        # Check if bot was added
        bot_id = context.bot.id
        bot_added = any(member.id == bot_id for member in update.message.new_chat_members)
        
        if not bot_added:
            return
        
        chat_id = update.message.chat_id
        chat = update.message.chat
        
        # Get chat members count if possible
        try:
            member_count = await context.bot.get_chat_member_count(chat_id)
        except:
            member_count = "неизвестное количество"
        
        # Generate welcome message using AI
        welcome_prompt = f"""
        Ты только что был добавлен в групповой чат "{chat.title or 'без названия'}" с {member_count} участниками.
        Создай приветственное сообщение, представься и расскажи о своих возможностях.
        Будь дружелюбным, вежливым и используй высокий литературный стиль.
        Упомяни что:
        - Ты отвечаешь на упоминания через @ и ответы на свои сообщения
        - Запоминаешь контекст беседы
        - Можешь ссылаться на предыдущие сообщения
        - Готов помочь, поддержать и вести интеллектуальную беседу
        """
        
        welcome_message = await self.ai_service.generate_response(
            message=welcome_prompt,
            temperature=0.8
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_message,
            parse_mode='Markdown'
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main message handler with enhanced features"""
        if not update.message or not update.message.text:
            return
        
        message = update.message
        chat_id = message.chat_id
        user = message.from_user
        text = message.text
        
        logger.info(f"Received message in chat {chat_id} (type: {message.chat.type}) from {user.username or user.first_name}: {text[:50]}...")
        
        # Check if bot is mentioned
        is_bot_mentioned = self._is_bot_mentioned(text)
        
        # Check if this is a reply to bot's message
        is_reply_to_bot = False
        if message.reply_to_message and message.reply_to_message.from_user:
            is_reply_to_bot = message.reply_to_message.from_user.id == context.bot.id
        
        # Store message in database with enhanced tracking
        async with get_session() as session:
            # Get or create user
            db_user = await self._get_or_create_user(session, user)
            
            # Check if user is a bot and apply filtering
            should_respond = True
            if db_user.is_bot and not is_bot_mentioned and not is_reply_to_bot:
                db_user.bot_message_count += 1
                should_respond = self.ai_service.should_respond_to_bot(db_user.bot_message_count)
                await session.commit()
                
                if not should_respond:
                    logger.info(f"Skipping response to bot {user.username} (message {db_user.bot_message_count})")
                    # Still store the message for context
                    await self._store_message_in_db(session, message, db_user, is_bot_mentioned)
                    await self._store_message_context(message, user)
                    return
            
            # Save message to database
            db_message = await self._store_message_in_db(session, message, db_user, is_bot_mentioned)
            
            # Track message references if it's a reply
            if message.reply_to_message:
                await self._track_message_reference(
                    session, 
                    db_message.id, 
                    message.reply_to_message.message_id,
                    'reply'
                )
        
        # Check if this is a private chat
        is_private_chat = message.chat.type == 'private'
        
        # Determine if we should respond
        if not (is_bot_mentioned or is_reply_to_bot or is_private_chat):
            # Store in vector store for context but don't respond
            logger.info(f"Not responding to message from {user.username}: not mentioned, not a reply, and not private chat")
            await self._store_message_context(message, user)
            return
        
        logger.info(f"Responding to message from {user.username}: private={is_private_chat}, mentioned={is_bot_mentioned}, reply={is_reply_to_bot}")
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            # In group chats, don't filter by user - get all chat context
            # In private chats, user context and chat context are the same
            is_group_chat = message.chat.type in ['group', 'supergroup']
            
            if is_group_chat:
                # In groups, get chat context only (no user filtering)
                chat_context = await self.vector_store.get_chat_context(chat_id, limit=12)
                user_context = []  # Don't use user-specific context in groups
            else:
                # In private chats, get user-specific context
                user_context = await self.vector_store.get_user_context(user.id, chat_id, limit=6)
                chat_context = await self.vector_store.get_chat_context(chat_id, limit=6)
            
            # Search for 6 similar messages in vector store
            similar_messages = await self.vector_store.search(text, k=6, chat_id=chat_id)
            
            # Combine contexts - max 12 messages total (6 recent + 6 similar)
            enhanced_context = []
            
            # Add recent chat messages (up to 6)
            for msg in chat_context[-6:]:
                if msg not in enhanced_context:
                    enhanced_context.append(msg)
            
            # Add similar messages from vector store (up to 6)
            added_similar = 0
            for msg, score in similar_messages:
                if added_similar >= 6:
                    break
                if msg not in enhanced_context:
                    enhanced_context.append(msg)
                    added_similar += 1
            
            # Find relevant previous messages for referencing
            relevant_messages = await self._find_relevant_messages(text, chat_id, session)
            
            # Prepare limited context (max 12 messages)
            context_messages = enhanced_context[:12]
            
            # Generate response with username
            response = await self.ai_service.generate_response(
                message=text,
                user_context=user_context,
                chat_context=context_messages,
                is_bot_mentioned=is_bot_mentioned,
                is_reply=is_reply_to_bot,
                from_bot=db_user.is_bot,
                username=user.username or user.first_name
            )
            
            # Check if we should reference or forward any previous messages
            reference_decision = await self._should_reference_message(
                text, 
                relevant_messages,
                response
            )
            
            # Send response with references if needed
            if reference_decision and reference_decision['should_reference']:
                await self._send_with_reference(
                    context.bot,
                    chat_id,
                    response,
                    reference_decision,
                    message.message_id
                )
            else:
                # Send normal response with Markdown
                sent_message = await message.reply_text(
                    response,
                    reply_to_message_id=message.message_id,
                    parse_mode='Markdown'
                )
                
                # Store bot's response
                await self._store_bot_response(sent_message, context.bot.id, chat_id, response)
            
            # Store messages in vector store
            await self._store_message_context(message, user)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.reply_text(
                "Прошу прощения, произошла техническая ошибка. Пожалуйста, попробуйте ещё раз.",
                parse_mode='Markdown'
            )
    
    async def _store_message_in_db(self, session: AsyncSession, message: Message, 
                                   db_user: User, is_bot_mentioned: bool) -> DBMessage:
        """Store message in database with enhanced tracking"""
        # Check for forwarded message attributes
        is_forwarded = hasattr(message, 'forward_origin') or hasattr(message, 'forward_from')
        forward_from_chat_id = None
        if hasattr(message, 'forward_origin') and hasattr(message.forward_origin, 'chat'):
            forward_from_chat_id = message.forward_origin.chat.id
        elif hasattr(message, 'forward_from_chat'):
            forward_from_chat_id = message.forward_from_chat.id if message.forward_from_chat else None
            
        db_message = DBMessage(
            telegram_message_id=message.message_id,
            chat_id=message.chat_id,
            user_id=db_user.telegram_id,
            text=message.text,
            is_reply=message.reply_to_message is not None,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,
            is_bot_mentioned=is_bot_mentioned,
            is_forwarded=is_forwarded,
            forward_from_chat_id=forward_from_chat_id,
            forward_from_message_id=None,  # Not easily accessible in newer telegram API
            raw_data={
                'username': db_user.username,
                'first_name': db_user.first_name,
                'last_name': db_user.last_name,
                'date': message.date.isoformat() if message.date else None
            }
        )
        session.add(db_message)
        await session.commit()
        return db_message
    
    async def _track_message_reference(self, session: AsyncSession, 
                                      from_msg_id: int, to_msg_telegram_id: int, 
                                      ref_type: str):
        """Track message references"""
        # Find the referenced message in DB
        result = await session.execute(
            select(DBMessage).where(DBMessage.telegram_message_id == to_msg_telegram_id)
        )
        to_message = result.scalar_one_or_none()
        
        if to_message:
            reference = MessageReference(
                from_message_id=from_msg_id,
                to_message_id=to_message.id,
                reference_type=ref_type
            )
            session.add(reference)
            await session.commit()
    
    async def _find_relevant_messages(self, query: str, chat_id: int, 
                                     session: AsyncSession = None) -> List[Dict]:
        """Find relevant messages from database"""
        relevant_messages = []
        
        async with get_session() as db_session:
            if not session:
                session = db_session
            
            # Get recent messages from chat
            result = await session.execute(
                select(DBMessage)
                .where(
                    and_(
                        DBMessage.chat_id == chat_id,
                        DBMessage.is_deleted == False
                    )
                )
                .order_by(desc(DBMessage.created_at))
                .limit(50)
            )
            recent_messages = result.scalars().all()
            
            for msg in recent_messages:
                relevant_messages.append({
                    'id': msg.id,
                    'telegram_id': msg.telegram_message_id,
                    'text': msg.text,
                    'user_id': msg.user_id,
                    'created_at': msg.created_at,
                    'is_reply': msg.is_reply,
                    'reply_to': msg.reply_to_message_id
                })
        
        return relevant_messages
    
    async def _prepare_context_with_references(self, relevant_messages: List[Dict],
                                              vector_context: List[Dict],
                                              chat_id: int) -> List[Dict]:
        """Prepare context with message references - limited to 12 messages total"""
        context_messages = vector_context.copy()
        
        # Add relevant messages with their relationships (ensure total doesn't exceed 12)
        remaining_slots = max(0, 12 - len(context_messages))
        for msg in relevant_messages[:remaining_slots]:
            if msg not in context_messages:
                context_messages.append({
                    'text': msg.get('text'),
                    'user_id': msg.get('user_id'),
                    'message_id': msg.get('telegram_id'),
                    'timestamp': msg.get('created_at'),
                    'is_reference': True
                })
        
        return context_messages[:12]  # Ensure we never exceed 12 messages
    
    async def _should_reference_message(self, current_text: str, 
                                       relevant_messages: List[Dict],
                                       response: str) -> Optional[Dict]:
        """Decide if we should reference a previous message"""
        if not relevant_messages:
            return None
        
        # Use AI to decide if referencing would be helpful
        decision_prompt = f"""
        Текущее сообщение: {current_text}
        Мой ответ: {response}
        
        Есть релевантные предыдущие сообщения. Должен ли я сослаться на одно из них?
        Ответь JSON: {{"should_reference": true/false, "message_index": 0-9, "reference_type": "reply"/"forward"/"quote"}}
        """
        
        try:
            decision = await self.ai_service.generate_response(
                message=decision_prompt,
                temperature=0.3
            )
            
            # Parse decision (simplified - in production use proper JSON parsing)
            if "true" in decision.lower():
                # Pick a relevant message
                return {
                    'should_reference': True,
                    'message': relevant_messages[0] if relevant_messages else None,
                    'type': 'reply'
                }
        except:
            pass
        
        return None
    
    async def _send_with_reference(self, bot: Bot, chat_id: int, 
                                  response: str, reference_decision: Dict,
                                  original_msg_id: int):
        """Send message with reference to previous message"""
        try:
            ref_msg = reference_decision.get('message')
            ref_type = reference_decision.get('type', 'reply')
            
            if ref_type == 'reply' and ref_msg:
                # Try to reply to the referenced message
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"📎 Ссылаясь на предыдущее сообщение:\n\n{response}",
                        reply_to_message_id=ref_msg['telegram_id']
                    )
                except BadRequest:
                    # Message might be deleted, send without reference
                    await bot.send_message(
                        chat_id=chat_id,
                        text=response,
                        reply_to_message_id=original_msg_id
                    )
            elif ref_type == 'forward' and ref_msg:
                # Forward the message then reply
                try:
                    await bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=chat_id,
                        message_id=ref_msg['telegram_id']
                    )
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"☝️ Относительно сообщения выше:\n\n{response}"
                    )
                except BadRequest:
                    # Message deleted, just send response
                    await bot.send_message(
                        chat_id=chat_id,
                        text=response,
                        reply_to_message_id=original_msg_id
                    )
            else:
                # Quote the message in response
                quoted_text = ref_msg.get('text', '')[:100] if ref_msg else ''
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"💬 «{quoted_text}...»\n\n{response}",
                    reply_to_message_id=original_msg_id
                )
                
        except TelegramError as e:
            logger.error(f"Error sending with reference: {e}")
            # Fallback to simple reply
            await bot.send_message(
                chat_id=chat_id,
                text=response,
                reply_to_message_id=original_msg_id
            )
    
    async def _store_bot_response(self, sent_message: Message, bot_id: int, 
                                 chat_id: int, response_text: str):
        """Store bot's response in database and vector store"""
        async with get_session() as session:
            # Create bot user if not exists
            result = await session.execute(
                select(User).where(User.telegram_id == bot_id)
            )
            bot_user = result.scalar_one_or_none()
            
            if not bot_user:
                bot_user = User(
                    telegram_id=bot_id,
                    username=self.bot_username,
                    first_name="Gentle Bot",
                    is_bot=True
                )
                session.add(bot_user)
                await session.commit()
            
            # Store message
            db_message = DBMessage(
                telegram_message_id=sent_message.message_id,
                chat_id=chat_id,
                user_id=bot_id,
                text=response_text,
                is_reply=True,
                reply_to_message_id=sent_message.reply_to_message.message_id if sent_message.reply_to_message else None,
                raw_data={'is_bot_response': True}
            )
            session.add(db_message)
            await session.commit()
        
        # Store in vector store
        await self.vector_store.add_messages([{
            'text': response_text,
            'chat_id': chat_id,
            'user_id': bot_id,
            'username': self.bot_username,
            'timestamp': datetime.utcnow(),
            'message_id': sent_message.message_id
        }])
    
    async def handle_deleted_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle deleted messages gracefully"""
        if not update.message:
            return
        
        # Mark message as deleted in database
        async with get_session() as session:
            result = await session.execute(
                select(DBMessage).where(
                    DBMessage.telegram_message_id == update.message.message_id
                )
            )
            db_message = result.scalar_one_or_none()
            
            if db_message:
                db_message.is_deleted = True
                await session.commit()
                logger.info(f"Marked message {update.message.message_id} as deleted")
    
    async def _get_or_create_user(self, session: AsyncSession, tg_user) -> User:
        """Get or create user in database"""
        result = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            db_user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                is_bot=tg_user.is_bot,
                language_code=tg_user.language_code
            )
            session.add(db_user)
            await session.commit()
        else:
            # Update user info
            db_user.username = tg_user.username
            db_user.first_name = tg_user.first_name
            db_user.last_name = tg_user.last_name
            await session.commit()
        
        return db_user
    
    async def _store_message_context(self, message: Message, user):
        """Store message in vector store for context"""
        await self.vector_store.add_messages([{
            'text': message.text,
            'chat_id': message.chat_id,
            'user_id': user.id,
            'username': user.username or user.first_name,
            'timestamp': datetime.utcnow(),
            'message_id': message.message_id
        }])
    
    def _is_bot_mentioned(self, text: str) -> bool:
        """Check if bot is mentioned in the message"""
        if not self.bot_username or not text:
            return False
        
        text_lower = text.lower()
        return f"@{self.bot_username}" in text_lower