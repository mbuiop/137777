from flask import Flask, request, jsonify, redirect, render_template_string, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import nltk
import json
import hashlib
from difflib import SequenceMatcher
from nltk.tokenize import word_tokenize, sent_tokenize
import os
import re
import requests
from bs4 import BeautifulSoup
import PyPDF2
import docx
import csv
import random
from urllib.parse import quote
import logging
from functools import wraps
import time

app = Flask(__name__)

# ==================== تنظیمات پایه ====================
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ai_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False  # برای توسعه
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'json'}

# ایجاد پوشه‌ها
os.makedirs('uploads', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# ==================== دیتابیس ====================
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Knowledge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100), default='manual')
    confidence = db.Column(db.Integer, default=100)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'usage': self.usage_count,
            'confidence': self.confidence
        }

class FileHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    extracted_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text)
    answer = db.Column(db.Text)
    answer_type = db.Column(db.String(50))  # google, knowledge, price, error
    created_at = db.Column(db.DateTime, default=datetime.now)

# ==================== ایجاد دیتابیس ====================
with app.app_context():
    db.create_all()
    
    # ایجاد کاربر ادمین پیش‌فرض
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# ==================== لاگینگ ====================
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ==================== دکوریتور احراز هویت ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'unauthorized', 'message': 'لطفا ابتدا وارد شوید'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== کلاس جستجوی گوگل ====================
class GoogleSearcher:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
        ]
        self.trusted_sites = [
            'tgju.org', 'bonbast.com', 'donya-e-eqtesad.com', 'eghtesadnews.com',
            'tabnak.ir', 'irna.ir', 'mehrnews.com', 'farsnews.ir', 'tasnimnews.com',
            'bbc.com', 'isna.ir', 'yjc.ir', 'digiato.com', 'zoomit.ir'
        ]
        self.cache = {}
    
    def _get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept-Language': 'fa,en-US;q=0.9,en;q=0.8',
        }
    
    def search(self, query, num=5):
        cache_key = hashlib.md5(f"{query}_{num}".encode()).hexdigest()
        if cache_key in self.cache:
            cache_time, results = self.cache[cache_key]
            if (datetime.now() - cache_time).seconds < 300:
                return results
        
        try:
            url = f"https://www.google.com/search?q={quote(query)}&num={num}&hl=fa"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for g in soup.find_all('div', class_='g')[:num]:
                try:
                    title = g.find('h3')
                    link = g.find('a')
                    snippet = g.find('div', class_='VwiC3b')
                    
                    if title and link:
                        href = link.get('href', '')
                        if href.startswith('/url?q='):
                            href = href.split('/url?q=')[1].split('&')[0]
                        
                        domain = href.split('/')[2] if '//' in href else ''
                        is_trusted = any(site in domain for site in self.trusted_sites)
                        
                        results.append({
                            'title': title.text,
                            'link': href,
                            'snippet': snippet.text if snippet else '',
                            'domain': domain,
                            'trusted': is_trusted
                        })
                except:
                    continue
            
            self.cache[cache_key] = (datetime.now(), results)
            return results
        except Exception as e:
            logging.error(f"Google search error: {e}")
            return []
    
    def get_price(self, query):
        """دریافت قیمت با جستجوی هدفمند"""
        search_queries = [
            f"قیمت {query} {datetime.now().strftime('%Y/%m/%d')}",
            f"نرخ {query} امروز",
            f"{query} price today"
        ]
        
        all_results = []
        for q in search_queries:
            results = self.search(q, num=3)
            all_results.extend(results)
        
        # استخراج اعداد قیمتی
        price_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(تومان|دلار|ریال|\$)'
        price_data = []
        
        for r in all_results[:5]:
            if r['trusted']:
                prices = re.findall(price_pattern, r['snippet'] + r['title'])
                if prices:
                    price_data.append({
                        'source': r['domain'],
                        'title': r['title'],
                        'prices': prices[:3],
                        'link': r['link']
                    })
        
        return price_data

