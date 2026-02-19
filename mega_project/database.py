from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    messages_count = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class KnowledgeDB(db.Model):
    __tablename__ = 'knowledge_db'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.BigInteger, primary_key=True)
    question = db.Column(db.Text, nullable=False, index=True)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), index=True)
    usage = db.Column(db.BigInteger, default=0, index=True)
    source = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Message(db.Model):
    __tablename__ = 'messages'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), index=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    response_time = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
