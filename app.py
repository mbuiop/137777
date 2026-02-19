from flask import Flask, request, jsonify, redirect
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
import re
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import random
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = os.urandom(24)

# تنظیم لاگینگ
if not os.path.exists('logs'):
    os.makedirs('logs')
    
handler = RotatingFileHandler('logs/app.log', maxBytes=10000000, backupCount=3)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# دانلود داده‌های NLTK
def download_nltk_data():
    required_packages = ['punkt', 'stopwords', 'averaged_perceptron_tagger']
    for package in required_packages:
        try:
            nltk.download(package, quiet=True)
            app.logger.info(f"✅ NLTK package {package} downloaded")
        except Exception as e:
            app.logger.error(f"❌ Failed to download {package}: {e}")

download_nltk_data()

# تنظیمات برنامه
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['MAX_HISTORY'] = 1000
app.config['SIMILARITY_THRESHOLD'] = 0.6

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv', 'json'}
os.makedirs('uploads', exist_ok=True)
os.makedirs('backups', exist_ok=True)

# ==================== دیتابیس حافظه ====================
knowledge_base = {}
file_history = []
chat_history = []
search_cache = {}

# ==================== تنظیمات امنیتی ساده ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # در تولید حتماً تغییر دهید

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return jsonify({'success': False, 'message': 'نام کاربری یا رمز عبور اشتباه است'}), 401

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ==================== توابع کمکی ====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_file_read(filepath, mode='r', encoding='utf-8', max_size=10*1024*1024):
    try:
        if os.path.getsize(filepath) > max_size:
            raise ValueError(f"فایل بزرگتر از حد مجاز {max_size/1024/1024}MB است")
        with open(filepath, mode, encoding=encoding) as f:
            return f.read()
    except Exception as e:
        app.logger.error(f"خطا در خواندن فایل {filepath}: {e}")
        return ""

def read_txt_file(filepath):
    return safe_file_read(filepath)

def read_pdf_file(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text += page.extract_text() + "\n"
                except:
                    continue
        return text
    except Exception as e:
        app.logger.error(f"خطا در خواندن PDF: {e}")
        return ""

def read_docx_file(filepath):
    try:
        doc = docx.Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        app.logger.error(f"خطا در خواندن DOCX: {e}")
        return ""

def read_csv_file(filepath):
    text = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                text += " ".join(row) + "\n"
        return text
    except Exception as e:
        app.logger.error(f"خطا در خواندن CSV: {e}")
        return ""

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s؟?!.،]', '', text)
    return text.strip()

def extract_keywords(text, max_keywords=10):
    try:
        words = word_tokenize(text)
        stop_words = set(nltk.corpus.stopwords.words('persian') + nltk.corpus.stopwords.words('english'))
        keywords = [word.lower() for word in words if word.isalnum() and word.lower() not in stop_words and len(word) > 2]
        return list(set(keywords))[:max_keywords]
    except:
        return []

# ==================== کلاس جستجوی پیشرفته گوگل ====================
class AdvancedGoogleSearcher:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
        self.search_cache = {}
        self.cache_duration = 900
        self.trusted_persian_sites = [
            'tgju.org', 'bonbast.com', 'donya-e-eqtesad.com', 'eghtesadnews.com',
            'tabnak.ir', 'irna.ir', 'mehrnews.com', 'farsnews.ir', 'tasnimnews.com',
            'bbc.com/persian', 'dw.com/fa', 'isna.ir', 'yjc.ir', 'digiato.com', 
            'zoomit.ir', 'virgool.io', 'tebyan.net', 'beytoote.com'
        ]
    
    def _get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def _extract_main_content(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        main_content = None
        content_classes = ['article', 'post', 'content', 'main', 'entry-content', 
                          'matn', 'text', 'body-content']
        
        for class_name in content_classes:
            content = soup.find('div', class_=class_name) or soup.find('article', class_=class_name)
            if content:
                main_content = content
                break
        
        if not main_content:
            main_content = soup.find('article') or soup.find('main') or soup.body
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 30]
            return '\n'.join(lines)
        return None
    
    def search_google(self, query, num_results=5):
        cache_key = hashlib.md5(f"{query}_{num_results}".encode()).hexdigest()
        if cache_key in self.search_cache:
            cache_time, results = self.search_cache[cache_key]
            if (datetime.now() - cache_time).seconds < self.cache_duration:
                return results
        
        try:
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fa,en-US;q=0.9,en;q=0.8',
            }
            
            search_url = f"https://www.google.com/search?q={quote(query)}&num={num_results}&hl=fa"
            app.logger.info(f"🔍 جستجو در گوگل: {query}")
            
            session = requests.Session()
            response = session.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            search_results = soup.find_all('div', class_='g') or soup.find_all('div', class_='rc')
            
            for result in search_results[:num_results]:
                try:
                    link_elem = result.find('a')
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href', '')
                    if href.startswith('/url?q='):
                        link = href.split('/url?q=')[1].split('&')[0]
                    elif href.startswith('http'):
                        link = href
                    else:
                        continue
                    
                    title_elem = result.find('h3')
                    title = title_elem.get_text() if title_elem else "بدون عنوان"
                    
                    snippet_elem = result.find('div', class_='VwiC3b') or result.find('span', class_='aCOpRe')
                    snippet = snippet_elem.get_text() if snippet_elem else ""
                    
                    domain = link.split('/')[2] if '//' in link else link
                    is_trusted = any(site in domain.lower() for site in self.trusted_persian_sites)
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'trusted': is_trusted,
                        'source_domain': domain
                    })
                except:
                    continue
            
            self.search_cache[cache_key] = (datetime.now(), results)
            return results
            
        except Exception as e:
            app.logger.error(f"خطا در جستجو: {e}")
            return []
    
    def get_price_info(self, query):
        price_results = []
        results = self.search_google(query, num_results=10)
        
        for result in results:
            if result['trusted']:
                price_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(تومان|دلار|ریال)'
                prices = re.findall(price_pattern, result['snippet'])
                if prices:
                    price_results.append({
                        'source': result['source_domain'],
                        'title': result['title'],
                        'prices': prices[:3],
                        'link': result['link']
                    })
        
        return price_results[:5]
    
    def format_response(self, query, results):
        if not results:
            return f"❌ متاسفانه نتیجه‌ای برای '{query}' پیدا نشد."
        
        response = f"🔍 **نتایج جستجو برای:** {query}\n\n"
        
        for i, result in enumerate(results[:3], 1):
            response += f"**{i}. {result['title']}**\n"
            response += f"{result['snippet'][:200]}...\n"
            response += f"📌 {result['source_domain']}\n\n"
        
        return response

