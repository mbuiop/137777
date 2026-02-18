"""
MEGA AI SYSTEM - Professional Version
Supports millions of users, advanced AI, file learning, Persian language support
"""

import os
import json
import time
import hashlib
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from logging.handlers import RotatingFileHandler

import redis
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

# AI Libraries
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    AI_READY = True
except ImportError:
    AI_READY = False
    print("⚠️ AI libraries not fully installed")

# File processing libraries
try:
    import PyPDF2
    import docx
    import pandas as pd
    FILE_PROCESSING = True
except ImportError:
    FILE_PROCESSING = False

# ==================== Configuration ====================
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'megasecretkey2026')
    
    # Database - PostgreSQL for millions of users
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///megadb.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 100,
        'max_overflow': 200,
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Redis for caching and rate limiting
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Cache settings
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 600
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = '1000 per minute'
    
    # Upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024 * 1024  # 1GB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'xlsx', 'json'}
    
    # AI Settings
    AI_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'  # Supports Persian
    AI_CACHE_SIZE = 100000
    AI_BATCH_SIZE = 64
    AI_MAX_LENGTH = 512
    
    # Admin credentials
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'

# ==================== Initialize App ====================
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
cache = Cache(app)

# Redis client
redis_client = redis.Redis.from_url(
    app.config['REDIS_URL'],
    decode_responses=True,
    socket_keepalive=True,
    socket_timeout=5
)

# Rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=app.config['REDIS_URL'],
    strategy='fixed-window'
)

