"""
Unified Vector Database Manager
Handles FAISS, ChromaDB, Qdrant, and MongoDB with consistent interface
"""

import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
import numpy as np

# Database-specific imports
import faiss
import chromadb
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models
import pymongo
from pymongo import MongoClient

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
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "flat") -> Tuple[List[Dict], float]:
        """Search for similar vectors, return (results, query_time)"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass


class FAISSDatabase(VectorDatabase):
    """FAISS vector database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "faiss")
        self.indexes = {}
        self.chunks_data = []
        self.storage_path = Path(config.get('storage_path', 'data/embeddings/faiss_index'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def connect(self) -> bool:
        """FAISS doesn't need connection, always available"""
        logger.info("FAISS database ready (local)")
        return True
    
    def create_collection(self, collection_name: str = "default") -> bool:
        """Create FAISS indexes"""
        self.collection_name = collection_name
        return True
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Insert chunks and create base indexes"""
        try:
            self.chunks_data = chunks
            vectors = np.array([chunk['embedding'] for chunk in chunks]).astype('float32')
            
            # Create flat index
            flat_index = faiss.IndexFlatIP(self.vector_dimension)
            flat_index.add(vectors)
            self.indexes['flat'] = flat_index
            
            # Create HNSW index
            hnsw_index = faiss.IndexHNSWFlat(self.vector_dimension, 16)
            hnsw_index.add(vectors)
            self.indexes['hnsw'] = hnsw_index
            
            # Create IVF index
            quantizer = faiss.IndexFlatIP(self.vector_dimension)
            ivf_index = faiss.IndexIVFFlat(quantizer, self.vector_dimension, min(100, len(chunks) // 10))
            ivf_index.train(vectors)
            ivf_index.add(vectors)
            self.indexes['ivf'] = ivf_index
            
            logger.info(f"FAISS: Inserted {len(chunks)} chunks with all index types")
            return True
            
        except Exception as e:
            logger.error(f"FAISS insert error: {e}")
            return False
    
    def create_index(self, index_type: str) -> bool:
        """Index creation is handled in insert_chunks for FAISS"""
        return index_type in self.indexes
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "flat") -> Tuple[List[Dict], float]:
        """Search using specified index type"""
        start_time = time.time()
        
        try:
            if index_type not in self.indexes:
                raise ValueError(f"Index type {index_type} not available")
            
            index = self.indexes[index_type]
            query_vector = query_vector.reshape(1, -1).astype('float32')
            
            distances, indices = index.search(query_vector, top_k)
            
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.chunks_data):
                    result = self.chunks_data[idx].copy()
                    result['similarity_score'] = float(distance)
                    result['rank'] = i + 1
                    results.append(result)
            
            query_time = time.time() - start_time
            return results, query_time
            
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return [], time.time() - start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get FAISS statistics"""
        return {
            'database': 'FAISS',
            'total_vectors': len(self.chunks_data),
            'vector_dimension': self.vector_dimension,
            'available_indexes': list(self.indexes.keys()),
            'storage_path': str(self.storage_path)
        }


class ChromaDatabase(VectorDatabase):
    """ChromaDB vector database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "chromadb")
        self.client = None
        self.collections = {}
        self.storage_path = Path(config.get('storage_path', 'data/embeddings/chroma_db'))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def connect(self) -> bool:
        """Connect to ChromaDB"""
        try:
            self.client = chromadb.PersistentClient(path=str(self.storage_path))
            logger.info("ChromaDB connected successfully")
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
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "flat") -> Tuple[List[Dict], float]:
        """Search in ChromaDB"""
        start_time = time.time()
        
        try:
            collection = self.collections['default']
            
            results = collection.query(
                query_embeddings=[query_vector.tolist()],
                n_results=top_k
            )
            
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


class QdrantDatabase(VectorDatabase):
    """Qdrant vector database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "qdrant")
        self.client = None
        self.collection_name = config.get('collection_name', 'document_chunks')
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6333)
        
    def connect(self) -> bool:
        """Connect to Qdrant"""
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Qdrant connected successfully at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Qdrant connection error: {e}")
            return False
    
    def create_collection(self, collection_name: str = None) -> bool:
        """Create Qdrant collection"""
        try:
            collection_name = collection_name or self.collection_name
            
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            # Create new collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_dimension,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Qdrant collection '{collection_name}' created")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant collection creation error: {e}")
            return False
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Insert chunks into Qdrant"""
        try:
            points = []
            for i, chunk in enumerate(chunks):
                point = PointStruct(
                    id=i,
                    vector=chunk['embedding'],
                    payload={
                        'chunk_id': chunk['chunk_id'],
                        'text': chunk['text'],
                        'source_document': chunk['source_document'],
                        'chunk_type': chunk['chunk_type'],
                        'page_numbers': chunk['page_numbers'],
                        'metadata': chunk.get('metadata', {})
                    }
                )
                points.append(point)
            
            # Insert in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
            
            logger.info(f"Qdrant: Inserted {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant insert error: {e}")
            return False
    
    def create_index(self, index_type: str) -> bool:
        """Qdrant handles indexing automatically (HNSW by default)"""
        logger.info(f"Qdrant: Index type '{index_type}' handled automatically (HNSW)")
        return True
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "hnsw") -> Tuple[List[Dict], float]:
        """Search in Qdrant"""
        start_time = time.time()
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                limit=top_k
            )
            
            formatted_results = []
            for i, result in enumerate(results):
                formatted_result = result.payload.copy()
                formatted_result['similarity_score'] = result.score
                formatted_result['rank'] = i + 1
                formatted_results.append(formatted_result)
            
            query_time = time.time() - start_time
            return formatted_results, query_time
            
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return [], time.time() - start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Qdrant statistics"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'database': 'Qdrant',
                'total_vectors': collection_info.points_count,
                'vector_dimension': self.vector_dimension,
                'available_indexes': ['hnsw'],
                'host': self.host,
                'port': self.port
            }
        except Exception as e:
            return {'database': 'Qdrant', 'error': str(e)}


class MongoDatabase(VectorDatabase):
    """MongoDB with vector search implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "mongodb")
        self.client = None
        self.database = None
        self.collection = None
        self.connection_string = config.get('connection_string', 'mongodb://localhost:27017/')
        self.database_name = config.get('database_name', 'rag_evaluation')
        self.collection_name = config.get('collection_name', 'document_chunks')
        
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            # For now, we'll use local MongoDB or skip if not available
            # In production, you'd use MongoDB Atlas with vector search
            self.client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
            # Test connection
            self.client.server_info()
            self.database = self.client[self.database_name]
            self.collection = self.database[self.collection_name]
            logger.info("MongoDB connected successfully")
            return True
        except Exception as e:
            logger.warning(f"MongoDB not available (this is OK for demo): {e}")
            return False
    
    def create_collection(self, collection_name: str = None) -> bool:
        """Create MongoDB collection"""
        if not self.client:
            return False
        
        try:
            collection_name = collection_name or self.collection_name
            self.collection = self.database[collection_name]
            # Drop existing collection
            self.collection.drop()
            logger.info(f"MongoDB collection '{collection_name}' ready")
            return True
        except Exception as e:
            logger.error(f"MongoDB collection creation error: {e}")
            return False
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Insert chunks into MongoDB"""
        if not self.collection:
            return False
        
        try:
            documents = []
            for chunk in chunks:
                doc = {
                    'chunk_id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'source_document': chunk['source_document'],
                    'chunk_type': chunk['chunk_type'],
                    'page_numbers': chunk['page_numbers'],
                    'embedding': chunk['embedding'],
                    'metadata': chunk.get('metadata', {})
                }
                documents.append(doc)
            
            self.collection.insert_many(documents)
            logger.info(f"MongoDB: Inserted {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB insert error: {e}")
            return False
    
    def create_index(self, index_type: str) -> bool:
        """Create text indexes in MongoDB (vector search requires Atlas)"""
        if not self.collection:
            return False
        
        try:
            # Create text index for basic search
            self.collection.create_index([("text", "text")])
            logger.info(f"MongoDB: Created text index (vector search requires Atlas)")
            return True
        except Exception as e:
            logger.error(f"MongoDB index creation error: {e}")
            return False
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, index_type: str = "text") -> Tuple[List[Dict], float]:
        """Basic text search in MongoDB (vector search requires Atlas)"""
        if not self.collection:
            return [], 0.0
        
        start_time = time.time()
        
        try:
            # For demo, return random documents
            results = list(self.collection.aggregate([
                {"$sample": {"size": top_k}},
                {"$project": {"embedding": 0}}  # Exclude embedding from results
            ]))
            
            formatted_results = []
            for i, result in enumerate(results):
                result['similarity_score'] = 0.5  # Dummy score
                result['rank'] = i + 1
                formatted_results.append(result)
            
            query_time = time.time() - start_time
            return formatted_results, query_time
            
        except Exception as e:
            logger.error(f"MongoDB search error: {e}")
            return [], time.time() - start_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get MongoDB statistics"""
        if not self.collection:
            return {'database': 'MongoDB', 'status': 'Not connected'}
        
        try:
            count = self.collection.count_documents({})
            return {
                'database': 'MongoDB',
                'total_vectors': count,
                'vector_dimension': self.vector_dimension,
                'available_indexes': ['text'],
                'note': 'Vector search requires MongoDB Atlas'
            }
        except Exception as e:
            return {'database': 'MongoDB', 'error': str(e)}


