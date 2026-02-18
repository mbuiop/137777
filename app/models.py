from app import db
from flask_login import UserMixin
from datetime import datetime
import json

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Stats
    messages_count = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    messages = db.relationship('Message', backref='user', lazy='dynamic')
    uploads = db.relationship('Upload', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Knowledge(db.Model):
    __tablename__ = 'knowledge'
    __table_args__ = (
        db.Index('idx_question_search', 'question'),
        db.Index('idx_category_usage', 'category', 'usage'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general', index=True)
    
    # Metadata
    language = db.Column(db.String(10), default='fa')
    confidence = db.Column(db.Float, default=1.0)
    source = db.Column(db.String(200))
    source_type = db.Column(db.String(20))  # 'manual', 'file', 'api'
    
    # Stats
    usage = db.Column(db.Integer, default=0, index=True)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Vector embedding (for AI)
    embedding = db.Column(db.Text)  # JSON string
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'confidence': self.confidence
        }

class Message(db.Model):
    __tablename__ = 'messages'
    __table_args__ = (
        db.Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Content
    content = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    response_time = db.Column(db.Float)  # milliseconds
    
    # Feedback
    rating = db.Column(db.Integer)  # 1-5
    feedback = db.Column(db.Text)
    
    # Metadata
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Upload(db.Model):
    __tablename__ = 'uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    filename = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)  # bytes
    
    # Processing
    processed = db.Column(db.Boolean, default=False)
    items_extracted = db.Column(db.Integer, default=0)
    error = db.Column(db.Text)
    
    # Stats
    download_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'processed': self.processed,
            'items_extracted': self.items_extracted,
            'created_at': self.created_at.isoformat()
        }

class Analytics(db.Model):
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # Counters
    total_queries = db.Column(db.Integer, default=0)
    unique_users = db.Column(db.Integer, default=0)
    total_uploads = db.Column(db.Integer, default=0)
    total_knowledge = db.Column(db.Integer, default=0)
    
    # Performance
    avg_response_time = db.Column(db.Float, default=0)
    cache_hit_rate = db.Column(db.Float, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
