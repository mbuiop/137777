from m1_app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

class Knowledge(db.Model):
    __tablename__ = 'knowledge'
    __table_args__ = (
        db.Index('idx_question_search', 'question'),
        {'extend_existing': True}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False, index=True)
    answer = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), default='general', index=True)
    usage = db.Column(db.Integer, default=0, index=True)
    confidence = db.Column(db.Float, default=1.0)
    source = db.Column(db.String(200), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    __table_args__ = (
        db.Index('idx_user_created', 'user_id', 'created_at'),
        {'extend_existing': True}
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

print("✅ مدل‌های دیتابیس آماده شد")
