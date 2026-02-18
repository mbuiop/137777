from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import db, cache, limiter
from app.models import User, Knowledge, Message, Upload
from app.ai_engine import ai
from app.auth import admin_required, create_admin
import os
import time
from datetime import datetime

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__)
api_bp = Blueprint('api', __name__)

# ==================== Main Routes ====================

@main_bp.route('/')
def index():
    return redirect(url_for('main.chat'))

@main_bp.route('/chat')
def chat():
    return render_template('chat.html')

@main_bp.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('main.chat'))
        else:
            flash('❌ نام کاربری یا رمز اشتباه است', 'danger')
    
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('✅ خارج شدید', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('❌ این نام کاربری وجود دارد', 'danger')
            return redirect(url_for('main.register'))
        
        if User.query.filter_by(email=email).first():
            flash('❌ این ایمیل وجود دارد', 'danger')
            return redirect(url_for('main.register'))
        
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('✅ ثبت‌نام موفقیت‌آمیز. حالا وارد شوید.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('register.html')

@main_bp.route('/profile')
@login_required
def profile():
    messages = Message.query.filter_by(user_id=current_user.id).order_by(
        Message.created_at.desc()
    ).limit(50).all()
    
    uploads = Upload.query.filter_by(user_id=current_user.id).order_by(
        Upload.created_at.desc()
    ).limit(20).all()
    
    return render_template('profile.html', 
                         messages=messages, 
                         uploads=uploads)

# ==================== Admin Routes ====================

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    stats = {
        'users': User.query.count(),
        'knowledge': Knowledge.query.count(),
        'messages': Message.query.count(),
        'uploads': Upload.query.count(),
        'active_today': User.query.filter(
            User.last_active >= datetime.utcnow().date()
        ).count()
    }
    
    recent_users = User.query.order_by(
        User.created_at.desc()
    ).limit(10).all()
    
    top_knowledge = Knowledge.query.order_by(
        Knowledge.usage.desc()
    ).limit(10).all()
    
    ai_stats = ai.get_stats()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         top_knowledge=top_knowledge,
                         ai_stats=ai_stats)

@admin_bp.route('/knowledge')
@login_required
@admin_required
def knowledge():
    page = request.args.get('page', 1, type=int)
    knowledge = Knowledge.query.order_by(
        Knowledge.usage.desc()
    ).paginate(page=page, per_page=50)
    
    return render_template('admin/knowledge.html', knowledge=knowledge)

@admin_bp.route('/knowledge/add', methods=['POST'])
@login_required
@admin_required
def add_knowledge():
    question = request.form.get('question')
    answer = request.form.get('answer')
    category = request.form.get('category', 'general')
    
    if question and answer:
        success, message = ai.learn(question, answer, category, 'manual')
        flash(message, 'success' if success else 'danger')
    
    return redirect(url_for('admin.knowledge'))

@admin_bp.route('/knowledge/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_knowledge(id):
    knowledge = db.session.get(Knowledge, id)
    if knowledge:
        db.session.delete(knowledge)
        db.session.commit()
        flash('✅ حذف شد', 'success')
    
    return redirect(url_for('admin.knowledge'))

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(
        User.created_at.desc()
    ).paginate(page=page, per_page=50)
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/uploads')
@login_required
@admin_required
def uploads():
    page = request.args.get('page', 1, type=int)
    uploads = Upload.query.order_by(
        Upload.created_at.desc()
    ).paginate(page=page, per_page=50)
    
    return render_template('admin/uploads.html', uploads=uploads)

@admin_bp.route('/upload', methods=['POST'])
@login_required
@admin_required
def upload_file():
    if 'file' not in request.files:
        flash('❌ فایلی انتخاب نشده', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('❌ فایل خالی است', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    filename = secure_filename(file.filename)
    file_ext = filename.split('.')[-1].lower()
    
    if file_ext not in current_app.config['ALLOWED_EXTENSIONS']:
        flash('❌ فرمت فایل مجاز نیست', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Save file
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    file_size = os.path.getsize(file_path)
    
    # Process with AI
    start_time = time.time()
    extracted = ai.process_file(file_path, filename, current_user.id)
    process_time = time.time() - start_time
    
    # Save to database
    upload = Upload(
        user_id=current_user.id,
        filename=filename,
        file_type=file_ext,
        file_size=file_size,
        processed=True,
        items_extracted=extracted
    )
    db.session.add(upload)
    db.session.commit()
    
    flash(f'✅ {extracted} مورد یادگیری استخراج شد (زمان: {process_time:.2f} ثانیه)', 'success')
    
    return redirect(url_for('admin.dashboard'))

# ==================== API Routes ====================

@api_bp.route('/ask', methods=['POST'])
@limiter.limit("100 per minute")
def ask():
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    # Measure response time
    start_time = time.time()
    answer = ai.think(question, session.get('user_id'))
    response_time = (time.time() - start_time) * 1000  # ms
    
    # Save message if user logged in
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            user.messages_count += 1
            user.last_active = datetime.utcnow()
            
            message = Message(
                user_id=user.id,
                content=question,
                response=answer,
                response_time=response_time,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(message)
            db.session.commit()
    
    return jsonify({
        'answer': answer,
        'response_time': round(response_time, 2),
        'timestamp': datetime.utcnow().isoformat()
    })

@api_bp.route('/feedback', methods=['POST'])
@login_required
def feedback():
    data = request.json
    message_id = data.get('message_id')
    rating = data.get('rating')
    feedback = data.get('feedback')
    
    message = db.session.get(Message, message_id)
    if message and message.user_id == current_user.id:
        message.rating = rating
        message.feedback = feedback
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Message not found'}), 404

@api_bp.route('/stats')
def stats():
    return jsonify(ai.get_stats())

# Create admin on startup
create_admin()