# Setup logging
if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler(
    'logs/megai.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Create upload folder
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# ==================== Database Models ====================
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    messages_count = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

class Knowledge(db.Model):
    __tablename__ = 'knowledge'
    
    id = db.Column(db.BigInteger, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    language = db.Column(db.String(10), default='fa')
    confidence = db.Column(db.Float, default=1.0)
    source = db.Column(db.String(200))
    usage = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    embedding = db.Column(db.Text)  # Store embedding as JSON

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), index=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    response_time = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Upload(db.Model):
    __tablename__ = 'uploads'
    
    id = db.Column(db.BigInteger, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.BigInteger)
    items_extracted = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== AI Engine ====================
class MegaAI:
    def __init__(self):
        self.name = "MegaAI"
        self.version = "3.0"
        self.lock = threading.RLock()
        self.stats = defaultdict(int)
        self.stats['start_time'] = time.time()
        self.cache = {}
        
        # Persian stopwords for better understanding
        self.persian_stopwords = {
            'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'را',
            'است', 'می', 'های', 'ها', 'کرد', 'شود', 'شده', 'نیز', 'یا',
            'اما', 'اگر', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی', 'بود',
            'دارد', 'کنید', 'شما', 'ما', 'ایشان', 'آنها', 'خواهد', 'باشند',
            'کردن', 'داشتن', 'گفتن', 'رفتن', 'آمدن', 'دادن', 'گرفتن'
        }
        
        if AI_READY:
            self._init_ai()
    
    def _init_ai(self):
        try:
            self.model = SentenceTransformer(Config.AI_MODEL_NAME)
            self.dimension = self.model.get_sentence_embedding_dimension()
            
            # FAISS index for fast similarity search
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIDMap(self.index)
            self.knowledge_map = {}
            
            self._load_knowledge()
            app.logger.info(f"✅ AI initialized with dimension {self.dimension}")
        except Exception as e:
            app.logger.error(f"❌ AI initialization failed: {e}")
    
    def _load_knowledge(self):
        """Load all knowledge into FAISS index"""
        try:
            with app.app_context():
                knowledge = Knowledge.query.all()
                
                if not knowledge:
                    return
                
                embeddings = []
                ids = []
                
                for k in knowledge:
                    if k.question and len(k.question) > 3:
                        emb = self.model.encode(k.question)
                        embeddings.append(emb)
                        ids.append(k.id)
                        self.knowledge_map[k.id] = k
                
                if embeddings:
                    embeddings_array = np.array(embeddings).astype('float32')
                    ids_array = np.array(ids).astype('int64')
                    self.index.add_with_ids(embeddings_array, ids_array)
                    
                    redis_client.set('ai:total_items', len(embeddings))
                    app.logger.info(f"✅ Loaded {len(embeddings)} knowledge items")
                    
        except Exception as e:
            app.logger.error(f"❌ Failed to load knowledge: {e}")
    
    def detect_language(self, text):
        """Detect if text is Persian or English"""
        if re.search('[\u0600-\u06FF]', text):
            return 'fa'
        return 'en'
    
    def preprocess_text(self, text):
        """Clean and prepare text for analysis"""
        text = text.strip()
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        # Handle Persian specific characters
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        
        return text
    
    @cache.memoize(timeout=300)
    def think(self, question, user_id=None):
        """Get answer for question with caching"""
        self.stats['total_queries'] += 1
        question = self.preprocess_text(question)
        
        # Check local cache
        cache_key = hashlib.md5(question.encode()).hexdigest()
        cached = redis_client.get(f'answer:{cache_key}')
        if cached:
            self.stats['cache_hits'] += 1
            return cached
        
        # FAISS search
        if AI_READY and hasattr(self, 'index') and self.index.ntotal > 0:
            q_emb = self.model.encode(question).astype('float32').reshape(1, -1)
            scores, indices = self.index.search(q_emb, 5)
            
            if scores[0][0] > 0.65:  # Similarity threshold
                knowledge_id = indices[0][0]
                if knowledge_id in self.knowledge_map:
                    knowledge = self.knowledge_map[knowledge_id]
                    
                    # Update usage count
                    self._update_usage(knowledge_id)
                    
                    # Cache result
                    redis_client.setex(f'answer:{cache_key}', 600, knowledge.answer)
                    
                    self.stats['faiss_hits'] += 1
                    return knowledge.answer
        
        # Database search
        return self._db_search(question, cache_key)
    
    def _db_search(self, question, cache_key):
        """Fallback database search"""
        with app.app_context():
            try:
                # Get most used knowledge
                knowledge = Knowledge.query.order_by(
                    Knowledge.usage.desc()
                ).limit(100).all()
                
                best_match = None
                best_score = 0
                q_words = set(question.split())
                
                for k in knowledge:
                    k_words = set(k.question.split())
                    common = q_words.intersection(k_words)
                    score = len(common)
                    
                    if score > best_score and score > 1:
                        best_score = score
                        best_match = k
                
                if best_match:
                    self._update_usage(best_match.id)
                    redis_client.setex(f'answer:{cache_key}', 600, best_match.answer)
                    return best_match.answer
                    
            except Exception as e:
                app.logger.error(f"DB search error: {e}")
        
        return "متوجه نشدم. میشه بیشتر توضیح بدید؟"
    
    def _update_usage(self, knowledge_id):
        """Update knowledge usage count in background"""
        try:
            with app.app_context():
                knowledge = db.session.get(Knowledge, knowledge_id)
                if knowledge:
                    knowledge.usage += 1
                    db.session.commit()
        except:
            pass
    
    def learn(self, question, answer, category='general', source='manual'):
        """Add new knowledge"""
        with self.lock:
            try:
                language = self.detect_language(question)
                
                knowledge = Knowledge(
                    question=question,
                    answer=answer,
                    category=category,
                    language=language,
                    source=source,
                    confidence=1.0
                )
                
                db.session.add(knowledge)
                db.session.commit()
                
                # Update FAISS
                if AI_READY and hasattr(self, 'index'):
                    emb = self.model.encode(question).astype('float32').reshape(1, -1)
                    self.index.add_with_ids(emb, np.array([knowledge.id]))
                    self.knowledge_map[knowledge.id] = knowledge
                
                self.stats['total_learns'] += 1
                return True, "✅ یاد گرفتم!"
                
            except Exception as e:
                app.logger.error(f"Learn error: {e}")
                return False, str(e)
    
    def process_file(self, file_path, filename):
        """Extract knowledge from file"""
        extracted = 0
        file_ext = filename.split('.')[-1].lower()
        
        if not FILE_PROCESSING:
            return 0
        
        try:
            text = ""
            
            # Extract text based on file type
            if file_ext == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            elif file_ext == 'pdf':
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    for page in pdf.pages:
                        text += page.extract_text()
            
            elif file_ext == 'docx':
                doc = docx.Document(file_path)
                text = '\n'.join([p.text for p in doc.paragraphs])
            
            elif file_ext == 'csv':
                df = pd.read_csv(file_path)
                text = df.to_string()
            
            # Extract QA pairs
            if text and len(text) > 100:
                sentences = sent_tokenize(text)
                
                for i, sent in enumerate(sentences):
                    if '?' in sent or '؟' in sent:
                        for j in range(i+1, min(i+3, len(sentences))):
                            answer = sentences[j].strip()
                            if answer and len(answer) > 20:
                                success, _ = self.learn(
                                    sent[:500], 
                                    answer[:500], 
                                    category='file',
                                    source=filename
                                )
                                if success:
                                    extracted += 1
                                break
            
            return extracted
            
        except Exception as e:
            app.logger.error(f"File processing error: {e}")
            return 0
    
    def get_stats(self):
        """Get AI statistics"""
        runtime = time.time() - self.stats['start_time']
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)
        
        with app.app_context():
            total = Knowledge.query.count()
        
        return {
            'total_knowledge': total,
            'total_queries': self.stats['total_queries'],
            'cache_hits': self.stats['cache_hits'],
            'faiss_hits': self.stats.get('faiss_hits', 0),
            'total_learns': self.stats['total_learns'],
            'runtime': f"{hours}h {minutes}m"
        }

