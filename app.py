from flask import Flask, request, jsonify, redirect, render_template_string, session
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
import uuid
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
    required_packages = ['punkt', 'stopwords', 'averaged_perceptron_tagger', 'punkt_tab']
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

# ==================== تنظیمات امنیتی ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def check_auth(username, password):
    return username == ADMIN_USERNAME and hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

def authenticate():
    return jsonify({'success': False, 'message': 'احراز هویت الزامی است', 'login_required': True}), 401

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
                except Exception as e:
                    app.logger.warning(f"خطا در صفحه {page_num}: {e}")
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

def extract_sentences(text):
    try:
        sentences = sent_tokenize(text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    except:
        return [line.strip() for line in text.split('\n') if len(line.strip()) > 10]

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
    except Exception as e:
        app.logger.error(f"خطا در استخراج کلمات کلیدی: {e}")
        return []

# ==================== کلاس استخراج سوال و جواب ====================
class QuestionAnswerExtractor:
    def __init__(self):
        self.question_patterns = [
            r'[؟?]\s*$',
            r'^(چیست|کیست|کجاست|چرا|چطور|چگونه|آیا|چه|کدام|چند|چه\s+کسی|چه\s+چیزی)',
            r'(چیست|کیست|کجاست|چرا|چطور|چگونه|آیا|چه|کدام|چند)\s*$',
            r'\b(what|who|where|why|how|when|which|is|are|can|could)\b.*\?$',
        ]
        self.answer_indicators = [
            r'^پاسخ:',
            r'^جواب:',
            r'^answer:',
            r'^نتیجه:',
            r'^\d+[\.\)]',
            r'^[•\-*]',
        ]
        self.stop_phrases = [
            'کپی رایت', 'تمامی حقوق', 'منبع:', 'مرجع:', 'www.', 'http',
            'برای اطلاعات بیشتر', 'ادامه مطلب', 'منبع تصویر'
        ]
    
    def is_question(self, text):
        text = text.strip().lower()
        if len(text) < 5 or len(text) > 500:
            return False
        for pattern in self.question_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        question_words = ['چیست', 'کیست', 'کجاست', 'چرا', 'چطور', 'چگونه', 'آیا', 
                         'چه', 'کدام', 'چند', 'میشه', 'میتوان', 'هست', 'آیا']
        if any(word in text for word in question_words):
            return True
        if '?' in text or '؟' in text:
            return True
        return False
    
    def is_answer(self, text, min_length=20, max_length=2000):
        text = text.strip()
        if len(text) < min_length or len(text) > max_length:
            return False
        if any(phrase in text.lower() for phrase in self.stop_phrases):
            return False
        sentences = sent_tokenize(text)
        if len(sentences) < 2:
            return False
        return True
    
    def find_best_answer(self, lines, question_index, max_distance=5):
        best_answer = None
        best_score = 0
        for i in range(1, min(max_distance + 1, len(lines) - question_index)):
            candidate = lines[question_index + i].strip()
            if not candidate:
                continue
            if self.is_question(candidate):
                break
            score = 0
            if 50 <= len(candidate) <= 1000:
                score += 20
            elif len(candidate) > 1000:
                score += 10
            sentence_count = len(sent_tokenize(candidate))
            score += sentence_count * 5
            score += (max_distance - i) * 3
            if re.match(r'^[0-9]+[\.\)]', candidate):
                score += 15
            if candidate[0] in ['-', '•', '*']:
                score += 10
            if candidate[0].isupper():
                score += 5
            if score > best_score:
                best_score = score
                best_answer = candidate
        return best_answer, best_score
    
    def extract_qa_pairs(self, text, filename=""):
        lines = text.split('\n')
        qa_pairs = []
        i = 0
        app.logger.info(f"شروع استخراج از {filename} با {len(lines)} خط")
        while i < len(lines):
            line = lines[i].strip()
            if not line or len(line) < 10:
                i += 1
                continue
            if self.is_question(line):
                app.logger.debug(f"سوال پیدا شد در خط {i}: {line[:50]}...")
                answer, score = self.find_best_answer(lines, i)
                if answer and score > 30:
                    qa_pairs.append({
                        'question': line,
                        'answer': answer,
                        'line_number': i,
                        'confidence': score,
                        'source': filename
                    })
                    app.logger.info(f"✅ جفت سوال-جواب استخراج شد با امتیاز {score}")
                    i += 1
                    continue
            i += 1
        return qa_pairs
    
    def extract_from_structured(self, text, filename=""):
        qa_pairs = []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        question = item.get('question') or item.get('q') or item.get('سوال')
                        answer = item.get('answer') or item.get('a') or item.get('جواب') or item.get('response')
                        if question and answer:
                            qa_pairs.append({
                                'question': str(question),
                                'answer': str(answer),
                                'confidence': 100,
                                'source': filename,
                                'type': 'json_structured'
                            })
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str) and len(value) > 50:
                        if self.is_question(key):
                            qa_pairs.append({
                                'question': key,
                                'answer': value,
                                'confidence': 90,
                                'source': filename,
                                'type': 'json_dict'
                            })
        except json.JSONDecodeError:
            pass
        return qa_pairs
    
    def extract_from_csv(self, text, filename=""):
        qa_pairs = []
        try:
            lines = text.split('\n')
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 2:
                    question = parts[0].strip()
                    answer = ','.join(parts[1:]).strip()
                    if len(question) > 10 and len(answer) > 20:
                        qa_pairs.append({
                            'question': question,
                            'answer': answer,
                            'confidence': 80,
                            'source': filename,
                            'type': 'csv'
                        })
        except Exception as e:
            app.logger.error(f"خطا در استخراج CSV: {e}")
        return qa_pairs

