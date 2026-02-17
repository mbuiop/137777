from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bot.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Knowledge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question = db.Column(db.Text)
    answer = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    return 'سلام به ربات من خوش اومدی'
  @app.route('/chat')
def chat():
    return '''
    <html>
        <body>
            <h2>ربات هوش مصنوعی</h2>
            <input id="q" placeholder="سوال خود را بنویس">
            <button onclick="send()">ارسال</button>
            <div id="response"></div>
    '''

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    q = data.get('question')
      know = Knowledge.query.filter_by(question=q).first()
    
    if know:
        answer = know.answer
    else:
        answer = 'نمی‌دونم. به من یاد بده'
    
    return jsonify({'answer': answer})

@app.route('/admin')
def admin():
    return 'پنل مدیریت'
@app.route('/add_knowledge', methods=['POST'])
def add_knowledge():
    data = request.json
    q = data.get('question')
    a = data.get('answer')
    
    know = Knowledge(question=q, answer=a)
    db.session.add(know)
    db.session.commit()
    
    return jsonify({'message': 'یاد گرفتم!'})
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)

# ========== تموم شد ==========
# حالا فایل تو ۷۰ خط تموم شد
