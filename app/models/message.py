from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, Boolean, JSON, Float, Integer
from sqlalchemy.orm import relationship
from .base import Base


class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_message_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    text = Column(Text, nullable=True)
    is_reply = Column(Boolean, default=False)
    reply_to_message_id = Column(BigInteger, nullable=True)
    is_bot_mentioned = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)  # Track deleted messages
    is_forwarded = Column(Boolean, default=False)
    forward_from_chat_id = Column(BigInteger, nullable=True)
    forward_from_message_id = Column(BigInteger, nullable=True)
    relevance_score = Column(Float, nullable=True)  # For tracking message relevance
    raw_data = Column(JSON, nullable=True)
    embedding_vector = Column(Text, nullable=True)  # Store as serialized numpy array
    
    # Relationships
    user = relationship("User", back_populates="messages")
    references = relationship("MessageReference", foreign_keys="MessageReference.from_message_id", back_populates="from_message")
    referenced_by = relationship("MessageReference", foreign_keys="MessageReference.to_message_id", back_populates="to_message")
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, user_id={self.user_id})>"


class MessageReference(Base):
    __tablename__ = 'message_references'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    from_message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    to_message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    reference_type = Column(String(50), nullable=False)  # 'reply', 'forward', 'context', 'similar'
    relevance_score = Column(Float, nullable=True)
    
    # Relationships
    from_message = relationship("Message", foreign_keys=[from_message_id], back_populates="references")
    to_message = relationship("Message", foreign_keys=[to_message_id], back_populates="referenced_by")
    
    def __repr__(self):
        return f"<MessageReference(from={self.from_message_id}, to={self.to_message_id}, type={self.reference_type})>"