from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid

from config import Config
from models.database import db, User, Message, TrainingData, AIKnowledge
from models.ai_model import ai_model

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ایجاد پوشه‌های مورد نیاز
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    message = data.get('message', '')
    user_id = session.get('user_id')
    
    # دریافت پاسخ از هوش مصنوعی
    response = ai_model.get_response(message, user_id)
    
    # ذخیره در دیتابیس اگر کاربر لاگین کرده
    if user_id:
        msg = Message(
            user_id=user_id,
            content=message,
            response=response,
            is_answered=True
        )
        db.session.add(msg)
        db.session.commit()
    
    return jsonify({
        'response': response,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        return redirect(url_for('chat'))
    
    # آمار کلی
    total_users = User.query.count()
    total_messages = Message.query.count()
    unanswered_messages = Message.query.filter_by(is_answered=False).count()
    total_training = TrainingData.query.count()
    
    # آمار هوش مصنوعی
    ai_stats = ai_model.get_stats()
    
    return render_template('admin.html', 
                         total_users=total_users,
                         total_messages=total_messages,
                         unanswered_messages=unanswered_messages,
                         total_training=total_training,
                         ai_stats=ai_stats)

@app.route('/admin/train/file', methods=['POST'])
@login_required
def train_with_file():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if file_ext not in app.config['ALLOWED_EXTENSIONS']:
        return jsonify({'error': 'File type not allowed'}), 400
    
    # ذخیره فایل
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    try:
        # پردازش با هوش مصنوعی
        num_extracted = ai_model.process_file(file_path, filename)
        
        # ذخیره در دیتابیس
        training = TrainingData(
            filename=filename,
            file_type=file_ext,
            content=f"Processed: {num_extracted} items extracted",
            processed=True,
            metadata=json.dumps({'extracted_count': num_extracted})
        )
        db.session.add(training)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'فایل با موفقیت پردازش شد. {num_extracted} مورد یادگیری استخراج شد.',
            'extracted': num_extracted
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/train/manual', methods=['POST'])
@login_required
def train_manual():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    category = data.get('category', 'manual')
    
    if not question or not answer:
        return jsonify({'error': 'Question and answer are required'}), 400
    
    # اضافه به هوش مصنوعی
    knowledge_id = ai_model.add_knowledge(question, answer, category)
    
    # ذخیره در دیتابیس
    knowledge = AIKnowledge(
        question=question,
        answer=answer,
        category=category,
        source_file='manual'
    )
    db.session.add(knowledge)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'دانش با موفقیت اضافه شد',
        'knowledge_id': knowledge_id
    })

@app.route('/admin/stats')
@login_required
def get_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # آمار کاربران
    users = User.query.all()
    user_stats = [{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'created_at': u.created_at.isoformat(),
        'last_active': u.last_active.isoformat(),
        'message_count': len(u.messages)
    } for u in users]
    
    # پیام‌های بی‌جواب
    unanswered = Message.query.filter_by(is_answered=False).all()
    unanswered_messages = [{
        'id': m.id,
        'user': m.user.username,
        'content': m.content,
        'created_at': m.created_at.isoformat()
    } for m in unanswered]
    
    return jsonify({
        'users': user_stats,
        'unanswered_messages': unanswered_messages,
        'ai_stats': ai_model.get_stats()
    })

@app.route('/admin/knowledge')
@login_required
def get_knowledge():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    knowledge = AIKnowledge.query.order_by(AIKnowledge.usage_count.desc()).limit(100).all()
    
    return jsonify([{
        'id': k.id,
        'question': k.question,
        'answer': k.answer,
        'category': k.category,
        'usage_count': k.usage_count,
        'confidence': k.confidence,
        'created_at': k.created_at.isoformat()
    } for k in knowledge])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_id'] = user.id
            
            # به‌روزرسانی آخرین فعالیت
            user.last_active = datetime.utcnow()
            db.session.commit()
            
            if user.is_admin:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('chat'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # بررسی تکراری نبودن
        if User.query.filter_by(username=username).first():
            return 'Username already exists', 400
        
        if User.query.filter_by(email=email).first():
            return 'Email already exists', 400
        
        # ایجاد کاربر جدید
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_admin=(username == 'admin')  # اولین کاربر admin می‌شود
        )
        
        db.session.add(user)
        db.session.commit()
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # ایجاد کاربر admin پیش‌فرض
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@localhost',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
