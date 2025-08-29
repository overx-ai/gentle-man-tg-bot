import aiohttp
import asyncio
import logging
import yaml
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import random

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = "google/gemini-2.0-flash-001"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/gentle-telegram-bot",
            "X-Title": "Gentle Telegram Bot"
        }
        
        # Load prompts
        with open('prompts.yaml', 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)
        
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_session(self) -> aiohttp.ClientSession:
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def build_context(self, 
                     message: str,
                     user_context: List[Dict] = None,
                     chat_context: List[Dict] = None,
                     is_bot_mentioned: bool = False,
                     is_reply: bool = False,
                     from_bot: bool = False,
                     username: str = None) -> str:
        """Build context-aware prompt"""
        
        # Start with system prompt
        full_prompt = self.prompts['system_prompt'] + "\n\n"
        
        # Add historical context if available
        if chat_context:
            full_prompt += "Контекст беседы:\n"
            for ctx in chat_context[-10:]:  # Last 10 messages
                username = ctx.get('username', 'Пользователь')
                text = ctx.get('text', '')
                full_prompt += f"{username}: {text}\n"
            full_prompt += "\n"
        
        # Add user-specific context
        if user_context:
            full_prompt += "История взаимодействия с пользователем:\n"
            for ctx in user_context[-5:]:  # Last 5 interactions
                text = ctx.get('text', '')
                full_prompt += f"- {text}\n"
            full_prompt += "\n"
        
        # Handle special contexts
        if from_bot:
            full_prompt += self.prompts['special_contexts']['bot_interaction'] + "\n"
        elif is_bot_mentioned:
            full_prompt += self.prompts['special_contexts']['direct_mention'] + "\n"
        elif is_reply:
            full_prompt += self.prompts['special_contexts']['reply_to_message'] + "\n"
        
        # Add username context if available
        if username:
            full_prompt += f"Пользователь @{username} пишет:\n"
        
        # Add the actual message
        full_prompt += f"Сообщение: {message}\n\n"
        full_prompt += f"Ваш ответ (3-5 предложений максимум! Используйте Markdown и обращайтесь как @{username if username else 'друг'}):"
        
        return full_prompt
    
    async def generate_response(self,
                               message: str,
                               user_context: List[Dict] = None,
                               chat_context: List[Dict] = None,
                               is_bot_mentioned: bool = False,
                               is_reply: bool = False,
                               from_bot: bool = False,
                               username: str = None,
                               temperature: float = 0.7) -> str:
        """Generate response using Gemini Flash 2.0 with retry logic"""
        
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                session = await self.get_session()
                
                # Build context-aware prompt
                prompt = self.build_context(
                    message=message,
                    user_context=user_context,
                    chat_context=chat_context,
                    is_bot_mentioned=is_bot_mentioned,
                    is_reply=is_reply,
                    from_bot=from_bot,
                    username=username
                )
                
                # Prepare message with username context
                user_message = message
                if username:
                    user_message = f"Пользователь @{username}: {message}"
                
                # Prepare request
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self.prompts['system_prompt']
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": 300,  # Reduced for shorter responses (3-5 sentences)
                    "top_p": 0.9,
                    "frequency_penalty": 0.3,
                    "presence_penalty": 0.3
                }
                
                # Make API request
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    elif response.status == 429:
                        # Rate limited - retry with exponential backoff
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            logger.warning(f"Rate limited, retrying in {delay:.1f} seconds (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error("Max retries reached for rate-limited request")
                            return self._get_rate_limit_response()
                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        return self._get_fallback_response()
                        
            except asyncio.TimeoutError:
                logger.error("API request timeout")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay)
                    continue
                return self._get_fallback_response()
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay)
                    continue
                return self._get_fallback_response()
        
        return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Return a fallback response when API fails"""
        return "Прошу прощения, в данный момент я испытываю технические сложности. Пожалуйста, повторите Ваш вопрос чуть позже."
    
    def _get_rate_limit_response(self) -> str:
        """Return a response when rate limited"""
        return "Извините, сейчас слишком много запросов. Пожалуйста, подождите несколько секунд и попробуйте снова."
    
    def should_respond_to_bot(self, bot_message_count: int) -> bool:
        """Determine if we should respond to a bot based on message count"""
        # Respond to every 5th message from bots
        return bot_message_count % 5 == 0
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of the message"""
        try:
            session = await self.get_session()
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Analyze the sentiment of the following Russian text. Return JSON with: sentiment (positive/negative/neutral), topics (list), needs_support (boolean)"
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 200
            }
            
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result_text = data['choices'][0]['message']['content']
                    # Try to parse as JSON
                    try:
                        return json.loads(result_text)
                    except:
                        return {
                            "sentiment": "neutral",
                            "topics": [],
                            "needs_support": False
                        }
                else:
                    return {
                        "sentiment": "neutral",
                        "topics": [],
                        "needs_support": False
                    }
                    
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "topics": [],
                "needs_support": False
            }