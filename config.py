import os
from datetime import timedelta

class Config:
    # امنیت
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # دیتابیس (برای میلیون‌ها کاربر)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ai_brain.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 40
    }
    
    # Redis برای کش (برای سرعت بالا)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CACHE_TYPE = 'RedisCache'
    CACHE_DEFAULT_TIMEOUT = 3600
    
    # محدودیت درخواست (برای جلوگیری از DoS)
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "100/minute"
    RATELIMIT_STORAGE_URL = REDIS_URL
    
    # آپلود فایل
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv'}
    
    # تنظیمات مغز هوش مصنوعی
    BRAIN_CONFIG = {
        'similarity_threshold': 0.65,      # آستانه شباهت
        'max_results': 5,                   # حداکثر نتایج
        'use_stemming': True,                # استفاده از ریشه‌یابی
        'use_synonyms': True,                # استفاده از مترادف
        'cache_size': 10000,                  # حجم کش
        'vector_dimension': 300,              # ابعاد برداری
        'batch_size': 1000,                   # اندازه بatch برای پردازش
        'parallel_workers': 4,                 # تعداد پردازنده‌های موازی
        'answer_quality_threshold': 0.8       # آستانه کیفیت جواب
    }
    
    # نشانگر جواب در فایل‌ها
    ANSWER_MARKER = '!این'  # هر جا این بود یعنی جواب
    
    # ایجاد پوشه‌ها
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
