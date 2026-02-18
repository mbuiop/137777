from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import redis
import os
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions (بدون limiter)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()

def create_app(config_class=None):
    app = Flask(__name__, 
                instance_relative_config=True,
                template_folder='templates',
                static_folder='static')
    
    # Load config
    if config_class is None:
        app.config.from_object('config.Config')
    else:
        app.config.from_object(config_class)
    
    # Initialize basic extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'لطفا وارد شوید'
    
    migrate.init_app(app, db)
    cache.init_app(app)
    csrf.init_app(app)
    
    # Setup rate limiter (اختیاری)
    try:
        limiter = Limiter(
            get_remote_address,
            app=app,
            storage_uri=app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
            strategy='fixed-window'
        )
        app.limiter = limiter
        print("✅ Rate limiter initialized")
    except Exception as e:
        app.limiter = None
        print(f"⚠️ Rate limiter not initialized: {e}")
    
    # Redis client
    try:
        app.redis_client = redis.Redis.from_url(
            app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
            decode_responses=True,
            socket_keepalive=True,
            socket_timeout=5
        )
        print("✅ Redis client initialized")
    except Exception as e:
        app.redis_client = None
        print(f"⚠️ Redis not available: {e}")
    
    # Setup logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        app.config.get('LOG_FILE', 'logs/app.log'),
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('🚀 Mega AI System Started')
    
    # Register blueprints
    try:
        from app.routes import main_bp, admin_bp, api_bp
        app.register_blueprint(main_bp)
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(api_bp, url_prefix='/api')
        print("✅ Blueprints registered")
    except Exception as e:
        print(f"⚠️ Blueprint registration error: {e}")
    
    # Create upload folder
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    
    return app