# ==================== توابع پردازش فایل ====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath, ext):
    try:
        if ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext == 'pdf':
            text = ""
            with open(filepath, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        elif ext == 'docx':
            doc = docx.Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext == 'csv':
            text = ""
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    text += " ".join(row) + "\n"
            return text
        elif ext == 'json':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        logging.error(f"File extraction error: {e}")
        return ""

def extract_qa_from_text(text):
    """استخراج سوال و جواب از متن"""
    lines = text.split('\n')
    qa_pairs = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if len(line) < 10:
            continue
        
        # تشخیص سوال
        is_question = any([
            '?' in line,
            '؟' in line,
            'چیست' in line,
            'کیست' in line,
            'کجاست' in line,
            'چرا' in line,
            'چطور' in line
        ])
        
        if is_question and i + 1 < len(lines):
            answer = lines[i + 1].strip()
            if len(answer) > 20:
                qa_pairs.append({
                    'question': line[:200],
                    'answer': answer[:500]
                })
    
    return qa_pairs

# ==================== روت‌های اصلی ====================
@app.route('/')
def home():
    return redirect('/chat')

@app.route('/chat')
def chat():
    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>هوش مصنوعی پیشرفته</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Vazir', system-ui, sans-serif;
            }
            
            body {
                height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .chat-container {
                width: 90%;
                max-width: 1200px;
                height: 90vh;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .header h1 {
                font-size: 1.5rem;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .menu-btn {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 10px;
                cursor: pointer;
                font-size: 1rem;
            }
            
            .menu-dropdown {
                position: absolute;
                top: 80px;
                left: 20px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                display: none;
                z-index: 1000;
            }
            
            .menu-dropdown.show {
                display: block;
            }
            
            .menu-item {
                padding: 15px 30px;
                color: #333;
                text-decoration: none;
                display: block;
                border-bottom: 1px solid #eee;
                cursor: pointer;
            }
            
            .menu-item:hover {
                background: #f5f5f5;
            }
            
            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #f8f9fa;
            }
            
            .message {
                margin-bottom: 20px;
                display: flex;
            }
            
            .message.user {
                justify-content: flex-end;
            }
            
            .message.bot {
                justify-content: flex-start;
            }
            
            .message-content {
                max-width: 70%;
                padding: 15px 20px;
                border-radius: 15px;
                position: relative;
            }
            
            .user .message-content {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-bottom-right-radius: 5px;
            }
            
            .bot .message-content {
                background: white;
                color: #333;
                border-bottom-left-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .time {
                font-size: 0.75rem;
                opacity: 0.7;
                margin-top: 5px;
            }
            
            .typing-indicator {
                display: flex;
                gap: 5px;
                padding: 15px 20px;
                background: white;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .typing-dot {
                width: 8px;
                height: 8px;
                background: #667eea;
                border-radius: 50%;
                animation: typing 1.4s infinite;
            }
            
            .typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-dot:nth-child(3) { animation-delay: 0.4s; }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
            
            .input-area {
                padding: 20px;
                background: white;
                border-top: 1px solid #eee;
            }
            
            .suggestions {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }
            
            .suggestion-chip {
                padding: 8px 15px;
                background: #f0f2f5;
                border-radius: 20px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: all 0.3s;
            }
            
            .suggestion-chip:hover {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .input-wrapper {
                display: flex;
                gap: 10px;
            }
            
            #question {
                flex: 1;
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 1rem;
                outline: none;
            }
            
            #question:focus {
                border-color: #667eea;
            }
            
            #sendBtn {
                padding: 15px 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                font-size: 1rem;
                transition: transform 0.3s;
            }
            
            #sendBtn:hover {
                transform: scale(1.05);
            }
            
            #sendBtn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="header">
                <h1>
                    🤖 هوش مصنوعی پیشرفته
                    <span style="font-size: 0.8rem; background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 20px;">v3.0</span>
                </h1>
                <button class="menu-btn" onclick="toggleMenu()">☰ منو</button>
            </div>
            
            <div class="menu-dropdown" id="menu">
                <div class="menu-item" onclick="toggleDarkMode()">🌙 حالت شب</div>
                <a href="/login" class="menu-item">⚙️ پنل مدیریت</a>
                <div class="menu-item" onclick="clearChat()">🗑️ پاک کردن چت</div>
            </div>
            
            <div class="messages" id="messages">
                <div class="message bot">
                    <div class="message-content">
                        👋 سلام! به هوش مصنوعی پیشرفته خوش آمدید.<br><br>
                        💡 می‌توانید بپرسید:<br>
                        • قیمت طلا، دلار، سکه، بیت کوین<br>
                        • سوالات عمومی و اطلاعات روز<br>
                        • تعریف مفاهیم و اصطلاحات<br><br>
                        <small>💰 مثال: قیمت طلا امروز چنده؟</small>
                        <div class="time">{{ datetime.now().strftime('%H:%M') }}</div>
                    </div>
                </div>
            </div>
            
            <div class="input-area">
                <div class="suggestions">
                    <span class="suggestion-chip" onclick="useSuggestion('قیمت طلا امروز چنده؟')">💰 قیمت طلا</span>
                    <span class="suggestion-chip" onclick="useSuggestion('دلار چند شد؟')">💵 قیمت دلار</span>
                    <span class="suggestion-chip" onclick="useSuggestion('سکه امامی چند؟')">🪙 سکه امامی</span>
                    <span class="suggestion-chip" onclick="useSuggestion('بیت کوین چند؟')">₿ بیت کوین</span>
                    <span class="suggestion-chip" onclick="useSuggestion('هوش مصنوعی چیست؟')">🤖 تعریف AI</span>
                </div>
                
                <div class="input-wrapper">
                    <input type="text" id="question" placeholder="سوال خود را بپرسید..." autofocus>
                    <button onclick="sendMessage()" id="sendBtn">ارسال</button>
                </div>
            </div>
        </div>
        
        <script>
            let isTyping = false;
            let darkMode = localStorage.getItem('darkMode') === 'true';
            
            if(darkMode) {
                document.body.style.background = '#1a1a1a';
            }
            
            function toggleMenu() {
                document.getElementById('menu').classList.toggle('show');
            }
            
            function toggleDarkMode() {
                darkMode = !darkMode;
                localStorage.setItem('darkMode', darkMode);
                document.body.style.background = darkMode ? '#1a1a1a' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                toggleMenu();
            }
            
            function clearChat() {
                if(confirm('آیا می‌خواهید تاریخچه چت پاک شود؟')) {
                    document.getElementById('messages').innerHTML = `
                        <div class="message bot">
                            <div class="message-content">
                                👋 تاریخچه پاک شد. دوباره سلام!
                                <div class="time">${new Date().toLocaleTimeString('fa-IR')}</div>
                            </div>
                        </div>
                    `;
                }
                toggleMenu();
            }
            
            function useSuggestion(text) {
                document.getElementById('question').value = text;
                sendMessage();
            }
            
            async function sendMessage() {
                const question = document.getElementById('question').value.trim();
                if(!question || isTyping) return;
                
                const messages = document.getElementById('messages');
                const time = new Date().toLocaleTimeString('fa-IR');
                
                // بستن منو
                document.getElementById('menu').classList.remove('show');
                
                // نمایش سوال کاربر
                messages.innerHTML += `
                    <div class="message user">
                        <div class="message-content">
                            ${escapeHtml(question)}
                            <div class="time">${time}</div>
                        </div>
                    </div>
                `;
                
                document.getElementById('question').value = '';
                document.getElementById('sendBtn').disabled = true;
                messages.scrollTop = messages.scrollHeight;
                
                // نمایش تایپ ایندیکیتور
                isTyping = true;
                messages.innerHTML += `
                    <div class="message bot" id="typingIndicator">
                        <div class="typing-indicator">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                `;
                messages.scrollTop = messages.scrollHeight;
                
                try {
                    const response = await fetch('/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: question})
                    });
                    
                    const data = await response.json();
                    
                    // حذف تایپ ایندیکیتور
                    document.getElementById('typingIndicator')?.remove();
                    
                    // نمایش پاسخ
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content">
                                ${escapeHtml(data.answer).replace(/\\n/g, '<br>')}
                                <div class="time">${time}</div>
                            </div>
                        </div>
                    `;
                } catch(error) {
                    document.getElementById('typingIndicator')?.remove();
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content" style="background: #fee; color: #c00;">
                                ❌ خطا در ارتباط با سرور
                                <div class="time">${time}</div>
                            </div>
                        </div>
                    `;
                }
                
                isTyping = false;
                document.getElementById('sendBtn').disabled = false;
                messages.scrollTop = messages.scrollHeight;
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // ارسال با کلید Enter
            document.getElementById('question').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') sendMessage();
            });
            
            // بستن منو با کلیک خارج
            document.addEventListener('click', function(e) {
                const menu = document.getElementById('menu');
                const btn = document.querySelector('.menu-btn');
                if(!menu.contains(e.target) && !btn.contains(e.target)) {
                    menu.classList.remove('show');
                }
            });
        </script>
    </body>
    </html>
    ''', datetime=datetime)

@app.route('/login')
def login():
    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ورود به پنل مدیریت</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: system-ui, sans-serif;
            }
            
            body {
                min-height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .login-box {
                background: white;
                border-radius: 20px;
                padding: 40px;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.5s ease;
            }
            
            @keyframes slideUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .logo .icon {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-size: 40px;
                line-height: 80px;
                text-align: center;
                border-radius: 50%;
                margin: 0 auto 20px;
            }
            
            h2 {
                color: #333;
                margin-bottom: 10px;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
            }
            
            input {
                width: 100%;
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 1rem;
                transition: all 0.3s;
            }
            
            input:focus {
                border-color: #667eea;
                outline: none;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            button {
                width: 100%;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 1.1rem;
                cursor: pointer;
                transition: transform 0.3s;
            }
            
            button:hover {
                transform: translateY(-2px);
            }
            
            .error {
                background: #fee;
                color: #c00;
                padding: 12px;
                border-radius: 10px;
                margin-top: 15px;
                display: none;
            }
            
            .info {
                text-align: center;
                margin-top: 20px;
                color: #666;
            }
            
            .info a {
                color: #667eea;
                text-decoration: none;
            }
            
            .demo {
                background: #f5f5f5;
                padding: 10px;
                border-radius: 10px;
                margin-top: 20px;
                font-size: 0.9rem;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <div class="logo">
                <div class="icon">🔐</div>
                <h2>پنل مدیریت</h2>
            </div>
            
            <div class="form-group">
                <label>نام کاربری</label>
                <input type="text" id="username" value="admin" autofocus>
            </div>
            
            <div class="form-group">
                <label>رمز عبور</label>
                <input type="password" id="password" value="admin123">
            </div>
            
            <button onclick="login()">ورود به پنل</button>
            
            <div class="error" id="errorMsg"></div>
            
            <div class="demo">
                <strong>دمو:</strong> admin / admin123
            </div>
            
            <div class="info">
                <a href="/chat">🔙 بازگشت به چت</a>
            </div>
        </div>
        
        <script>
            async function login() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                if(!username || !password) {
                    showError('لطفاً نام کاربری و رمز عبور را وارد کنید');
                    return;
                }
                
                try {
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });
                    
                    const data = await response.json();
                    
                    if(data.success) {
                        window.location.href = '/admin';
                    } else {
                        showError('نام کاربری یا رمز عبور اشتباه است');
                    }
                } catch(error) {
                    showError('خطا در ارتباط با سرور');
                }
            }
            
            function showError(message) {
                const errorEl = document.getElementById('errorMsg');
                errorEl.style.display = 'block';
                errorEl.textContent = '❌ ' + message;
            }
            
            // ورود با کلید Enter
            document.getElementById('password').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') login();
            });
        </script>
    </body>
    </html>
    ''')