class VectorDatabaseManager:
    """Unified manager for all vector databases"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.databases = {}
        self.chunks_loaded = False
        
        # Initialize all database connections
        self._initialize_databases()
    
    def _initialize_databases(self):
        """Initialize all database connections"""
        logger.info("Initializing vector databases...")
        
        # FAISS (always available)
        faiss_config = self.config.get('faiss', {})
        self.databases['faiss'] = FAISSDatabase(faiss_config)
        
        # ChromaDB (local)
        chroma_config = self.config.get('chromadb', {})
        self.databases['chromadb'] = ChromaDatabase(chroma_config)
        
        # Qdrant (Docker)
        qdrant_config = self.config.get('qdrant', {})
        self.databases['qdrant'] = QdrantDatabase(qdrant_config)
        
        # MongoDB (optional)
        mongo_config = self.config.get('mongodb', {})
        self.databases['mongodb'] = MongoDatabase(mongo_config)
        
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
                        db.create_index('hnsw')
                        db.create_index('ivf')
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


# Example usage and testing
if __name__ == "__main__":
    # Test configuration
    config = {
        'faiss': {'storage_path': 'data/embeddings/faiss_index'},
        'chromadb': {'storage_path': 'data/embeddings/chroma_db'},
        'qdrant': {'host': 'localhost', 'port': 6333, 'collection_name': 'document_chunks'},
        'mongodb': {'connection_string': 'mongodb://localhost:27017/', 'database_name': 'rag_evaluation'}
    }
    
    # Load chunks
    chunks_file = Path("data/processed/semantic_chunks.json")
    if chunks_file.exists():
        with open(chunks_file, 'r') as f:
            chunks_data = json.load(f)
        
        chunks = chunks_data['chunks']
        print(f"Loaded {len(chunks)} chunks")
        
        # Test vector database manager
        manager = VectorDatabaseManager(config)
        results = manager.setup_all_databases(chunks)
        
        print("Setup results:", results)
        print("Database stats:", manager.get_all_stats())
    else:
        print("No chunks file found. Run semantic chunking first.")
