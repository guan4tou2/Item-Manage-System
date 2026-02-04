"""測試套件初始化"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-minimum-123456")
os.environ.setdefault("DB_TYPE", "mongo")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/test")
os.environ.setdefault("CACHE_TYPE", "SimpleCache")
