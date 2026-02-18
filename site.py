from flask import Flask, request, jsonify
from textblob import TextBlob
import nltk
import json
import hashlib
from difflib import SequenceMatcher
from nltk.tokenize import word_tokenize
from werkzeug.utils import secure_filename
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
app = Flask(__name__)

# دانلود داده‌های مورد نیاز NLTK
nltk.download('punkt', quiet=True)

app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
os.makedirs('uploads', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

knowledge_base = {}

def find_best_answer(user_question):
    if user_question in knowledge_base:
        return knowledge_base[user_question]
    return "نمی‌دونم. میشه بیشتر توضیح بدی؟"

def save_knowledge():
    with open('knowledge.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False)

def load_knowledge():
    global knowledge_base
    try:
        with open('knowledge_10gb.json', 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
    except:
        knowledge_base = {}

def auto_save():
    with open('knowledge_10gb_backup.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False)
    print("✅ حافظه ذخیره شد")

def smart_search(user_question):
    best_match = None
    best_ratio = 0
    for question in knowledge_base.keys():
        ratio = SequenceMatcher(None, user_question.lower(), question.lower()).ratio()
        if ratio > best_ratio and ratio > 0.6:
            best_ratio = ratio
            best_match = question
    if best_match:
        return knowledge_base[best_match]
    
    if len(knowledge_base) > 0:
        questions = list(knowledge_base.keys())
        return questions[0]
    return None

def detect_question_type(text):
    if any(word in text for word in ['قیمت', 'چنده', 'چقدر']):
        return 'price'
    if any(word in text for word in ['چیست', 'کیه', 'چی']):
        return 'definition'
    if any(word in text for word in ['چرا', 'چطور', 'چگونه']):
        return 'reason'
    return 'general'

user_questions_log = []
def log_user_question(question):
    user_questions_log.append({'question': question, 'time': str(datetime.now())})
    if len(user_questions_log) > 1000:
        user_questions_log.pop(0)

@app.route('/')
def home():
    return redirect('/chat')

@app.route('/chat')
def chat():
    return '''
    <html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
    <style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
    body{height:100vh;display:flex;background:linear-gradient(135deg,#1a237e,#0d47a1);}
    .chat{width:100%;height:100%;display:flex;flex-direction:column;background:white;}</style></head>
    <body><div class="chat"><div style="padding:20px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;display:flex;justify-content:space-between;align-items:center">
    <h2>🤖 هوش مصنوعی</h2><div><a href="/admin" style="color:white;margin-right:20px;">⚙️</a></div></div>
    <div id="messages" style="flex:1;overflow-y:auto;padding:20px"></div>
    <div style="padding:20px;border-top:1px solid #eee"><input id="q" style="width:80%;padding:15px;border:2px solid #ddd;border-radius:30px;font-size:16px;" placeholder="سوال خود را بپرسید...">
    <button onclick="send()" style="width:18%;padding:15px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;border:none;border-radius:30px;font-size:16px;cursor:pointer;">ارسال</button></div></div>
    <script>function send(){let q=document.getElementById('q').value;if(!q)return;let m=document.getElementById('messages');m.innerHTML+='<div style="text-align:right;margin:10px"><span style="background:#1a237e;color:white;padding:12px 18px;border-radius:20px;display:inline-block;max-width:70%;">'+q+'</span></div>';
    document.getElementById('q').value='';fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:q})})
    .then(r=>r.json()).then(d=>{m.innerHTML+='<div style="text-align:left;margin:10px"><span style="background:#f0f0f0;padding:12px 18px;border-radius:20px;display:inline-block;max-width:70%;">'+d.a+'</span></div>';m.scrollTop=m.scrollHeight;});}</script></body></html>
    '''

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('q', '')
    
    # ذخیره سوال کاربر
    log_user_question(question)
    
    # تشخیص نوع سوال
    q_type = detect_question_type(question)
    
    # جستجوی هوشمند
    answer = smart_search(question)
    
    return jsonify({'a': answer, 'type': q_type})

@app.route('/admin')
def admin():
    return f'''
    <html><head><style>body{{font-family:system-ui;padding:20px;}}</style></head>
    <body><h2>پنل مدیریت</h2>
    <p>تعداد دانش: {len(knowledge_base)}</p>
    <p>سوالات امروز: {len(user_questions_log)}</p>
    <a href="/chat">بازگشت به چت</a>
    </body></html>
    '''

# بارگذاری دانش قبلی
load_knowledge()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
