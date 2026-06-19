from pydantic_settings import BaseSettings
from typing import List, Union

class Settings(BaseSettings):
    # API Meta
    API_TITLE: str = "RAG Pipeline API"
    API_VERSION: str = "1.0.0"
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["*"]

    # Vector DB config
    CHROMA_STORAGE_PATH: str = "./data/chroma_db"
    
    # NLP & Chunking config
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MIN_CHUNK_SIZE: int = 100
    MAX_CHUNK_SIZE: int = 2000
    CHUNK_SIMILARITY_THRESHOLD: float = 0.5
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32
    SPACY_MODEL: str = "en_core_web_sm"
    PROCESSED_DATA_DIR: str = "./data/processed"
    
    # Reranking
    RERANK_ENABLED: bool = True
    RERANK_METHOD: str = "bm25"
    
    # Web Search
    WEB_SEARCH_ENABLED: bool = True
    
    # LLM Provider
    LLM_PROVIDER: str = "groq" # groq, anthropic, ollama, aws, gemini
    
    # Provider specifics
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"
    AWS_BEDROCK_MODEL: str = "anthropic.claude-3-haiku-20240307-v1:0"
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    OLLAMA_MODEL: str = "llama3"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_TEMPERATURE: float = 0.0
    
    class Config:
        env_file = ".env"
        extra = "ignore"
        
    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

settings = Settings()
