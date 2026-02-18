from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from datetime import datetime
import os

app = Flask(__name__)

# ========== تنظیمات پیشرفته ==========
app.config['SECRET_KEY'] = 'your-secret-key-123456'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}

# ========== کش ==========
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

# ========== دیتابیس ==========
db = SQLAlchemy(app)

# ========== پوشه آپلود ==========
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
