from flask import Blueprint, request, jsonify, session
from core.brain import Brain
from models.database import Knowledge, FileLearningHistory, ChatHistory, db
from utils.logger import logger
from werkzeug.utils import secure_filename
import os
from config import Config

admin_bp = Blueprint('admin', __name__)
brain = Brain()

# بررسی احراز هویت
def login_required(f):
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/learn', methods=['POST'])
@login_required
def learn():
    """یادگیری دستی"""
    try:
        data = request.json
        question = data.get('question')
        answer = data.get('answer')
        
        if not question or not answer:
            return jsonify({
                'success': False,
                'message': '❌ سوال و جواب را وارد کنید'
            })
        
        result = brain.learn(question, answer)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Learn error: {e}")
        return jsonify({
            'success': False,
            'message': f'❌ خطا: {str(e)}'
        })

@admin_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """آپلود فایل برای یادگیری"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '❌ فایلی انتخاب نشده'
            })
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '❌ فایل خالی است'
            })
        
        # بررسی فرمت
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext not in Config.ALLOWED_EXTENSIONS:
            return jsonify({
                'success': False,
                'message': f'❌ فرمت {ext} مجاز نیست'
            })
        
        # ذخیره فایل
        filename = secure_filename(file.filename)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # یادگیری از فایل
        result = brain.learn_from_file(filepath, filename)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({
            'success': False,
            'message': f'❌ خطا: {str(e)}'
        })

@admin_bp.route('/knowledge', methods=['GET'])
@login_required
def get_knowledge():
    """دریافت لیست دانش‌ها"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    knowledge = Knowledge.query.filter_by(is_active=True)\
        .order_by(Knowledge.usage_count.desc())\
        .paginate(page=page, per_page=per_page)
    
    return jsonify({
        'items': [k.to_dict() for k in knowledge.items],
        'total': knowledge.total,
        'pages': knowledge.pages,
        'current': page
    })

@admin_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """دریافت آمار"""
    stats = {
        'total_knowledge': Knowledge.query.filter_by(is_active=True).count(),
        'total_files': FileLearningHistory.query.count(),
        'total_chats': ChatHistory.query.count(),
        'brain_stats': brain.get_stats()
    }
    return jsonify(stats)

@admin_bp.route('/forget/<int:knowledge_id>', methods=['DELETE'])
@login_required
def forget(knowledge_id):
    """فراموش کردن یک دانش"""
    if brain.forget(knowledge_id):
        return jsonify({'success': True})
    return jsonify({'success': False}), 404
