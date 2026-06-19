"""
Unified Vector Database Manager
Handles ChromaDB
"""

import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
import numpy as np
import chromadb

logger = logging.getLogger(__name__)

class VectorDatabase(ABC):
    """Abstract base class for vector databases"""
    
    def __init__(self, config: Dict[str, Any], db_name: str):
        self.config = config
        self.db_name = db_name
        self.vector_dimension = 384  # sentence-transformers default
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the database"""
        pass
    
    @abstractmethod
    def create_collection(self, collection_name: str) -> bool:
        """Create a collection/index"""
        pass
    
    @abstractmethod
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Insert chunks into the database"""
        pass
    
    @abstractmethod
    def create_index(self, index_type: str) -> bool:
        """Create an index (flat, hnsw, ivf)"""
        pass
    
    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "flat", metadata_filter: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict], float]:
        """Search for similar vectors, return (results, query_time)"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass


class ChromaDatabase(VectorDatabase):
    """ChromaDB vector database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "chromadb")
        self.client = None
        self.collections = {}
        self.storage_path = Path(config.get('storage_path', 'data/chroma_db'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def connect(self) -> bool:
        """Connect to ChromaDB"""
        try:
            self.client = chromadb.PersistentClient(path=str(self.storage_path))
            logger.info("ChromaDB connected successfully")
            
            # Try to load existing collection
            try:
                self.collections['default'] = self.client.get_collection("document_chunks")
                logger.info("ChromaDB: loaded existing collection 'document_chunks'")
            except Exception:
                logger.info("ChromaDB: no existing collection found (will be created on first upload)")
                
            return True
        except Exception as e:
            logger.error(f"ChromaDB connection error: {e}")
            return False
    
    def create_collection(self, collection_name: str = "document_chunks") -> bool:
        """Create ChromaDB collection"""
        try:
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            collection = self.client.create_collection(collection_name)
            self.collections['default'] = collection
            logger.info(f"ChromaDB collection '{collection_name}' created")
            return True
        except Exception as e:
            logger.error(f"ChromaDB collection creation error: {e}")
            return False
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Insert chunks into ChromaDB"""
        try:
            collection = self.collections['default']
            
            # Prepare data for ChromaDB
            ids = [chunk['chunk_id'] for chunk in chunks]
            embeddings = [chunk['embedding'] for chunk in chunks]
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [{
                'source_document': chunk['source_document'],
                'chunk_type': chunk['chunk_type'],
                'page_numbers': str(chunk['page_numbers']),
                'metadata': json.dumps(chunk.get('metadata', {}))
            } for chunk in chunks]
            
            # Insert in batches to avoid memory issues
            batch_size = 1000
            for i in range(0, len(chunks), batch_size):
                batch_end = min(i + batch_size, len(chunks))
                collection.add(
                    ids=ids[i:batch_end],
                    embeddings=embeddings[i:batch_end],
                    documents=documents[i:batch_end],
                    metadatas=metadatas[i:batch_end]
                )
            
            logger.info(f"ChromaDB: Inserted {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"ChromaDB insert error: {e}")
            return False
    
    def create_index(self, index_type: str) -> bool:
        """ChromaDB handles indexing automatically"""
        logger.info(f"ChromaDB: Index type '{index_type}' handled automatically")
        return True
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "flat", metadata_filter: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict], float]:
        """Search in ChromaDB"""
        start_time = time.time()
        
        try:
            collection = self.collections.get('default')
            if not collection:
                logger.warning("ChromaDB search: No collection loaded.")
                return [], time.time() - start_time
            
            kwargs = {
                "query_embeddings": [query_vector.tolist()],
                "n_results": top_k
            }
            if metadata_filter:
                kwargs["where"] = metadata_filter
                
            results = collection.query(**kwargs)
            
            # Handle case where n_results > number of documents in collection
            if not results['ids'] or not results['ids'][0]:
                return [], time.time() - start_time
                
            formatted_results = []
            for i, (doc_id, document, metadata, distance) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                result = {
                    'chunk_id': doc_id,
                    'text': document,
                    'source_document': metadata['source_document'],
                    'chunk_type': metadata['chunk_type'],
                    'page_numbers': eval(metadata['page_numbers']),
                    'metadata': json.loads(metadata['metadata']),
                    'similarity_score': 1 - distance,  # Convert distance to similarity
                    'rank': i + 1
                }
                formatted_results.append(result)
            
            query_time = time.time() - start_time
            return formatted_results, query_time
            
        except Exception as e:
            logger.error(f"ChromaDB search error: {e}")
            return [], time.time() - start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ChromaDB statistics"""
        try:
            collection = self.collections.get('default')
            count = collection.count() if collection else 0
            return {
                'database': 'ChromaDB',
                'total_vectors': count,
                'vector_dimension': self.vector_dimension,
                'available_indexes': ['auto'],
                'storage_path': str(self.storage_path)
            }
        except:
            return {'database': 'ChromaDB', 'error': 'Stats unavailable'}

class VectorDatabaseManager:
    """Manager for Vector database"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.databases = {}
        self.chunks_loaded = False
        
        # Initialize database connection
        self._initialize_databases()
    
    def _initialize_databases(self):
        """Initialize all database connections"""
        logger.info("Initializing vector databases...")
        
        # ChromaDB (local)
        chroma_config = self.config.get('chromadb', {})
        self.databases['chromadb'] = ChromaDatabase(chroma_config)
        
        # Test connections
        for name, db in self.databases.items():
            if db.connect():
                logger.info(f"✅ {name.upper()} connected")
            else:
                logger.warning(f"⚠️ {name.upper()} not available")
    
    def setup_all_databases(self, chunks: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Setup all databases with chunks"""
        results = {}
        
        for name, db in self.databases.items():
            logger.info(f"Setting up {name.upper()}...")
            try:
                # Create collection
                if db.create_collection():
                    # Insert chunks
                    if db.insert_chunks(chunks):
                        # Create indexes
                        db.create_index('flat')
                        results[name] = True
                        logger.info(f"✅ {name.upper()} setup complete")
                    else:
                        results[name] = False
                        logger.error(f"❌ {name.upper()} chunk insertion failed")
                else:
                    results[name] = False
                    logger.error(f"❌ {name.upper()} collection creation failed")
            except Exception as e:
                results[name] = False
                logger.error(f"❌ {name.upper()} setup error: {e}")
        
        self.chunks_loaded = any(results.values())
        return results
    
    def get_database(self, db_name: str) -> VectorDatabase:
        """Get a specific database instance"""
        if db_name not in self.databases:
            raise ValueError(f"Database {db_name} not available")
        return self.databases[db_name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all databases"""
        stats = {}
        for name, db in self.databases.items():
            stats[name] = db.get_stats()
        return stats
