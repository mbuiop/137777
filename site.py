from flask import Flask, request, jsonify, redirect, render_template_string
from textblob import TextBlob
import nltk
import json
import hashlib
from difflib import SequenceMatcher
from nltk.tokenize import word_tokenize, sent_tokenize
from werkzeug.utils import secure_filename
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import PyPDF2
import docx
import csv
app = Flask(__name__)

# دانلود داده‌های مورد نیاز NLTK
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 مگابایت
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'json'}
os.makedirs('uploads', exist_ok=True)

# ==================== دیتابیس حافظه ====================
knowledge_base = {}
file_history = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def extract_sentences(text):
    try:
        return sent_tokenize(text)
    except:
        return text.split('\n')

# ==================== توابع یادگیری ====================
def learn_from_text(question, answer, source='manual'):
    """یادگیری مستقیم از متن"""
    knowledge_base[question] = {
        'answer': answer,
        'source': source,
        'learned_at': str(datetime.now()),
        'usage': 0
    }
    auto_save()
    return True

def learn_from_file(filepath, filename):
    """یادگیری از فایل آپلود شده"""
    extracted = 0
    file_ext = filename.rsplit('.', 1)[1].lower()
    content = ""
    
    try:
        # خوندن فایل بر اساس نوع
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
        
        # استخراج جملات
        sentences = extract_sentences(content)
        print(f"✅ تعداد جملات استخراج شده: {len(sentences)}")
        
        # پیدا کردن سوال و جواب
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if len(sent) < 10:
                continue
                
            # اگه جمله سوال بود
            if '?' in sent or '؟' in sent:
                # جواب می‌تونه جمله بعدی باشه
                if i + 1 < len(sentences):
                    answer = sentences[i + 1].strip()
                    if answer and len(answer) > 10:
                        learn_from_text(sent, answer, f'file:{filename}')
                        extracted += 1
        
        # ذخیره تاریخچه فایل
        file_history.append({
            'filename': filename,
            'extracted': extracted,
            'time': str(datetime.now())
        })
        
        return extracted
        
    except Exception as e:
        print(f"خطا در خوندن فایل: {e}")
        return 0

def smart_search(user_question):
    """جستجوی هوشمند با مقایسه شباهت"""
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

def detect_question_type(text):
    if any(word in text for word in ['قیمت', 'چنده', 'چقدر']):
        return 'price'
    if any(word in text for word in ['چیست', 'کیه', 'چی']):
        return 'definition'
    if any(word in text for word in ['چرا', 'چطور', 'چگونه']):
        return 'reason'
    return 'general'