@app.route('/admin')
@login_required
def admin_panel():
    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>پنل مدیریت</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: system-ui, sans-serif;
            }
            
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            
            h1 {
                color: #333;
                margin-bottom: 30px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
            }
            
            .stat-number {
                font-size: 2.5rem;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            
            .tab {
                padding: 12px 25px;
                background: #f0f2f5;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .tab:hover {
                background: #e0e0e0;
            }
            
            .tab.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .tab-content {
                display: none;
            }
            
            .tab-content.active {
                display: block;
            }
            
            .section {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 15px;
                margin-bottom: 20px;
            }
            
            h2 {
                color: #333;
                margin-bottom: 20px;
            }
            
            input, textarea {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 1rem;
            }
            
            textarea {
                min-height: 100px;
                resize: vertical;
            }
            
            button {
                padding: 12px 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                font-size: 1rem;
            }
            
            .file-upload {
                border: 3px dashed #667eea;
                padding: 40px;
                text-align: center;
                border-radius: 15px;
                cursor: pointer;
                margin: 20px 0;
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            
            th {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px;
            }
            
            td {
                padding: 12px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .message {
                padding: 12px;
                border-radius: 10px;
                margin-top: 15px;
                display: none;
            }
            
            .message.success {
                background: #d4edda;
                color: #155724;
                display: block;
            }
            
            .message.error {
                background: #f8d7da;
                color: #721c24;
                display: block;
            }
            
            .logout {
                text-align: center;
                margin-top: 30px;
            }
            
            .logout a {
                color: #667eea;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚙️ پنل مدیریت هوش مصنوعی</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ stats.knowledge_count }}</div>
                    <div>تعداد دانش‌ها</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.file_count }}</div>
                    <div>فایل‌های آپلود</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ stats.chat_count }}</div>
                    <div>تعداد چت‌ها</div>
                </div>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('learn')">📚 آموزش دستی</div>
                <div class="tab" onclick="showTab('upload')">📁 آپلود فایل</div>
                <div class="tab" onclick="showTab('knowledge')">📖 دانش‌ها</div>
                <div class="tab" onclick="showTab('chats')">💬 تاریخچه چت</div>
            </div>
            
            <!-- آموزش دستی -->
            <div id="learn" class="tab-content active">
                <div class="section">
                    <h2>📚 آموزش دستی</h2>
                    <input type="text" id="question" placeholder="سوال را وارد کنید">
                    <textarea id="answer" placeholder="جواب را وارد کنید"></textarea>
                    <button onclick="manualLearn()">✅ ذخیره</button>
                    <div id="learnMessage" class="message"></div>
                </div>
            </div>
            
            <!-- آپلود فایل -->
            <div id="upload" class="tab-content">
                <div class="section">
                    <h2>📁 آپلود فایل</h2>
                    <div class="file-upload" onclick="document.getElementById('file').click()">
                        📤 کلیک کنید یا فایل را اینجا رها کنید<br>
                        <small>فرمت‌های مجاز: txt, pdf, docx, csv, json</small>
                    </div>
                    <input type="file" id="file" style="display:none" onchange="uploadFile()">
                    <div id="uploadMessage" class="message"></div>
                </div>
            </div>
            
            <!-- دانش‌ها -->
            <div id="knowledge" class="tab-content">
                <div class="section">
                    <h2>📖 دانش‌های ذخیره شده</h2>
                    <table>
                        <tr>
                            <th>#</th>
                            <th>سوال</th>
                            <th>جواب</th>
                            <th>استفاده</th>
                        </tr>
                        {% for k in knowledge %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td>{{ k.question[:50] }}...</td>
                            <td>{{ k.answer[:50] }}...</td>
                            <td>{{ k.usage }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
            
            <!-- تاریخچه چت -->
            <div id="chats" class="tab-content">
                <div class="section">
                    <h2>💬 تاریخچه چت</h2>
                    <table>
                        <tr>
                            <th>سوال</th>
                            <th>پاسخ</th>
                            <th>زمان</th>
                        </tr>
                        {% for c in chats %}
                        <tr>
                            <td>{{ c.question[:30] }}...</td>
                            <td>{{ c.answer[:30] }}...</td>
                            <td>{{ c.time }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
            
            <div class="logout">
                <a href="/logout">🚪 خروج از پنل</a>
            </div>
        </div>
        
        <script>
            function showTab(tabName) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
                document.getElementById(tabName).classList.add('active');
            }
            
            async function manualLearn() {
                const question = document.getElementById('question').value;
                const answer = document.getElementById('answer').value;
                
                if(!question || !answer) {
                    showMessage('learnMessage', 'لطفاً سوال و جواب را وارد کنید', 'error');
                    return;
                }
                
                const response = await fetch('/admin/learn', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question, answer})
                });
                
                const data = await response.json();
                
                if(data.success) {
                    showMessage('learnMessage', '✅ با موفقیت ذخیره شد', 'success');
                    document.getElementById('question').value = '';
                    document.getElementById('answer').value = '';
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showMessage('learnMessage', '❌ خطا در ذخیره', 'error');
                }
            }
            
            async function uploadFile() {
                const file = document.getElementById('file').files[0];
                if(!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/admin/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if(data.success) {
                    showMessage('uploadMessage', '✅ ' + data.message, 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showMessage('uploadMessage', '❌ ' + data.message, 'error');
                }
            }
            
            function showMessage(elementId, message, type) {
                const el = document.getElementById(elementId);
                el.className = 'message ' + type;
                el.textContent = message;
            }
        </script>
    </body>
    </html>
    ''', 
    stats={
        'knowledge_count': Knowledge.query.count(),
        'file_count': FileHistory.query.count(),
        'chat_count': ChatHistory.query.count()
    },
    knowledge=[k.to_dict() for k in Knowledge.query.order_by(Knowledge.created_at.desc()).limit(10).all()],
    chats=[{'question': c.question, 'answer': c.answer, 'time': c.created_at.strftime('%Y-%m-%d %H:%M')} 
           for c in ChatHistory.query.order_by(ChatHistory.created_at.desc()).limit(20).all()]
    )

# ==================== API ====================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and user.check_password(data.get('password')):
        session['user_id'] = user.id
        session.permanent = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'اطلاعات وارد شده صحیح نیست'}), 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'answer': '❌ لطفاً یک سوال وارد کنید'})
    
    # ایجاد جستجوگر
    searcher = GoogleSearcher()
    
    try:
        # تشخیص نوع سوال
        is_price = any(w in question for w in ['قیمت', 'چنده', 'چقدر', 'نرخ'])
        
        if is_price:
            # جستجوی قیمت
            price_data = searcher.get_price(question)
            if price_data:
                answer = f"💰 **{question}**\n\n"
                for item in price_data[:3]:
                    answer += f"**{item['title']}**\n"
                    for price in item['prices'][:2]:
                        answer += f"💵 {price[0]} {price[1]}\n"
                    answer += f"📌 {item['source']}\n\n"
                
                # ذخیره در تاریخچه
                chat = ChatHistory(question=question, answer=answer, answer_type='price')
                db.session.add(chat)
                db.session.commit()
                
                return jsonify({'answer': answer})
        
        # جستجوی عادی
        results = searcher.search(question, num=3)
        
        if results:
            answer = f"🔍 **نتایج جستجو برای:** {question}\n\n"
            for r in results[:3]:
                answer += f"📌 **{r['title']}**\n"
                answer += f"{r['snippet'][:200]}...\n"
                answer += f"🔗 {r['domain']}\n\n"
            
            # ذخیره در تاریخچه
            chat = ChatHistory(question=question, answer=answer, answer_type='google')
            db.session.add(chat)
            db.session.commit()
            
            return jsonify({'answer': answer})
        
        # جستجو در دانش داخلی
        knowledge_item = Knowledge.query.filter(
            Knowledge.question.contains(question)
        ).first()
        
        if knowledge_item:
            knowledge_item.usage_count += 1
            db.session.commit()
            
            chat = ChatHistory(question=question, answer=knowledge_item.answer, answer_type='knowledge')
            db.session.add(chat)
            db.session.commit()
            
            return jsonify({'answer': knowledge_item.answer})
        
        return jsonify({'answer': '❌ متاسفانه نتیجه‌ای پیدا نشد. لطفاً دقیق‌تر بپرسید.'})
    
    except Exception as e:
        logging.error(f"Error in ask: {e}")
        return jsonify({'answer': '❌ خطا در پردازش سوال. لطفاً دوباره تلاش کنید.'})

@app.route('/admin/learn', methods=['POST'])
@login_required
def admin_learn():
    data = request.json
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    
    if not question or not answer:
        return jsonify({'success': False, 'message': 'سوال و جواب را وارد کنید'})
    
    knowledge = Knowledge(question=question, answer=answer, source='manual', confidence=100)
    db.session.add(knowledge)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '✅ دانش جدید ذخیره شد'})

@app.route('/admin/upload', methods=['POST'])
@login_required
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'فایلی انتخاب نشده'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'فایل خالی است'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'فرمت فایل مجاز نیست'})
    
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # استخراج متن
    text = extract_text_from_file(filepath, ext)
    
    if not text:
        return jsonify({'success': False, 'message': 'متنی از فایل استخراج نشد'})
    
    # استخراج سوال و جواب
    qa_pairs = extract_qa_from_text(text)
    
    count = 0
    for qa in qa_pairs:
        if not Knowledge.query.filter_by(question=qa['question']).first():
            knowledge = Knowledge(
                question=qa['question'][:500],
                answer=qa['answer'][:1000],
                source=f'file:{filename}',
                confidence=70
            )
            db.session.add(knowledge)
            count += 1
    
    # ذخیره تاریخچه فایل
    history = FileHistory(filename=filename, extracted_count=count)
    db.session.add(history)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'✅ {count} مورد یادگیری از فایل استخراج شد'})

# ==================== اجرا ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
