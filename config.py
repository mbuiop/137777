import os
from datetime import timedelta

class Config:
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-production'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Database (PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:password@localhost:5432/megadb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 100,
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'max_overflow': 200,
        'pool_timeout': 30,
        'echo': False
    }
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Cache
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 600
    CACHE_KEY_PREFIX = 'mega_'
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = '200 per minute'
    RATELIMIT_HEADERS_ENABLED = True
    
    # Upload
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'xlsx', 'json', 'md'}
    
    # AI Config
    AI_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    AI_CACHE_SIZE = 100000
    AI_BATCH_SIZE = 64
    AI_MAX_LENGTH = 512
    
    # Pagination
    ITEMS_PER_PAGE = 50
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'
    
    # Admin
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'  # Change in production
