import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-minimum-123456")
os.environ.setdefault("DB_TYPE", "postgres")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
os.environ.setdefault("CACHE_TYPE", "SimpleCache")
os.environ.setdefault("DEFAULT_LIMITS", "200 per day,50 per hour")
os.environ.setdefault("STORAGE_URI", "memory://")
os.environ.setdefault("LIMITER_STORAGE_URI", "memory://")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("TEST_MODE", "true")
