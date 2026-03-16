"""
Production-grade settings and configuration management
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    app_name: str = Field(default="CO-PO-PSO Mapping Chatbot", env="APP_NAME")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=4)
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False)
    
    # JWT
    secret_key: str = Field(env="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1:8b", env="OLLAMA_MODEL")
    embedding_provider: str = Field(default="gemini", env="EMBEDDING_PROVIDER")
    llm_temperature: float = Field(default=0.3)
    llm_max_tokens: int = Field(default=2000)
    llm_request_timeout_sec: float = Field(default=60.0, env="LLM_REQUEST_TIMEOUT_SEC")
    
    # Pinecone Vector DB
    pinecone_api_key: Optional[str] = Field(default=None, env="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-west1-gcp-free", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="co-po-pso-index", env="PINECONE_INDEX_NAME")
    pinecone_namespace: str = Field(default="academic")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")

    # Redis / Broker
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_stream_prefix: str = Field(default="obe", env="REDIS_STREAM_PREFIX")

    # Celery
    celery_broker_url: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")

    # Neo4j
    neo4j_uri: Optional[str] = Field(default=None, env="NEO4J_URI")
    neo4j_user: Optional[str] = Field(default=None, env="NEO4J_USER")
    neo4j_password: Optional[str] = Field(default=None, env="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", env="NEO4J_DATABASE")

    # Object Storage (MinIO / S3)
    s3_endpoint_url: Optional[str] = Field(default=None, env="S3_ENDPOINT_URL")
    s3_access_key: Optional[str] = Field(default=None, env="S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = Field(default=None, env="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", env="S3_REGION")
    s3_bucket_uploads: str = Field(default="obe-uploads", env="S3_BUCKET_UPLOADS")
    s3_bucket_reports: str = Field(default="obe-reports", env="S3_BUCKET_REPORTS")
    s3_presign_expiry_seconds: int = Field(default=86400, env="S3_PRESIGN_EXPIRY_SECONDS")

    # Elasticsearch
    elasticsearch_url: Optional[str] = Field(default=None, env="ELASTICSEARCH_URL")
    elasticsearch_user: Optional[str] = Field(default=None, env="ELASTICSEARCH_USER")
    elasticsearch_password: Optional[str] = Field(default=None, env="ELASTICSEARCH_PASSWORD")
    elasticsearch_index_questions: str = Field(default="obe_questions", env="ELASTICSEARCH_INDEX_QUESTIONS")
    
    # CORS
    allowed_origins: list = Field(
        default=["*"],
        env="ALLOWED_ORIGINS"
    )
    
    # File Upload
    max_upload_size: int = Field(default=52428800, env="MAX_UPLOAD_SIZE")  # 50MB
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    
    # Academic Thresholds — NBA standard: L3>=60%, L2>=50%, L1<50%
    attainment_level_3_threshold: float = Field(default=0.60, env="ATTAINMENT_LEVEL_3_THRESHOLD")
    attainment_level_2_threshold: float = Field(default=0.50, env="ATTAINMENT_LEVEL_2_THRESHOLD")
    attainment_level_1_threshold: float = Field(default=0.0,  env="ATTAINMENT_LEVEL_1_THRESHOLD")

    # NBA OBE Calculation Settings
    # Direct/Indirect blend: Final_CO = Direct*direct_weight + Indirect*indirect_weight
    co_direct_weight: float = Field(default=0.80, env="CO_DIRECT_WEIGHT")
    co_indirect_weight: float = Field(default=0.20, env="CO_INDIRECT_WEIGHT")
    # Default CO attainment threshold (students must score >= this fraction of CO max marks)
    co_attainment_threshold: float = Field(default=0.40, env="CO_ATTAINMENT_THRESHOLD")
    # Best-N-of-M rule for formative assessments (T1-T5)
    fa_best_n: int = Field(default=3, env="FA_BEST_N")   # take best N
    fa_total_m: int = Field(default=5, env="FA_TOTAL_M")  # out of M tests
    # CO target level for gap analysis (faculty sets target before course starts)
    co_target_level: int = Field(default=2, env="CO_TARGET_LEVEL")  # 1/2/3
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        if not (v.startswith("postgresql://") or v.startswith("postgresql+asyncpg://")):
            raise ValueError("Database URL must use PostgreSQL")
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