# ==================== توابع یادگیری ====================
def learn_from_text(question, answer, source='manual', confidence=100):
    question = clean_text(question)
    answer = clean_text(answer)
    
    if question in knowledge_base:
        old_version = knowledge_base[question].get('version', 1)
        knowledge_base[question]['answer'] = answer
        knowledge_base[question]['updated_at'] = str(datetime.now())
        knowledge_base[question]['version'] = old_version + 1
        knowledge_base[question]['confidence'] = confidence
    else:
        knowledge_base[question] = {
            'answer': answer,
            'source': source,
            'learned_at': str(datetime.now()),
            'updated_at': str(datetime.now()),
            'usage': 0,
            'confidence': confidence,
            'version': 1,
            'keywords': extract_keywords(question + " " + answer)
        }
    
    auto_save()
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
        elif file_ext == 'json':
            content = safe_file_read(filepath)
        else:
            return 0
        
        if not content:
            return 0
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) < 10:
                continue
            if '?' in line or '؟' in line or 'چیست' in line:
                if i + 1 < len(lines):
                    answer = lines[i + 1].strip()
                    if answer and len(answer) > 10:
                        learn_from_text(line, answer, f'file:{filename}', 70)
                        extracted += 1
        
        file_history.append({
            'filename': filename,
            'extracted': extracted,
            'time': str(datetime.now())
        })
        
        return extracted
    except Exception as e:
        app.logger.error(f"خطا در یادگیری: {e}")
        return 0

def smart_search(user_question):
    searcher = AdvancedGoogleSearcher()
    
    # تشخیص سوال قیمتی
    if any(word in user_question for word in ['قیمت', 'چنده', 'چقدر', 'نرخ']):
        app.logger.info(f"💰 سوال قیمتی: {user_question}")
        price_info = searcher.get_price_info(user_question)
        if price_info:
            response = f"💰 **{user_question}**\n\n"
            for info in price_info[:3]:
                response += f"**{info['title']}**\n"
                for price in info['prices']:
                    response += f"💰 {price[0]} {price[1]}\n"
                response += f"📌 {info['source']}\n\n"
            
            chat_history.append({
                'question': user_question,
                'answer': response,
                'type': 'price',
                'time': str(datetime.now())
            })
            return response
    
    # جستجوی عادی
    results = searcher.search_google(user_question)
    if results:
        response = searcher.format_response(user_question, results)
        chat_history.append({
            'question': user_question,
            'answer': response,
            'type': 'google',
            'time': str(datetime.now())
        })
        return response
    
    # جستجو در دانش داخلی
    cache_key = hashlib.md5(user_question.encode()).hexdigest()
    if cache_key in search_cache:
        cache_time, answer = search_cache[cache_key]
        if (datetime.now() - cache_time).seconds < 300:
            return answer
    
    best_match = None
    best_ratio = 0
    
    for question in knowledge_base.keys():
        ratio = SequenceMatcher(None, user_question.lower(), question.lower()).ratio()
        if ratio > best_ratio and ratio > app.config['SIMILARITY_THRESHOLD']:
            best_ratio = ratio
            best_match = question
    
    if best_match:
        knowledge_base[best_match]['usage'] += 1
        answer = knowledge_base[best_match]['answer']
        search_cache[cache_key] = (datetime.now(), answer)
        
        chat_history.append({
            'question': user_question,
            'answer': answer,
            'type': 'knowledge',
            'time': str(datetime.now())
        })
        return answer
    
    return f"❌ متاسفانه نتیجه‌ای برای '{user_question}' پیدا نشد. لطفاً دقیق‌تر بپرسید."

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

# ==================== ایمپورت روت‌ها ====================
from routes import *
from admin_routes import *

if __name__ == '__main__':
    load_knowledge()
    app.run(host='0.0.0.0', port=5000, debug=True)
