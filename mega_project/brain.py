from flask import Flask, request, jsonify, redirect
from textblob import TextBlob
import nltk
import json
import hashlib
from difflib import SequenceMatcher
from nltk.tokenize import word_tokenize, sent_tokenize
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import PyPDF2
import docx
import csv

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'json'}
os.makedirs('uploads', exist_ok=True)

# ==================== حافظه اصلی (۱۰ گیگابایت) ====================
knowledge_base = {}
file_history = []

def read_txt_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def read_pdf_file(filepath):
    text = ""
    with open(filepath, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def read_docx_file(filepath):
    doc = docx.Document(filepath)
    return "\n".join([para.text for para in doc.paragraphs])

def read_csv_file(filepath):
    text = ""
    with open(filepath, 'r', encoding='utf-8') as f:
        csv_reader = csv.reader(f)
        for row in csv_reader:
            text += " ".join(row) + "\n"
    return text

def learn_from_text(question, answer, source='manual'):
    knowledge_base[question] = {
        'answer': answer,
        'source': source,
        'learned_at': str(datetime.now()),
        'usage': 0
    }
    return True

def learn_from_file(filepath, filename):
    extracted = 0
    file_ext = filename.rsplit('.', 1)[1].lower()
    content = ""
    
    try:
        if file_ext == 'txt':
            content = read_txt_file(filepath)
        elif file_ext == 'pdf':
            content = read_pdf_file(filepath)
        elif file_ext == 'docx':
            content = read_docx_file(filepath)
        elif file_ext == 'csv':
            content = read_csv_file(filepath)
        else:
            return 0
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) < 10:
                continue
                
            if '?' in line or '؟' in line or 'چیست' in line or 'کجاست' in line or 'چرا' in line:
                if i + 1 < len(lines):
                    answer = lines[i + 1].strip()
                    if answer and len(answer) > 10:
                        learn_from_text(line, answer, f'file:{filename}')
                        extracted += 1
        
        file_history.append({
            'filename': filename,
            'extracted': extracted,
            'time': str(datetime.now())
        })
        
        return extracted
        
    except Exception as e:
        print(f"خطا: {e}")
        return 0

def smart_search(user_question):
    best_match = None
    best_ratio = 0
    
    for question in knowledge_base.keys():
        ratio = SequenceMatcher(None, user_question.lower(), question.lower()).ratio()
        if ratio > best_ratio and ratio > 0.5:
            best_ratio = ratio
            best_match = question
    
    if best_match:
        knowledge_base[best_match]['usage'] += 1
        return knowledge_base[best_match]['answer']
    
    return "نمی‌دونم. میشه بیشتر توضیح بدی؟"

# ==================== صفحات ====================
@app.route('/')
def home():
    return redirect('/chat')

@app.route('/chat')
def chat():
    return '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
        <title>هوش مصنوعی پیشرفته</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box;font-family:system-ui;}
            body{height:100vh;display:flex;background:linear-gradient(135deg,#1a237e,#0d47a1);}
            .chat{width:100%;height:100%;display:flex;flex-direction:column;background:white;}
            .header{padding:20px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;display:flex;justify-content:space-between;}
            .messages{flex:1;overflow-y:auto;padding:20px;background:#f5f7fa;}
            .message{margin:10px 0;display:flex;}
            .message.user{justify-content:flex-end;}
            .message.bot{justify-content:flex-start;}
            .message-content{max-width:70%;padding:12px 18px;border-radius:20px;}
            .user .message-content{background:#1a237e;color:white;}
            .bot .message-content{background:white;color:#333;box-shadow:0 2px 10px rgba(0,0,0,0.1);}
            .input-area{padding:20px;border-top:1px solid #eee;}
            .input-wrapper{display:flex;gap:10px;}
            input{flex:1;padding:15px;border:2px solid #ddd;border-radius:30px;font-size:16px;}
            button{padding:15px 30px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;border:none;border-radius:30px;cursor:pointer;}
        </style>
    </head>
    <body>
        <div class="chat">
            <div class="header"><h2>🤖 هوش مصنوعی</h2></div>
            <div class="messages" id="messages">
                <div class="message bot"><div class="message-content">سلام! هر سوالی داری بپرس</div></div>
            </div>
            <div class="input-area">
                <div class="input-wrapper">
                    <input type="text" id="question" placeholder="سوال...">
                    <button onclick="send()">ارسال</button>
                </div>
            </div>
        </div>
        <script>
            async function send(){
                let q=document.getElementById('question').value;
                if(!q)return;
                let m=document.getElementById('messages');
                m.innerHTML+='<div class="message user"><div class="message-content">'+q+'</div></div>';
                document.getElementById('question').value='';
                let r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
                let d=await r.json();
                m.innerHTML+='<div class="message bot"><div class="message-content">'+d.answer+'</div></div>';
                m.scrollTop=m.scrollHeight;
            }
        </script>
    </body>
    </html>
    '''
