import faiss
import numpy as np
import pickle
import os
from openai import AsyncOpenAI
from typing import List, Tuple, Optional, Dict, Any
import logging
import asyncio

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, openai_api_key: str, embedding_model: str = "text-embedding-3-small", store_path: str = "./data/vector_store"):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.embedding_model = embedding_model
        self.dimension = 1536  # OpenAI text-embedding-3-small dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.store_path = store_path
        self.metadata: List[Dict[Any, Any]] = []
        
        os.makedirs(store_path, exist_ok=True)
        self.index_path = os.path.join(store_path, "faiss.index")
        self.metadata_path = os.path.join(store_path, "metadata.pkl")
        
        self.load()
    
    async def encode(self, texts: List[str]) -> np.ndarray:
        """Get embeddings from OpenAI API"""
        try:
            # Remove empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                return np.array([])
            
            response = await self.client.embeddings.create(
                input=valid_texts,
                model=self.embedding_model
            )
            
            embeddings = np.array([item.embedding for item in response.data])
            return embeddings
            
        except Exception as e:
            logger.error(f"Error getting embeddings from OpenAI: {e}")
            # Return zero embeddings as fallback
            return np.zeros((len(texts), self.dimension))
    
    async def add_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Add messages to vector store with metadata"""
        valid_messages = [msg for msg in messages if msg.get('text') and msg['text'].strip()]
        if not valid_messages:
            return
            
        texts = [msg['text'] for msg in valid_messages]
        embeddings = await self.encode(texts)
        
        if embeddings.size > 0:
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store metadata
            for msg in valid_messages:
                self.metadata.append({
                    'chat_id': msg.get('chat_id'),
                    'user_id': msg.get('user_id'),
                    'username': msg.get('username'),
                    'text': msg.get('text'),
                    'timestamp': msg.get('timestamp'),
                    'message_id': msg.get('message_id')
                })
            
            await self.save()
    
    async def search(self, query: str, k: int = 5, chat_id: Optional[int] = None) -> List[Tuple[Dict, float]]:
        """Search for similar messages - ALWAYS filtered by chat_id for context isolation"""
        if not query or not query.strip():
            return []
        
        if chat_id is None:
            logger.warning("search() called without chat_id - returning empty results for safety")
            return []
            
        query_embedding = await self.encode([query])
        
        if query_embedding.size == 0 or self.index.ntotal == 0:
            return []
        
        # Search in FAISS
        search_k = min(k * 3, self.index.ntotal)  # Search more to ensure we get enough from this chat
        distances, indices = self.index.search(query_embedding, search_k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0 and idx < len(self.metadata):
                meta = self.metadata[idx]
                # STRICT filtering by chat_id - only return messages from the same chat
                if meta.get('chat_id') == chat_id:
                    results.append((meta, float(dist)))
        
        # Return top k results from this specific chat only
        return results[:k]
    
    async def get_user_context(self, user_id: int, chat_id: int, limit: int = 10) -> List[Dict]:
        """Get recent context for a specific user IN A SPECIFIC CHAT"""
        user_messages = [
            meta for meta in self.metadata 
            if meta.get('user_id') == user_id and meta.get('chat_id') == chat_id
        ]
        return user_messages[-limit:]
    
    async def get_chat_context(self, chat_id: int, limit: int = 20) -> List[Dict]:
        """Get recent context for a specific chat ONLY"""
        chat_messages = [
            meta for meta in self.metadata 
            if meta.get('chat_id') == chat_id
        ]
        return chat_messages[-limit:]
    
    async def save(self) -> None:
        """Save index and metadata to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
                
            logger.info(f"Vector store saved: {len(self.metadata)} entries")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
    
    def load(self) -> None:
        """Load index and metadata from disk"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                # Load FAISS index
                self.index = faiss.read_index(self.index_path)
                
                # Load metadata
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                logger.info(f"Vector store loaded: {len(self.metadata)} entries")
        except Exception as e:
            logger.warning(f"Could not load vector store: {e}. Starting fresh.")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []
    
    async def clear(self) -> None:
        """Clear the vector store"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        await self.save()