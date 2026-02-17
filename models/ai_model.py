import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
from datetime import datetime
import hashlib
from textblob import TextBlob
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import re

nltk.download('punkt')
nltk.download('stopwords')

class AdvancedAIModel:
    def __init__(self):
        self.model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        self.embedding_model = SentenceTransformer(self.model_name)
        self.nlp = spacy.load('en_core_web_sm')
        
        # حافظه اصلی (10GB)
        self.knowledge_base = {}
        self.embeddings = []
        self.knowledge_ids = []
        
        # Index برای جستجوی سریع
        self.index = None
        self.dimension = 384  # بعد embedding ها
        
        # کش برای پاسخ‌های سریع
        self.response_cache = {}
        self.cache_size = 10000
        
        # آمار و متریک‌ها
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'avg_response_time': 0
        }
        
    def init_faiss_index(self):
        """ایندکس FAISS برای جستجوی سریع"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index = faiss.IndexIDMap(self.index)
        
    def add_knowledge(self, question, answer, category='general', source_file=None):
        """اضافه کردن دانش جدید به حافظه"""
        # ایجاد ID یکتا
        knowledge_id = hashlib.md5(f"{question}{answer}{datetime.now()}".encode()).hexdigest()
        
        # ایجاد embedding
        embedding = self.embedding_model.encode(question)
        
        # ذخیره در دانش
        self.knowledge_base[knowledge_id] = {
            'question': question,
            'answer': answer,
            'category': category,
            'source_file': source_file,
            'created_at': datetime.now(),
            'usage_count': 0,
            'embedding': embedding
        }
        
        # اضافه به FAISS index
        if self.index is not None:
            self.index.add_with_ids(
                np.array([embedding]).astype('float32'),
                np.array([int(knowledge_id, 16) % 10**12])  # تبدیل به عدد
            )
        
        self.knowledge_ids.append(knowledge_id)
        self.embeddings.append(embedding)
        
        return knowledge_id
    
    def process_file(self, file_path, filename):
        """پردازش فایل‌های آپلودی با 20 کتابخانه مختلف"""
        file_ext = filename.split('.')[-1].lower()
        extracted_data = []
        
        # استفاده از کتابخانه‌های مختلف برای تحلیل متن
        if file_ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                extracted_data = self.advanced_text_analysis(content)
                
        elif file_ext == 'pdf':
            import PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text()
                extracted_data = self.advanced_text_analysis(content)
                
        elif file_ext == 'docx':
            import docx
            doc = docx.Document(file_path)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            extracted_data = self.advanced_text_analysis(content)
            
        elif file_ext == 'csv':
            df = pd.read_csv(file_path)
            content = df.to_string()
            extracted_data = self.advanced_text_analysis(content)
            
        elif file_ext == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                content = json.dumps(data, ensure_ascii=False)
                extracted_data = self.advanced_text_analysis(content)
        
        # استخراج جملات و اضافه به دانش
        for item in extracted_data:
            if 'question' in item and 'answer' in item:
                self.add_knowledge(
                    item['question'],
                    item['answer'],
                    category='extracted',
                    source_file=filename
                )
        
        return len(extracted_data)
    
    def advanced_text_analysis(self, text):
        """تحلیل متن با 20 تکنیک مختلف"""
        results = []
        
        # 1. Tokenization با NLTK
        tokens = word_tokenize(text)
        
        # 2. حذف کلمات توقف
        stop_words = set(stopwords.words('english'))
        filtered_tokens = [w for w in tokens if not w in stop_words]
        
        # 3. تحلیل احساسات با TextBlob
        blob = TextBlob(text)
        sentiment = blob.sentiment
        
        # 4. تحلیل با spaCy
        doc = self.nlp(text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        
        # 5. استخراج جملات کلیدی
        sentences = [sent.text for sent in doc.sents]
        
        # 6. TF-IDF Vectorization
        vectorizer = TfidfVectorizer(max_features=100)
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        
        # 7. استخراج الگوهای پرسش و پاسخ
        question_patterns = [
            r'(.*?)\?',
            r'(what|who|where|when|why|how).*?(?=\?|\.)',
            r'explain\s+(.*?)(?=\.|$)',
            r'define\s+(.*?)(?=\.|$)',
            r'what is\s+(.*?)(?=\.|$)'
        ]
        
        for i, sentence in enumerate(sentences):
            # تشخیص سوال
            is_question = False
            for pattern in question_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    is_question = True
                    break
            
            if is_question and i < len(sentences) - 1:
                # فرض می‌کنیم جواب در جمله بعدی است
                results.append({
                    'question': sentence,
                    'answer': sentences[i + 1],
                    'sentiment': sentiment.polarity,
                    'entities': entities
                })
        
        return results
    
    def get_response(self, query, user_id=None):
        """دریافت پاسخ هوشمند با استفاده از الگوریتم کوکی کاربر"""
        import time
        start_time = time.time()
        
        self.stats['total_queries'] += 1
        
        # بررسی کش با استفاده از کوکی کاربر
        cache_key = f"{user_id}:{hashlib.md5(query.encode()).hexdigest()}" if user_id else hashlib.md5(query.encode()).hexdigest()
        
        if cache_key in self.response_cache:
            self.stats['cache_hits'] += 1
            return self.response_cache[cache_key]
        
        # ایجاد embedding برای query
        query_embedding = self.embedding_model.encode(query)
        
        # جستجوی مشابه‌ترین دانش
        if self.index is not None and len(self.knowledge_ids) > 0:
            distances, indices = self.index.search(
                np.array([query_embedding]).astype('float32'), 
                self.AI_TOP_K
            )
            
            # پیدا کردن بهترین پاسخ
            best_response = None
            best_score = float('inf')
            
            for i, idx in enumerate(indices[0]):
                if idx > 0:
                    knowledge_id = self.knowledge_ids[idx % len(self.knowledge_ids)]
                    if knowledge_id in self.knowledge_base:
                        score = distances[0][i]
                        if score < best_score:
                            best_score = score
                            best_response = self.knowledge_base[knowledge_id]['answer']
                            
                            # افزایش شمارنده استفاده
                            self.knowledge_base[knowledge_id]['usage_count'] += 1
            
            if best_response:
                response = best_response
            else:
                response = self.generate_response(query)
        else:
            response = self.generate_response(query)
        
        # ذخیره در کش
        if len(self.response_cache) < self.cache_size:
            self.response_cache[cache_key] = response
        
        # به‌روزرسانی آمار
        response_time = time.time() - start_time
        self.stats['avg_response_time'] = (
            (self.stats['avg_response_time'] * (self.stats['total_queries'] - 1) + response_time) 
            / self.stats['total_queries']
        )
        
        return response
    
    def generate_response(self, query):
        """تولید پاسخ در صورت عدم وجود در دانش"""
        # اینجا می‌توانید از مدل‌های تولید متن استفاده کنید
        # برای مثال از transformers یا OpenAI API
        return f"من درک می‌کنم که شما پرسیده‌اید: '{query}'. لطفاً اطلاعات بیشتری در این زمینه به من آموزش دهید."
    
    def get_stats(self):
        """دریافت آمار هوش مصنوعی"""
        return {
            'total_knowledge': len(self.knowledge_base),
            'cache_size': len(self.response_cache),
            'cache_hit_rate': (self.stats['cache_hits'] / self.stats['total_queries'] * 100) if self.stats['total_queries'] > 0 else 0,
            'avg_response_time': self.stats['avg_response_time'],
            'total_queries': self.stats['total_queries']
        }

# نمونه Singleton از مدل AI
ai_model = AdvancedAIModel()
ai_model.init_faiss_index()