# Initialize AI
ai = MegaAI()

# ==================== Routes ====================
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def index():
    return redirect(url_for('chat'))

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            user.last_active = datetime.utcnow()
            db.session.commit()
            
            flash('✅ ورود موفقیت‌آمیز', 'success')
            
            if user.is_admin:
                return redirect(url_for('admin'))
            return redirect(url_for('chat'))
        else:
            flash('❌ نام کاربری یا رمز اشتباه است', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('chat'))
    
    stats = {
        'users': User.query.count(),
        'knowledge': Knowledge.query.count(),
        'messages': Message.query.count(),
        'uploads': Upload.query.count(),
        'active_24h': User.query.filter(
            User.last_active >= datetime.utcnow() - timedelta(hours=24)
        ).count()
    }
    
    ai_stats = ai.get_stats()
    
    return render_template('admin.html', stats=stats, ai_stats=ai_stats)

@app.route('/api/ask', methods=['POST'])
@limiter.limit("100 per minute")
def api_ask():
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question required'}), 400
    
    start_time = time.time()
    answer = ai.think(question, session.get('user_id'))
    response_time = (time.time() - start_time) * 1000
    
    # Save message if user logged in
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            user.messages_count += 1
            user.last_active = datetime.utcnow()
            
            message = Message(
                user_id=user.id,
                question=question,
                answer=answer,
                response_time=response_time
            )
            db.session.add(message)
            db.session.commit()
    
    return jsonify({
        'answer': answer,
        'time': round(response_time, 2)
    })

@app.route('/api/learn', methods=['POST'])
@login_required
def api_learn():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    category = data.get('category', 'general')
    
    if question and answer:
        success, message = ai.learn(question, answer, category)
        return jsonify({'success': success, 'message': message})
    
    return jsonify({'error': 'Invalid data'}), 400

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty file'}), 400
    
    filename = secure_filename(file.filename)
    file_ext = filename.split('.')[-1].lower()
    
    if file_ext not in Config.ALLOWED_EXTENSIONS:
        return jsonify({'error': 'File type not allowed'}), 400
    
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    
    extracted = ai.process_file(file_path, filename)
    
    upload = Upload(
        filename=filename,
        file_type=file_ext,
        file_size=file_size,
        items_extracted=extracted
    )
    db.session.add(upload)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'extracted': extracted,
        'message': f'✅ {extracted} مورد یادگیری استخراج شد'
    })

@app.route('/api/stats')
def api_stats():
    return jsonify(ai.get_stats())

# ==================== Create Admin ====================
def create_admin():
    with app.app_context():
        db.create_all()
        
        admin = User.query.filter_by(username=Config.ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=Config.ADMIN_USERNAME,
                password=generate_password_hash(Config.ADMIN_PASSWORD),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info("✅ Admin created: admin/admin123")

# ==================== Run ====================
if __name__ == '__main__':
    create_admin()
    app.logger.info("="*60)
    app.logger.info("🚀 MEGA AI SYSTEM STARTED")
    app.logger.info("="*60)
    app.logger.info("🌐 http://localhost:5000/chat")
    app.logger.info("👤 Admin: admin/admin123")
    app.logger.info("="*60)
    
    app.run(host='0.0.0.0', port=5000, threaded=True)
