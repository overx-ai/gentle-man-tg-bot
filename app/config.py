from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = Field(..., env='TELEGRAM_BOT_TOKEN')
    
    # Database
    database_url: str = Field(
        default='sqlite+aiosqlite:///./data/gentle_bot.db',
        env='DATABASE_URL'
    )
    
    # OpenRouter API
    openrouter_api_key: str = Field(..., env='OPENROUTER_API_KEY')
    openrouter_base_url: str = Field(
        default='https://openrouter.ai/api/v1',
        env='OPENROUTER_BASE_URL'
    )
    
    # OpenAI Embeddings API
    openai_embeddings_api_key: str = Field(..., env='OPENAI_EMBEDDINGS_API_KEY')
    openai_embedding_model: str = Field(
        default='text-embedding-3-small',
        env='OPENAI_EMBEDDING_MODEL'
    )
    
    # Vector Store
    vector_store_path: str = Field(default='./data/vector_store', env='VECTOR_STORE_PATH')
    
    # Bot Configuration
    message_history_limit: int = Field(default=100, env='MESSAGE_HISTORY_LIMIT')
    bot_response_frequency: int = Field(default=5, env='BOT_RESPONSE_FREQUENCY')
    
    # Logging
    log_level: str = Field(default='INFO', env='LOG_LEVEL')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Create global settings instance
settings = Settings()