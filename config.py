import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'your-secret-key-here-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///ai_chat.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # حافظه 10 گیگابایتی
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024  # 10GB
    
    # تنظیمات آپلود فایل
    UPLOAD_FOLDER = 'uploads/training_data'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'json'}
    
    # تنظیمات کش و حافظه
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_HOST = 'localhost'
    CACHE_REDIS_PORT = 6379
    CACHE_DEFAULT_TIMEOUT = 300
    
    # تنظیمات Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # تنظیمات هوش مصنوعی
    AI_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
    AI_MAX_HISTORY = 1000
    AI_TEMPERATURE = 0.7
    AI_TOP_K = 5
