from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, BigInteger
from sqlalchemy.sql import func
from .base import Base


class Chat(Base):
    """Telegram chat/group model"""
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    title = Column(String)
    type = Column(String)  # private, group, supergroup, channel
    username = Column(String)
    member_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())