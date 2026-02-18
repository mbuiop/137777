from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from datetime import datetime
import os
import redis

app = Flask(__name__)

# ========== کلید امنیتی ==========
app.config['SECRET_KEY'] = 'your-super-secret-key-change-this-123456'

# ========== دیتابیس PostgreSQL ==========
# برای میلیون کاربر باید از PostgreSQL استفاده کنیم
POSTGRES = {
    'user': 'postgres',
    'pw': 'password',
    'db': 'aidb',
    'host': 'localhost',
    'port': '5432',
}
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========== تنظیمات حرفه‌ای برای میلیون کاربر ==========
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 50,              # اندازه استخر اتصال
    'max_overflow': 100,           # حداکثر اتصال اضافی
    'pool_pre_ping': True,         # بررسی سلامت اتصال
    'pool_recycle': 300,            # بازسازی اتصال هر ۵ دقیقه
    'pool_timeout': 30,             # زمان انتظار برای اتصال
    'echo': False                    # لاگ نگیر
}

# ========== Redis برای کش ==========
app.config['CACHE_TYPE'] = 'RedisCache'
app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'
app.config['CACHE_DEFAULT_TIMEOUT'] = 600
cache = Cache(app)

# ========== Redis برای session ==========
redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

# ========== دیتابیس ==========
db = SQLAlchemy(app)

# ========== پوشه آپلود ==========
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

print("✅ PostgreSQL آماده شد")
print("✅ Redis آماده شد")
