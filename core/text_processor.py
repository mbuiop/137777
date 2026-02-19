import re
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import ISRIStemmer, PorterStemmer
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import threading

# دانلود داده‌های NLTK
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

class TextProcessor:
    """پردازشگر پیشرفته متن با قابلیت‌های چندزبانه"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.setup_processors()
    
    def setup_processors(self):
        """تنظیم پردازشگرها"""
        # استمرهای فارسی و انگلیسی
        self.arabic_stemmer = ISRIStemmer()
        self.english_stemmer = PorterStemmer()
        
        # کلمات توقف
        self.stop_words = set(stopwords.words('english'))
        # کلمات توقف فارسی
        persian_stops = {'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'تا', 'بر', 
                        'هم', 'نیز', 'را', 'ای', 'های', 'مورد', 'ها', 'کرد', 'شده', 'می',
                        'باشد', 'شود', 'دهد', 'گرفت', 'گفته', 'شده‌است', 'کرده', 'دارد'}
        self.stop_words.update(persian_stops)
        
        # مترادف‌ها (کلمات هم‌معنی)
        self.synonyms = {
            'قیمت': ['نرخ', 'بها', 'ارزش', 'مبلغ', 'چند'],
            'طلا': ['زر', 'طلای', 'سکه'],
            'دلار': ['دلار', 'اسکناس'],
            'هوش': ['ذکا', 'فراست'],
            'مصنوعی': ['ساختگی', 'مجازی'],
            'سلام': ['درود', 'احوال', 'خوبی'],
        }
        
        # بردارساز TF-IDF
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 3),
            analyzer='char_wb'  # برای زبان فارسی بهتر کار می‌کند
        )
        
        # حافظه موقت برای پردازش‌های تکراری
        self.cache = {}
        self.cache_lock = threading.Lock()
    
    def clean_text(self, text):
        """پاکسازی کامل متن"""
        if not text:
            return ""
        
        # حذف فاصله‌های اضافی
        text = re.sub(r'\s+', ' ', text)
        
        # حذف کاراکترهای خاص (به جز نشانگر جواب)
        text = re.sub(r'[^\w\s?!؟.،!این]', '', text)
        
        # حذف اعداد (اختیاری)
        # text = re.sub(r'\d+', '', text)
        
        return text.strip()
    
    def normalize_persian(self, text):
        """نرمال‌سازی متن فارسی"""
        # یکسان‌سازی حروف
        text = text.replace('ي', 'ی').replace('ك', 'ک')
        text = text.replace('ة', 'ه').replace('ۀ', 'ه')
        text = text.replace('إ', 'ا').replace('أ', 'ا')
        
        # حذف اعراب
        text = re.sub(r'[َُِّْـ]', '', text)
        
        return text
    
    def tokenize(self, text):
        """توکن‌سازی پیشرفته"""
        try:
            # پاکسازی اولیه
            text = self.clean_text(text)
            text = self.normalize_persian(text)
            
            # توکن‌سازی
            tokens = word_tokenize(text)
            
            # حذف کلمات توقف
            tokens = [t for t in tokens if t.lower() not in self.stop_words]
            
            # حذف توکن‌های کوتاه
            tokens = [t for t in tokens if len(t) > 1]
            
            return tokens
        except:
            # Fallback به روش ساده
            return text.split()
    
    def stem_word(self, word):
        """ریشه‌یابی کلمه"""
        if re.search(r'[a-zA-Z]', word):
            return self.english_stemmer.stem(word)
        else:
            return self.arabic_stemmer.stem(word)
    
    def expand_with_synonyms(self, word):
        """گسترش کلمه با مترادف‌ها"""
        expanded = {word}
        for key, synonyms in self.synonyms.items():
            if word in synonyms or word == key:
                expanded.update(synonyms)
                expanded.add(key)
        return list(expanded)
    
    def extract_keywords(self, text, max_keywords=10):
        """استخراج کلمات کلیدی مهم"""
        tokens = self.tokenize(text)
        
        # محاسبه اهمیت کلمات
        word_importance = {}
        for token in tokens:
            if token not in word_importance:
                # اهمیت بر اساس طول و موقعیت
                importance = len(token) * 2
                if token in text[:50]:  # کلمات ابتدای متن مهم‌ترند
                    importance *= 1.5
                word_importance[token] = importance
        
        # مرتب‌سازی و انتخاب مهم‌ترین‌ها
        keywords = sorted(word_importance.items(), key=lambda x: x[1], reverse=True)
        return [k[0] for k in keywords[:max_keywords]]
    
    def create_vector(self, text):
        """ایجاد بردار عددی از متن"""
        tokens = self.tokenize(text)
        stemmed = [self.stem_word(t) for t in tokens]
        
        # ایجاد بردار ساده (می‌توانید از word2vec هم استفاده کنید)
        vector = {}
        for word in stemmed:
            vector[word] = vector.get(word, 0) + 1
        
        return json.dumps(vector)
    
    def extract_answer_from_text(self, text, marker='!این'):
        """استخراج جواب از متن با استفاده از نشانگر"""
        answers = []
        lines = text.split('\n')
        
        current_answer = []
        in_answer = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if marker in line:
                # شروع جواب جدید
                if current_answer:
                    answers.append('\n'.join(current_answer))
                    current_answer = []
                in_answer = True
                # حذف نشانگر از متن
                line = line.replace(marker, '').strip()
                if line:
                    current_answer.append(line)
            elif in_answer:
                # ادامه جواب
                current_answer.append(line)
            else:
                # متن عادی
                if len(line) > 100:  # خطوط بلند ممکن است جواب باشند
                    answers.append(line)
        
        if current_answer:
            answers.append('\n'.join(current_answer))
        
        return answers
    
    def get_text_hash(self, text):
        """ایجاد هش یکتا برای متن"""
        normalized = self.normalize_persian(text.lower())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def batch_process(self, texts, func, max_workers=4):
        """پردازش دسته‌ای با چند ریسمان"""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(func, texts))
        return results
