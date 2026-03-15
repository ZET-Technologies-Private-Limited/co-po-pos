from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database.models import EmbeddingMetadata
import json


class EmbeddingService:
    """Production-grade embedding service with multi-provider support and RAG"""
    
    def __init__(self, provider: str = "openai"):
        self.settings = get_settings()
        self.logger = SystemLogger("embedding_service")
        self.provider = provider
        self.embeddings = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize embeddings model"""
        try:
            if self.provider == "openai":
                if not self.settings.openai_api_key:
                    self.logger.warning("OpenAI API key not configured")
                    return
                self.embeddings = OpenAIEmbeddings(
                    api_key=self.settings.openai_api_key,
                    model="text-embedding-3-small"
                )
                self.logger.info("OpenAI embeddings initialized")
            
            elif self.provider == "gemini":
                if not self.settings.gemini_api_key:
                    self.logger.warning("Gemini API key not configured")
                    return
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    google_api_key=self.settings.gemini_api_key,
                    model="models/gemini-embedding-001"
                )
                self.logger.info("Gemini embeddings initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings: {str(e)}")
    
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """Generate embedding for single text"""
        if not self.embeddings:
            return None
        
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {str(e)}")
            return None
    
    async def embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings batch"""
        if not self.embeddings:
            return None
        
        try:
            embeddings = self.embeddings.embed_documents(texts)
            return embeddings
        except Exception as e:
            self.logger.error(f"Batch embedding failed: {str(e)}")
            return None
    
    async def store_embeddings(
        self, session: AsyncSession, entity_type: str,
        entity_id: str, text: str
    ) -> Optional[str]:
        """Store embedding in database"""
        try:
            embedding = await self.embed_text(text)
            if not embedding:
                return None
            
            metadata = EmbeddingMetadata(
                id=str(__import__('uuid').uuid4()),
                entity_type=entity_type,
                entity_id=entity_id,
                embedding_id=f"{entity_type}_{entity_id}",
                vector_dimension=len(embedding),
                embedding_model=f"{self.provider}_embedding",
                similarity_scores=json.dumps({})
            )
            session.add(metadata)
            await session.flush()
            
            self.logger.info(f"Embedding stored: {entity_type}_{entity_id}")
            return metadata.id
        except Exception as e:
            self.logger.error(f"Store embedding failed: {str(e)}")
            return None
    
    async def retrieve_similar(
        self, session: AsyncSession, query: str,
        entity_type: str, threshold: float = 0.6,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """RAG: Retrieve similar documents"""
        try:
            query_embedding = await self.embed_text(query)
            if not query_embedding:
                return []
            
            query_arr = np.array(query_embedding)
            
            # Get embeddings from database
            result = await session.execute(
                select(EmbeddingMetadata).where(
                    EmbeddingMetadata.entity_type == entity_type
                )
            )
            embeddings = result.scalars().all()
            
            similarities = []
            for emb in embeddings:
                if not emb.similarity_scores:
                    continue
                
                # Calculate similarity
                similarity = self.cosine_similarity(
                    query_embedding,
                    json.loads(emb.similarity_scores) if isinstance(emb.similarity_scores, str) else emb.similarity_scores
                )
                
                if similarity >= threshold:
                    similarities.append({
                        "entity_id": emb.entity_id,
                        "entity_type": emb.entity_type,
                        "similarity": round(similarity, 4),
                        "embedding_id": emb.embedding_id
                    })
            
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:limit]
        except Exception as e:
            self.logger.error(f"Retrieval failed: {str(e)}")
            return []
    
    @staticmethod
    def cosine_similarity(
        embedding1: List[float], embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity"""
        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)
        
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    @staticmethod
    def batch_cosine_similarity(
        embedding: List[float], embeddings_list: List[List[float]]
    ) -> List[float]:
        """Calculate similarities with batch"""
        arr = np.array(embedding)
        arr_list = np.array(embeddings_list)
        
        similarities = []
        for other in arr_list:
            dot = np.dot(arr, other)
            norm1 = np.linalg.norm(arr)
            norm2 = np.linalg.norm(other)
            similarity = dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
            similarities.append(float(similarity))
        
        return similarities


embedding_service = EmbeddingService(get_settings().embedding_provider)
