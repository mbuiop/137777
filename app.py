from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
import json

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
    return db.session.get(User, int(user_id))

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
    ai_stats = ai_model.get_stats() if hasattr(ai_model, 'get_stats') else {}
    
    return render_template('admin.html', 
                         total_users=total_users,
                         total_messages=total_messages,
                         unanswered_messages=unanswered_messages,
                         total_training=total_training,
                         ai_stats=ai_stats)

# بقیه route ها...

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
            print("User admin created successfully!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