# ==================== کلاس جستجوی آنلاین قیمت ====================
class OnlinePriceSearcher:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        self.price_patterns = [
            r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(تومان|دلار|یورو|درهم|لیر|پوند)',
            r'(\d+(?:\.\d+)?)\s*(?:دلار|تومان|\$|€|£)',
            r'قیمت.*?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(تومان|دلار)',
            r'هر\s*(گرم|مثقال|انس|عدد)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(تومان|دلار)'
        ]
        self.price_keywords = {
            'gold': ['طلا', 'طلای', 'سکه', 'امامی', 'بهار آزادی', 'انس', 'اونس'],
            'currency': ['دلار', 'یورو', 'پوند', 'درهم', 'لیر', 'ارز', 'صرافی'],
            'crypto': ['بیت‌کوین', 'بیت کوین', 'اتریوم', 'بایننس', 'تتر', 'USDT'],
            'oil': ['نفت', 'طلای سیاه', 'برنت', 'WTI'],
            'coin': ['سکه', 'نیم سکه', 'ربع سکه', 'سکه گرمی']
        }
        self.trusted_sources = [
            'tgju.org', 'bonbast.com', 'donya-e-eqtesad.com', 'eghtesadnews.com',
            'alanchand.com', 'bazar360.com', 'boursenews.ir', 'kitco.com',
            'goldprice.org', 'xe.com'
        ]
        self.cache = {}
        self.cache_duration = 1800
    
    def _get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def is_price_question(self, question):
        question = question.lower()
        price_keywords = ['قیمت', 'چنده', 'چقدر', 'نرخ', 'قیمتش', 'بهای', 'ارزش', 'گرون', 'ارزون']
        if not any(keyword in question for keyword in price_keywords):
            return False
        for category, items in self.price_keywords.items():
            if any(item in question for item in items):
                return True
        return False
    
    def extract_price_item(self, question):
        question = question.lower()
        if 'طلا' in question:
            if 'انس' in question or 'اونس' in question:
                return {'type': 'gold', 'subtype': 'ounce', 'name': 'انس طلا'}
            elif 'مثقال' in question:
                return {'type': 'gold', 'subtype': 'mithqal', 'name': 'مثقال طلا'}
            else:
                return {'type': 'gold', 'subtype': 'gram', 'name': 'گرم طلا 18 عیار'}
        if 'سکه' in question:
            if 'امامی' in question or 'طرح جدید' in question:
                return {'type': 'coin', 'subtype': 'emami', 'name': 'سکه امامی'}
            elif 'بهار' in question or 'طرح قدیم' in question:
                return {'type': 'coin', 'subtype': 'bahar', 'name': 'سکه بهار آزادی'}
            elif 'نیم' in question:
                return {'type': 'coin', 'subtype': 'nim', 'name': 'نیم سکه'}
            elif 'ربع' in question:
                return {'type': 'coin', 'subtype': 'rob', 'name': 'ربع سکه'}
            elif 'گرمی' in question:
                return {'type': 'coin', 'subtype': 'grami', 'name': 'سکه گرمی'}
        if 'دلار' in question:
            return {'type': 'currency', 'subtype': 'usd', 'name': 'دلار آمریکا'}
        if 'یورو' in question:
            return {'type': 'currency', 'subtype': 'eur', 'name': 'یورو'}
        if 'پوند' in question:
            return {'type': 'currency', 'subtype': 'gbp', 'name': 'پوند انگلیس'}
        if 'درهم' in question:
            return {'type': 'currency', 'subtype': 'aed', 'name': 'درهم امارات'}
        if 'لیر' in question:
            return {'type': 'currency', 'subtype': 'try', 'name': 'لیر ترکیه'}
        return None
    
    def search_google(self, query, num_results=3):
        try:
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5,fa;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            search_url = f"https://www.google.com/search?q={quote(query)}&num={num_results}"
            app.logger.info(f"🔍 جستجو در گوگل: {query}")
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            search_results = soup.find_all('div', class_='g') or soup.find_all('div', class_='rc')
            for result in search_results[:num_results]:
                title_elem = result.find('h3')
                link_elem = result.find('a')
                snippet_elem = result.find('div', class_='IsZvec') or result.find('span', class_='aCOpRe')
                if title_elem and link_elem:
                    title = title_elem.get_text()
                    link = link_elem.get('href', '')
                    if link.startswith('/url?q='):
                        link = link.split('/url?q=')[1].split('&')[0]
                    snippet = snippet_elem.get_text() if snippet_elem else ""
                    source_trust = any(source in link for source in self.trusted_sources)
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'trusted': source_trust
                    })
            app.logger.info(f"✅ {len(results)} نتیجه از گوگل دریافت شد")
            return results
        except Exception as e:
            app.logger.error(f"خطا در جستجوی گوگل: {e}")
            return []
    
    def extract_price_from_snippet(self, snippet, item_info):
        if not snippet:
            return None
        prices = []
        for pattern in self.price_patterns:
            matches = re.findall(pattern, snippet, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    price_num = match[0].replace(',', '')
                    price_unit = match[1]
                    try:
                        price_value = float(price_num)
                        if item_info['type'] == 'gold':
                            if item_info.get('subtype') == 'ounce' and 1000 < price_value < 10000:
                                prices.append(('انس', price_value, 'دلار'))
                            elif item_info.get('subtype') == 'gram' and 1000000 < price_value < 100000000:
                                prices.append(('گرم', price_value, 'تومان'))
                        elif item_info['type'] == 'currency':
                            if 50000 < price_value < 500000:
                                prices.append(('دلار', price_value, 'تومان'))
                    except ValueError:
                        continue
        return prices[0] if prices else None
    
    def get_price(self, question):
        item_info = self.extract_price_item(question)
        if not item_info:
            return None
        cache_key = f"{item_info['type']}_{item_info['subtype']}_{datetime.now().strftime('%Y-%m-%d')}"
        if cache_key in self.cache:
            cache_time, price_data = self.cache[cache_key]
            if (datetime.now() - cache_time).seconds < self.cache_duration:
                app.logger.info(f"⚡ قیمت از کش: {item_info['name']}")
                return price_data
        search_query = f"قیمت {item_info['name']} {datetime.now().strftime('%Y/%m/%d')}"
        results = self.search_google(search_query)
        if not results:
            return None
        best_price = None
        best_confidence = 0
        for result in results:
            price_info = self.extract_price_from_snippet(result['snippet'], item_info)
            confidence = 70 if result['trusted'] else 40
            if price_info and confidence > best_confidence:
                best_price = {
                    'item': item_info['name'],
                    'price': price_info[1],
                    'unit': price_info[2],
                    'source': result['link'],
                    'source_title': result['title'],
                    'confidence': confidence,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }
                best_confidence = confidence
        if best_price:
            self.cache[cache_key] = (datetime.now(), best_price)
            return best_price
        return None
    
    def format_price_response(self, price_data):
        if not price_data:
            return "متاسفانه نتونستم قیمت دقیق رو پیدا کنم. لطفاً دقیق‌تر بپرسید."
        response = f"""💰 **{price_data['item']}**

قیمت: {price_data['price']:,} {price_data['unit']}
⏱ زمان: {price_data['timestamp']}
📊 منبع: {price_data['source_title'][:50]}

🔗 {price_data['source']}"""
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
        app.logger.info(f"📝 دانش به‌روزرسانی شد: {question[:30]}... (نسخه {old_version + 1})")
    else:
        knowledge_base[question] = {
            'answer': answer,
            'source': source,
            'learned_at': str(datetime.now()),
            'updated_at': str(datetime.now()),
            'usage': 0,
            'confidence': confidence,
            'version': 1,
            'keywords': extract_keywords(question + " " + answer),
            'answer_length': len(answer),
            'question_length': len(question)
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
            app.logger.warning(f"فایل {filename} خالی است")
            return 0
        app.logger.info(f"📄 فایل {filename} با {len(content)} کاراکتر بارگذاری شد")
        extractor = QuestionAnswerExtractor()
        all_qa_pairs = []
        if file_ext == 'json':
            qa_pairs = extractor.extract_from_structured(content, filename)
            all_qa_pairs.extend(qa_pairs)
        elif file_ext == 'csv':
            qa_pairs = extractor.extract_from_csv(content, filename)
            all_qa_pairs.extend(qa_pairs)
        qa_pairs = extractor.extract_qa_pairs(content, filename)
        all_qa_pairs.extend(qa_pairs)
        unique_pairs = {}
        for pair in all_qa_pairs:
            q_hash = hashlib.md5(pair['question'].encode()).hexdigest()
            if q_hash not in unique_pairs or pair['confidence'] > unique_pairs[q_hash]['confidence']:
                unique_pairs[q_hash] = pair
        for pair in unique_pairs.values():
            learn_from_text(pair['question'], pair['answer'], source=f'file:{filename}', confidence=pair.get('confidence', 70))
            extracted += 1
            app.logger.info(f"✅ یاد گرفتم: {pair['question'][:30]}... (اعتماد: {pair.get('confidence', 70)}%)")
        file_history.append({
            'filename': filename,
            'extracted': extracted,
            'total_pairs': len(unique_pairs),
            'time': str(datetime.now()),
            'file_size': os.path.getsize(filepath)
        })
        if len(file_history) > app.config['MAX_HISTORY']:
            file_history[:] = file_history[-app.config['MAX_HISTORY']:]
        app.logger.info(f"🎯 مجموع {extracted} مورد یادگیری از {filename}")
        return extracted
    except Exception as e:
        app.logger.error(f"خطا در یادگیری از فایل {filename}: {e}")
        return 0

def smart_search(user_question):
    price_searcher = OnlinePriceSearcher()
    if price_searcher.is_price_question(user_question):
        app.logger.info(f"💰 سوال قیمتی تشخیص داده شد: {user_question}")
        price_data = price_searcher.get_price(user_question)
        if price_data:
            response = price_searcher.format_price_response(price_data)
            chat_history.append({
                'question': user_question,
                'answer': response,
                'type': 'online_price',
                'time': str(datetime.now())
            })
            return response
        else:
            return "نتونستم قیمت لحظه‌ای رو پیدا کنم. لطفاً دقیق‌تر بپرسید یا از منابع دیگه استفاده کنید."
    cache_key = hashlib.md5(user_question.encode()).hexdigest()
    if cache_key in search_cache:
        cache_time, answer = search_cache[cache_key]
        if (datetime.now() - cache_time).seconds < 300:
            app.logger.info(f"⚡ نتیجه از کش: {user_question[:30]}...")
            return answer
    best_match = None
    best_ratio = 0
    second_best = None
    second_ratio = 0
    for question in knowledge_base.keys():
        ratio1 = SequenceMatcher(None, user_question.lower(), question.lower()).ratio()
        q_keywords = set(extract_keywords(user_question))
        kb_keywords = set(knowledge_base[question].get('keywords', []))
        if q_keywords and kb_keywords:
            keyword_ratio = len(q_keywords & kb_keywords) / len(q_keywords) if q_keywords else 0
            ratio1 = (ratio1 + keyword_ratio) / 2
        if ratio1 > best_ratio:
            second_best, second_ratio = best_match, best_ratio
            best_ratio = ratio1
            best_match = question
        elif ratio1 > second_ratio:
            second_ratio = ratio1
            second_best = question
    threshold = app.config['SIMILARITY_THRESHOLD']
    if best_ratio > threshold:
        knowledge_base[best_match]['usage'] += 1
        answer = knowledge_base[best_match]['answer']
        if second_ratio > threshold and second_best:
            answer += f"\n\n💡 همچنین می‌توانید بپرسید: {second_best}"
        search_cache[cache_key] = (datetime.now(), answer)
        chat_history.append({
            'question': user_question,
            'answer': answer,
            'type': 'knowledge_base',
            'time': str(datetime.now())
        })
        return answer
    no_answer = "متوجه سوالتون نشدم. میشه واضح‌تر بپرسید؟ یا می‌تونید این مطلب رو به من یاد بدید."
    chat_history.append({
        'question': user_question,
        'answer': no_answer,
        'type': 'no_answer',
        'time': str(datetime.now())
    })
    return no_answer

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

# ایمپورت صفحات از فایل‌های دیگر
from routes import *
from admin_routes import *

if __name__ == '__main__':
    load_knowledge()
    app.run(host='0.0.0.0', port=5000, debug=True)
