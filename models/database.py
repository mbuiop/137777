from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Index, text
import json

db = SQLAlchemy()

class Knowledge(db.Model):
    """مدل اصلی دانش - با ایندکس‌های بهینه برای جستجوی سریع"""
    __tablename__ = 'knowledge'
    __table_args__ = (
        Index('idx_question_vector', 'question_vector', mysql_prefix='FULLTEXT'),
        Index('idx_keywords', 'keywords'),
        Index('idx_usage_count', 'usage_count'),
        Index('idx_confidence', 'confidence'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    question_hash = db.Column(db.String(64), unique=True, index=True)  # برای جستجوی سریع
    question_vector = db.Column(db.Text)  # برداری از کلمات (برای جستجوی پیشرفته)
    question_length = db.Column(db.Integer, default=0)
    
    answer = db.Column(db.Text, nullable=False)
    answer_summary = db.Column(db.String(200))  # خلاصه جواب برای نمایش سریع
    answer_length = db.Column(db.Integer, default=0)
    
    keywords = db.Column(db.Text)  # کلمات کلیدی به صورت JSON
    important_words = db.Column(db.Text)  # کلمات مهم
    
    source_file = db.Column(db.String(200))
    source_line = db.Column(db.Integer)
    
    confidence = db.Column(db.Float, default=1.0)  # میزان اطمینان
    quality_score = db.Column(db.Float, default=1.0)  # امتیاز کیفیت
    
    usage_count = db.Column(db.BigInteger, default=0)  # تعداد استفاده
    success_count = db.Column(db.BigInteger, default=0)  # تعداد پاسخ‌های موفق
    fail_count = db.Column(db.BigInteger, default=0)  # تعداد پاسخ‌های ناموفق
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    last_used_at = db.Column(db.DateTime)
    
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question[:100],
            'answer': self.answer[:100],
            'confidence': self.confidence,
            'usage': self.usage_count,
            'quality': self.quality_score
        }
    
    def update_usage(self, success=True):
        self.usage_count += 1
        self.last_used_at = datetime.now()
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1

class FileLearningHistory(db.Model):
    """تاریخچه یادگیری از فایل‌ها"""
    __tablename__ = 'file_history'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), index=True)
    file_size = db.Column(db.BigInteger)
    total_lines = db.Column(db.Integer)
    extracted_count = db.Column(db.Integer)
    learned_count = db.Column(db.Integer)
    status = db.Column(db.String(50))  # success, partial, failed
    error_message = db.Column(db.Text)
    processing_time = db.Column(db.Float)  # زمان پردازش به ثانیه
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'filename': self.filename,
            'learned': self.learned_count,
            'time': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class ChatHistory(db.Model):
    """تاریخچه مکالمات - با پارتیشن‌بندی زمانی"""
    __tablename__ = 'chat_history'
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_user_id', 'user_id'),
    )
    
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.String(100), index=True)  # آی‌دی کاربر (برای تحلیل)
    session_id = db.Column(db.String(100), index=True)
    
    question = db.Column(db.Text)
    question_length = db.Column(db.Integer)
    
    answer = db.Column(db.Text)
    answer_id = db.Column(db.Integer, db.ForeignKey('knowledge.id'))
    answer_type = db.Column(db.String(20))  # exact, similar, new
    
    confidence = db.Column(db.Float)
    response_time = db.Column(db.Float)  # زمان پاسخگویی
    
    user_rating = db.Column(db.Integer)  # امتیاز کاربر (1-5)
    user_feedback = db.Column(db.Text)  # بازخورد کاربر
    
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'question': self.question[:50],
            'answer': self.answer[:50],
            'confidence': self.confidence,
            'time': self.created_at.strftime('%H:%M')
        }

class KnowledgeStats(db.Model):
    """آمار و تحلیل دانش"""
    __tablename__ = 'knowledge_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    total_knowledge = db.Column(db.BigInteger, default=0)
    total_answers = db.Column(db.BigInteger, default=0)
    avg_confidence = db.Column(db.Float, default=0)
    avg_response_time = db.Column(db.Float, default=0)
    popular_questions = db.Column(db.Text)  # JSON
    weak_points = db.Column(db.Text)  # JSON - نقاط ضعف
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
