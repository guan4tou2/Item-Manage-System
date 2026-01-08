"""Application configuration validation using pydantic"""
from typing import Optional, List
from pydantic import BaseModel, Field, validator, EmailStr, HttpUrl
import os


class DatabaseConfig(BaseModel):
    """Database configuration"""
    db_type: str = Field(default="postgres", description="Database type: postgres or mongo")
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    mongo_uri: Optional[str] = Field(default=None, description="MongoDB connection URI")

    @validator('database_url')
    def validate_postgres_url(cls, v):
        if v is not None and not v.startswith(('postgresql://', 'postgresql+')):
            raise ValueError('PostgreSQL URL must start with postgresql:// or postgresql+://')
        return v

    @validator('mongo_uri')
    def validate_mongo_uri(cls, v):
        if v is not None and not v.startswith(('mongodb://', 'mongodb+')):
            raise ValueError('MongoDB URI must start with mongodb:// or mongodb+://')
        return v


class ServerConfig(BaseModel):
    """Server configuration"""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    workers: int = Field(default=4, ge=1, le=32, description="Number of Gunicorn workers")
    threads: int = Field(default=2, ge=1, le=8, description="Number of Gunicorn threads per worker")
    secret_key: str = Field(..., min_length=32, description="Application secret key")

    @validator('secret_key')
    def validate_secret_key(cls, v):
        if v in ['dev-secret-key', 'change-in-production', 'secret']:
            raise ValueError('SECRET_KEY must not be a default value')
        return v


class CacheConfig(BaseModel):
    """Cache configuration"""
    cache_type: str = Field(default="RedisCache", description="Cache type")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    default_timeout: int = Field(default=300, ge=1, le=3600, description="Default cache timeout in seconds")


class MailConfig(BaseModel):
    """Email notification configuration"""
    server: str = Field(..., description="SMTP server address")
    port: int = Field(default=587, ge=1, le=65535, description="SMTP port")
    use_tls: bool = Field(default=True, description="Use TLS for SMTP")
    username: EmailStr = Field(..., description="SMTP username")
    password: str = Field(..., min_length=1, description="SMTP password")
    default_sender: EmailStr = Field(..., description="Default sender email address")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    default_limits: List[str] = Field(
        default=["200 per day", "50 per hour"],
        description="Default rate limits"
    )
    storage_uri: str = Field(default="memory://", description="Rate limit storage URI")


class AppConfig(BaseModel):
    """Application configuration"""

    # Environment
    flask_env: str = Field(default="production", description="Flask environment: development or production")

    # Database
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # Server
    server: ServerConfig = Field(default_factory=ServerConfig)

    # Cache
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # Mail
    mail: Optional[MailConfig] = Field(default=None, description="Email notification configuration")

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Paths
    upload_folder: str = Field(
        default="/workspace/static/uploads",
        description="Upload folder path"
    )

    @validator('database')
    def validate_database_config(cls, v):
        if v.db_type == "postgres" and not v.database_url:
            raise ValueError('DATABASE_URL is required when using PostgreSQL')
        if v.db_type == "mongo" and not v.mongo_uri:
            raise ValueError('MONGO_URI is required when using MongoDB')
        return v

    @validator('server')
    def validate_server_config(cls, v):
        if v.debug and v.secret_key in ['dev-secret-key', 'change-in-production', 'secret']:
            raise ValueError('Insecure configuration: Debug mode with default secret key not allowed')
        return v

    @validator('mail')
    def validate_mail_config(cls, v):
        if v.username and '@example.com' in v.username:
            raise ValueError('Example email addresses are not allowed in production')
        return v

    class Config:
        """Nested config for easier environment variable access"""
        class Database:
            DB_TYPE: str = "postgres"
            DATABASE_URL: Optional[str] = None
            MONGO_URI: Optional[str] = None

        class Server:
            HOST: str = "0.0.0.0"
            PORT: int = 8080
            DEBUG: bool = False
            GUNICORN_WORKERS: int = 4
            GUNICORN_THREADS: int = 2
            SECRET_KEY: str = ""

        class Cache:
            CACHE_TYPE: str = "RedisCache"
            REDIS_URL: str = "redis://localhost:6379/0"
            CACHE_DEFAULT_TIMEOUT: int = "300"

        class Mail:
            MAIL_SERVER: Optional[str] = None
            MAIL_PORT: int = 587
            MAIL_USE_TLS: str = "true"
            MAIL_USERNAME: Optional[str] = None
            MAIL_PASSWORD: Optional[str] = None
            MAIL_DEFAULT_SENDER: Optional[str] = None

        class RateLimit:
            DEFAULT_LIMITS: str = "200 per day, 50 per hour"
            STORAGE_URI: str = "redis://localhost:6379/0"

        UPLOAD_FOLDER: str = "/workspace/static/uploads"

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration from environment variables with validation"""
        return cls(
            flask_env=os.environ.get("FLASK_ENV", "production"),
            database=DatabaseConfig(
                db_type=os.environ.get("DB_TYPE", "postgres"),
                database_url=os.environ.get("DATABASE_URL"),
                mongo_uri=os.environ.get("MONGO_URI")
            ),
            server=ServerConfig(
                host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8080")),
                debug=os.environ.get("DEBUG", "False").lower() == "true",
                workers=int(os.environ.get("GUNICORN_WORKERS", "4")),
                threads=int(os.environ.get("GUNICORN_THREADS", "2")),
                secret_key=os.environ.get("SECRET_KEY", "")
            ),
            cache=CacheConfig(
                cache_type=os.environ.get("CACHE_TYPE", "RedisCache"),
                redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                default_timeout=int(os.environ.get("CACHE_DEFAULT_TIMEOUT", "300"))
            ),
            mail=MailConfig(
                server=os.environ.get("MAIL_SERVER"),
                port=int(os.environ.get("MAIL_PORT", "587")),
                use_tls=os.environ.get("MAIL_USE_TLS", "true").lower() == "true",
                username=os.environ.get("MAIL_USERNAME"),
                password=os.environ.get("MAIL_PASSWORD"),
                default_sender=os.environ.get("MAIL_DEFAULT_SENDER")
            ),
            rate_limit=RateLimitConfig(
                default_limits=os.environ.get("DEFAULT_LIMITS", "200 per day, 50 per hour"),
                storage_uri=os.environ.get("STORAGE_URI", "redis://localhost:6379/0")
            ),
            upload_folder=os.environ.get("UPLOAD_FOLDER", "/workspace/static/uploads")
        )

    @classmethod
    def validate(cls) -> dict:
        """Validate current configuration and return errors"""
        try:
            config = cls.load()
            return {"valid": True, "config": config.model_dump()}
        except Exception as e:
            return {"valid": False, "errors": str(e)}
