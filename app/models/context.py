from sqlalchemy import Column, BigInteger, Text, Float, JSON, Integer
from .base import Base


class Context(Base):
    __tablename__ = 'contexts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    context_type = Column(Text, nullable=False)  # 'conversation', 'topic', 'user_preference'
    content = Column(Text, nullable=False)
    embedding_vector = Column(Text, nullable=True)  # Serialized numpy array
    similarity_score = Column(Float, nullable=True)
    meta_data = Column(JSON, nullable=True)  # Renamed from metadata to avoid SQLAlchemy reserved word
    
    def __repr__(self):
        return f"<Context(id={self.id}, chat_id={self.chat_id}, type={self.context_type})>"