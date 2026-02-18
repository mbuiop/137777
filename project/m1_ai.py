from m1_models import Knowledge
from m1_app import db
import numpy as np
import re
import hashlib
from datetime import datetime

# کتابخونه‌های هوش مصنوعی
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    from textblob import TextBlob
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    
    AI_READY = True
    print("✅ هوش مصنوعی قوی آماده شد")
except Exception as e:
    AI_READY = False
    print(f"⚠️ هوش مصنوعی قوی نصب نیست: {e}")

class AdvancedAI:
    def __init__(self):
        self.name = "هوش مصنوعی پیشرفته"
        self.version = "3.0"
        self.knowledge_base = {}
        self.cache = {}
        
        if AI_READY:
            try:
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.dimension = 384
                print("✅ مدل درک متن آماده شد")
            except:
                self.model = None
                print("⚠️ مدل درک متن لود نشد")
            
            try:
                english_stops = set(stopwords.words('english'))
            except:
                english_stops = set()
            
            persian_stops = {
                'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'را',
                'است', 'می', 'های', 'ها', 'کرد', 'شود', 'شده', 'نیز', 'یا',
                'اما', 'اگر', 'یا', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی',
                'بود', 'دارد', 'کنید', 'شما', 'ما', 'ایشان', 'آنها'
            }
            
            self.stop_words = english_stops.union(persian_stops)
    
    def process_file(self, file_path, filename):
        """پردازش فایل و استخراج دانش"""
        extracted = 0
        file_ext = filename.split('.')[-1].lower()
        text = ""
        
        try:
            # خوندن فایل
            if file_ext == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                print(f"✅ فایل txt خوند: {len(text)} کاراکتر")
            
            elif file_ext == 'pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages:
                            text += page.extract_text()
                    print(f"✅ فایل pdf خوند: {len(text)} کاراکتر")
                except Exception as e:
                    print(f"خطا در pdf: {e}")
                    return {'extracted': 0, 'error': 'خطا در خوندن PDF'}
            
            elif file_ext == 'docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    print(f"✅ فایل docx خوند: {len(text)} کاراکتر")
                except Exception as e:
                    print(f"خطا در docx: {e}")
                    return {'extracted': 0, 'error': 'خطا در خوندن DOCX'}
            
            if text and len(text) > 50:
                # تقسیم متن به خطوط
                lines = text.split('\n')
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line or len(line) < 10:
                        continue
                    
                    # اگه خط سوال بود (علامت سوال داشت)
                    if '?' in line or '؟' in line:
                        # دنبال جواب میگردیم
                        for j in range(i+1, min(i+3, len(lines))):
                            answer = lines[j].strip()
                            if answer and len(answer) > 10 and not ('?' in answer or '؟' in answer):
                                # اضافه به دیتابیس
                                know = Knowledge(
                                    question=line[:500],
                                    answer=answer[:500],
                                    category='file',
                                    source=filename,
                                    confidence=0.8
                                )
                                db.session.add(know)
                                extracted += 1
                                print(f"✅ یادگرفتم: {line[:50]}...")
                                break
                
                db.session.commit()
                print(f"✅ {extracted} مورد یادگیری از فایل استخراج شد")
            
            return {'extracted': extracted, 'file': filename}
            
        except Exception as e:
            print(f"خطا کلی: {e}")
            return {'extracted': 0, 'error': str(e)}
    
    def think(self, question):
        """پاسخ هوشمند به سوال"""
        question = question.strip()
        
        # چک کردن کش
        if question in self.cache:
            return self.cache[question]
        
        # گرفتن همه دانش‌ها
        all_know = Knowledge.query.all()
        
        if not all_know:
            return "هنوز چیزی یاد نگرفتم. به من یاد بده"
        
        # جستجوی ساده
        best_match = None
        best_score = 0
        
        question_words = set(question.lower().split())
        
        for k in all_know:
            k_words = set(k.question.lower().split())
            common = question_words.intersection(k_words)
            score = len(common)
            
            if score > best_score and score > 0:
                best_score = score
                best_match = k
        
        if best_match:
            best_match.usage += 1
            db.session.commit()
            answer = best_match.answer
            self.cache[question] = answer
            return answer
        
        return "نمی‌دونم. می‌تونم یاد بگیرم"
    
    def learn(self, question, answer, category='general'):
        """یادگیری مطلب جدید"""
        try:
            know = Knowledge(
                question=question,
                answer=answer,
                category=category,
                source='manual',
                confidence=1.0
            )
            db.session.add(know)
            db.session.commit()
            return "✅ یاد گرفتم!"
        except Exception as e:
            print(f"خطا در یادگیری: {e}")
            return f"❌ خطا: {e}"
    
    def get_stats(self):
        """گرفتن آمار"""
        all_know = Knowledge.query.all()
        total = len(all_know)
        avg_usage = sum(k.usage for k in all_know) / max(total, 1)
        categories = list(set(k.category for k in all_know if k.category))
        
        return {
            'total': total,
            'avg_usage': avg_usage,
            'categories': categories if categories else ['general']
        }

# ساخت نمونه از هوش مصنوعی
ai = AdvancedAI()
