from flask import Blueprint, request, jsonify, session
from core.brain import Brain
from utils.logger import logger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

chat_bp = Blueprint('chat', __name__)
brain = Brain()

# محدود کننده درخواست
limiter = Limiter(key_func=get_remote_address)

@chat_bp.route('/ask', methods=['POST'])
@limiter.limit("30/minute")  # هر آیپی 30 تا در دقیقه
def ask():
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'answer': '❌ لطفاً یک سوال وارد کنید'
            })
        
        # دریافت user_id از session (اگر لاگین باشد)
        user_id = session.get('user_id', 'anonymous')
        
        # فکر کردن و پاسخ دادن
        result = brain.think(question, user_id)
        
        # لاگ کردن
        logger.info(f"Question: {question[:50]}... -> Answer: {result['answer'][:50]}...")
        
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'confidence': result.get('confidence', 0),
            'suggestions': result.get('suggestions', [])
        })
        
    except Exception as e:
        logger.error(f"Error in ask: {e}")
        return jsonify({
            'success': False,
            'answer': '❌ خطای داخلی سرور. لطفاً دوباره تلاش کنید.'
        }), 500

@chat_bp.route('/feedback', methods=['POST'])
def feedback():
    """دریافت بازخورد از کاربر"""
    try:
        data = request.json
        answer_id = data.get('answer_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback')
        
        # ذخیره بازخورد
        from models.database import ChatHistory, db
        chat = ChatHistory.query.filter_by(answer_id=answer_id).first()
        if chat:
            chat.user_rating = rating
            chat.user_feedback = feedback_text
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False}), 500