def save_knowledge():
    with open('knowledge_base.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False)

def load_knowledge():
    global knowledge_base
    try:
        with open('knowledge_base.json', 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
    except:
        knowledge_base = {}

def auto_save():
    save_knowledge()
    print("✅ حافظه ذخیره شد")

# ==================== صفحات اصلی ====================
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
            *{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
            body{height:100vh;display:flex;background:linear-gradient(135deg,#1a237e,#0d47a1);}
            .chat{width:100%;height:100%;display:flex;flex-direction:column;background:white;}
            .header{padding:20px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;display:flex;justify-content:space-between;align-items:center;}
            .header h2{display:flex;align-items:center;gap:10px;}
            .menu-btn{background:rgba(255,255,255,0.2);border:none;color:white;padding:10px 20px;border-radius:30px;cursor:pointer;font-size:16px;}
            .menu-dropdown{position:absolute;top:80px;left:20px;background:white;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,0.2);display:none;}
            .menu-dropdown.show{display:block;}
            .menu-item{padding:15px 30px;color:#333;text-decoration:none;display:block;border-bottom:1px solid #eee;}
            .menu-item:hover{background:#f5f5f5;}
            .messages{flex:1;overflow-y:auto;padding:20px;background:#f5f7fa;}
            .message{margin:15px 0;display:flex;}
            .message.user{justify-content:flex-end;}
            .message.bot{justify-content:flex-start;}
            .message-content{max-width:70%;padding:12px 18px;border-radius:20px;word-wrap:break-word;}
            .user .message-content{background:#1a237e;color:white;border-bottom-right-radius:5px;}
            .bot .message-content{background:white;color:#333;border-bottom-left-radius:5px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}
            .input-area{padding:20px;background:white;border-top:1px solid #eee;}
            .input-wrapper{display:flex;gap:10px;}
            input{flex:1;padding:15px;border:2px solid #ddd;border-radius:30px;font-size:16px;outline:none;}
            input:focus{border-color:#1a237e;}
            button{padding:15px 30px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;border:none;border-radius:30px;font-size:16px;cursor:pointer;transition:transform 0.2s;}
            button:hover{transform:scale(1.05);}
            .time{font-size:11px;opacity:0.7;margin-top:5px;}
        </style>
    </head>
    <body>
        <div class="chat">
            <div class="header">
                <h2>🤖 هوش مصنوعی پیشرفته</h2>
                <button class="menu-btn" onclick="toggleMenu()">☰ منو</button>
            </div>
            
            <div class="menu-dropdown" id="menu">
                <a href="/chat" class="menu-item">🏠 صفحه چت</a>
                <a href="/admin" class="menu-item">⚙️ پنل مدیریت</a>
            </div>
            
            <div class="messages" id="messages">
                <div class="message bot">
                    <div class="message-content">
                        سلام! من یک هوش مصنوعی هستم. هر سوالی داری بپرس
                        <div class="time">الان</div>
                    </div>
                </div>
            </div>
            
            <div class="input-area">
                <div class="input-wrapper">
                    <input type="text" id="question" placeholder="سوال خود را بنویسید..." autofocus>
                    <button onclick="sendMessage()">ارسال</button>
                </div>
            </div>
        </div>

        <script>
            function toggleMenu() {
                document.getElementById('menu').classList.toggle('show');
            }

            async function sendMessage() {
                let q = document.getElementById('question').value.trim();
                if (!q) return;

                let messages = document.getElementById('messages');
                let time = new Date().toLocaleTimeString('fa-IR');

                messages.innerHTML += `
                    <div class="message user">
                        <div class="message-content">
                            ${escapeHtml(q)}
                            <div class="time">${time}</div>
                        </div>
                    </div>
                `;

                document.getElementById('question').value = '';
                messages.scrollTop = messages.scrollHeight;

                let response = await fetch('/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q})
                });

                let data = await response.json();

                messages.innerHTML += `
                    <div class="message bot">
                        <div class="message-content">
                            ${escapeHtml(data.answer)}
                            <div class="time">${time}</div>
                        </div>
                    </div>
                `;
                messages.scrollTop = messages.scrollHeight;
            }

            function escapeHtml(unsafe) {
                return unsafe.replace(/[&<>"]/g, function(m) {
                    if(m == '&') return '&amp;'; if(m == '<') return '&lt;'; if(m == '>') return '&gt;'; if(m == '"') return '&quot;';
                    return m;
                });
            }

            document.getElementById('question').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    '''

# ==================== پنل مدیریت ====================
@app.route('/admin')
def admin():
    knowledge_list = ''
    for i, (q, data) in enumerate(list(knowledge_base.items())[:10]):
        knowledge_list += f'<tr><td>{i+1}</td><td>{q[:50]}...</td><td>{data["answer"][:50]}...</td><td>{data["usage"]}</td></tr>'
    
    file_list = ''
    for f in file_history[-5:]:
        file_list += f'<tr><td>{f["filename"]}</td><td>{f["extracted"]}</td><td>{f["time"]}</td></tr>'
    
    return f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>پنل مدیریت</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box;font-family:system-ui;}}
            body{{background:linear-gradient(135deg,#1a237e,#0d47a1);padding:20px;}}
            .container{{max-width:1200px;margin:0 auto;background:white;border-radius:20px;padding:30px;box-shadow:0 20px 60px rgba(0,0,0,0.3);}}
            h1{{color:#1a237e;margin-bottom:30px;}}
            .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:30px;}}
            .stat-card{{background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;padding:20px;border-radius:15px;text-align:center;}}
            .stat-number{{font-size:32px;font-weight:bold;}}
            .section{{background:#f5f7fa;padding:25px;border-radius:15px;margin-bottom:30px;}}
            h2{{color:#1a237e;margin-bottom:20px;}}
            input,textarea,select{{width:100%;padding:12px;margin:10px 0;border:2px solid #ddd;border-radius:10px;font-size:16px;}}
            button{{padding:12px 30px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;border:none;border-radius:10px;font-size:16px;cursor:pointer;}}
            .file-upload{{border:3px dashed #1a237e;padding:40px;text-align:center;border-radius:15px;cursor:pointer;margin:20px 0;}}
            table{{width:100%;border-collapse:collapse;margin-top:20px;}}
            th{{background:#1a237e;color:white;padding:12px;}}
            td{{border:1px solid #ddd;padding:10px;}}
            .back{{margin-top:20px;text-align:center;}}
            .back a{{color:#1a237e;text-decoration:none;}}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚙️ پنل مدیریت هوش مصنوعی</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{len(knowledge_base)}</div>
                    <div>تعداد دانش</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{sum(d['usage'] for d in knowledge_base.values())}</div>
                    <div>کل استفاده</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(file_history)}</div>
                    <div>فایل‌های آپلود شده</div>
                </div>
            </div>
            
            <div class="section">
                <h2>📚 آموزش دستی</h2>
                <input type="text" id="question" placeholder="سوال">
                <textarea id="answer" placeholder="جواب" rows="3"></textarea>
                <button onclick="manualLearn()">✅ یاد بده</button>
                <p id="manualMsg" style="color:green;margin-top:10px;"></p>
            </div>
            
            <div class="section">
                <h2>📁 آپلود فایل</h2>
                <div class="file-upload" onclick="document.getElementById('file').click()">
                    📤 کلیک کنید یا فایل را اینجا رها کنید<br>
                    <small>فرمت‌های مجاز: txt, pdf, docx, csv, json</small>
                </div>
                <input type="file" id="file" style="display:none" onchange="uploadFile()">
                <div id="uploadProgress" style="margin-top:20px;display:none;">
                    <div style="width:100%;height:20px;background:#f0f0f0;border-radius:10px;overflow:hidden;">
                        <div id="progressBar" style="width:0%;height:100%;background:linear-gradient(135deg,#1a237e,#0d47a1);"></div>
                    </div>
                    <p id="uploadStatus">در حال پردازش...</p>
                </div>
                <p id="uploadMsg" style="color:green;margin-top:10px;"></p>
            </div>
            
            <div class="section">
                <h2>📖 آخرین فایل‌های آپلود شده</h2>
                <table>
                    <tr><th>نام فایل</th><th>تعداد یادگیری</th><th>زمان</th></tr>
                    {file_list if file_list else '<tr><td colspan="3" style="text-align:center;">هیچ فایلی آپلود نشده</td></tr>'}
                </table>
            </div>
            
            <div class="section">
                <h2>📖 دانش‌های ذخیره شده</h2>
                <table>
                    <tr><th>#</th><th>سوال</th><th>جواب</th><th>استفاده</th></tr>
                    {knowledge_list if knowledge_list else '<tr><td colspan="4" style="text-align:center;">هیچ دانشی ثبت نشده</td></tr>'}
                </table>
            </div>
            
            <div class="back">
                <a href="/chat">🔙 بازگشت به صفحه چت</a>
            </div>
        </div>
        
        <script>
            async function manualLearn() {{
                let q = document.getElementById('question').value;
                let a = document.getElementById('answer').value;
                
                let response = await fetch('/admin/learn', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{question: q, answer: a}})
                }});
                
                let data = await response.json();
                document.getElementById('manualMsg').innerHTML = data.message;
                
                if(data.success) {{
                    document.getElementById('question').value = '';
                    document.getElementById('answer').value = '';
                    setTimeout(() => location.reload(), 1000);
                }}
            }}
            
            async function uploadFile() {{
                let file = document.getElementById('file').files[0];
                let formData = new FormData();
                formData.append('file', file);
                
                document.getElementById('uploadProgress').style.display = 'block';
                
                let response = await fetch('/admin/upload', {{
                    method: 'POST',
                    body: formData
                }});
                
                let data = await response.json();
                document.getElementById('uploadMsg').innerHTML = data.message;
                document.getElementById('uploadProgress').style.display = 'none';
                
                if(data.success) {{
                    setTimeout(() => location.reload(), 1000);
                }}
            }}
        </script>
    </body>
    </html>
    '''

# ==================== API ها ====================
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '')
    
    # جستجوی هوشمند
    answer = smart_search(question)
    
    return jsonify({'answer': answer})

@app.route('/admin/learn', methods=['POST'])
def admin_learn():
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    
    if question and answer:
        learn_from_text(question, answer)
        return jsonify({'success': True, 'message': '✅ یاد گرفتم!'})
    
    return jsonify({'success': False, 'message': '❌ لطفاً سوال و جواب را وارد کنید'})

@app.route('/admin/upload', methods=['POST'])
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '❌ فایلی انتخاب نشده'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '❌ فایل خالی است'})
    
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'message': '❌ فرمت فایل مجاز نیست'})
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # یادگیری از فایل
    extracted = learn_from_file(filepath, filename)
    
    return jsonify({'success': True, 'message': f'✅ {extracted} مورد یادگیری از فایل استخراج شد'})

# بارگذاری دانش قبلی
load_knowledge()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
