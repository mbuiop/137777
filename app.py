from flask import Flask, request, jsonify, redirect, session, render_template_string
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from brain import app as brain_app, knowledge_base
from brain import learn_from_file, chat as chat_page
from database import db, User, KnowledgeDB
from ai_engine import ai
from cache import RedisCache
import config
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# ==================== راه‌اندازی ====================
app = Flask(__name__)
app.config.from_object(config.Config)

# دیتابیس
db.init_app(app)

# محدود کننده
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri=app.config['REDIS_URL']
)

# کش
cache = RedisCache()

# ==================== مسیرها ====================
@app.route('/')
def home():
    return redirect('/chat')

@app.route('/chat')
def chat():
    return chat_page()

@app.route('/ask', methods=['POST'])
@limiter.limit("100 per minute")
def ask():
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'سوال را وارد کنید'}), 400
    
    # جستجو با هوش مصنوعی
    answer = ai.search(question, session.get('user_id'))
    
    return jsonify({'answer': answer})

@app.route('/admin/learn', methods=['POST'])
def admin_learn():
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    category = data.get('category', 'general')
    
    if question and answer:
        ai.learn(question, answer, category)
        return jsonify({'success': True, 'message': '✅ یاد گرفتم!'})
    
    return jsonify({'success': False, 'message': '❌ خطا'})

@app.route('/admin/upload', methods=['POST'])
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '❌ فایلی نیست'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '❌ فایل خالی'})
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # یادگیری از فایل
    extracted = learn_from_file(filepath, filename)
    
    return jsonify({'success': True, 'message': f'✅ {extracted} مورد یاد گرفتم'})

@app.route('/stats')
def stats():
    return jsonify(ai.get_stats())

# ==================== اجرا ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("="*60)
        print("🚀 MEGA AI SYSTEM - READY FOR MILLIONS")
        print("="*60)
        print(f"📊 حافظه اصلی: {len(knowledge_base)} مورد")
        print(f"⚡ کش: {cache.get_stats()['connected']}")
        print(f"📦 دیتابیس: PostgreSQL")
        print("="*60)
    
    app.run(host='0.0.0.0', port=5000, threaded=True)
