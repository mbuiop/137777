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
    
    # دانلود داده‌های مورد نیاز
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
            # مدل درک متن
            try:
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.dimension = 384
                print("✅ مدل درک متن آماده شد")
            except:
                self.model = None
                print("⚠️ مدل درک متن لود نشد")
            
            # کلمات توقف (Stop words)
            try:
                english_stops = set(stopwords.words('english'))
            except:
                english_stops = set()
            
            # کلمات توقف فارسی دستی
            persian_stops = {
                'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'را',
                'است', 'می', 'های', 'ها', 'کرد', 'شود', 'شده', 'نیز', 'یا',
                'اما', 'اگر', 'یا', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی'
            }
            
            self.stop_words = english_stops.union(persian_stops)
    
    def analyze_text(self, text):
        """تحلیل عمیق متن با ۱۰ تکنیک مختلف"""
        if not AI_READY:
            return {"error": "AI not ready", "simple": True}
        
        analysis = {}
        
        try:
            # 1. تحلیل احساسات
            blob = TextBlob(text)
            analysis['sentiment'] = {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
            
            # 2. استخراج کلمات کلیدی
            words = word_tokenize(text)
            words = [w.lower() for w in words if w.isalpha() and w.lower() not in self.stop_words]
            analysis['keywords'] = list(set(words))[:10]
            
            # 3. تشخیص زبان
            analysis['language'] = 'fa' if re.search('[\u0600-\u06FF]', text) else 'en'
            
            # 4. تعداد جملات
            sentences = sent_tokenize(text)
            analysis['sentence_count'] = len(sentences)
            
            # 5. سوالات موجود
            questions = [s for s in sentences if '?' in s or '؟' in s]
            analysis['questions'] = questions
            
            # 6. embedding برای جستجو
            if hasattr(self, 'model') and self.model:
                analysis['embedding'] = self.model.encode(text).tolist()
            
        except Exception as e:
            print(f"خطا در تحلیل: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def extract_qa_from_text(self, text):
        """استخراج سوال و جواب از متن"""
        qa_pairs = []
        try:
            sentences = sent_tokenize(text)
            
            for i, sent in enumerate(sentences):
                # اگه جمله سوال بود
                if '?' in sent or '؟' in sent:
                    # جواب میتونه جمله بعدی باشه
                    if i + 1 < len(sentences):
                        answer = sentences[i + 1]
                        if len(answer) > 10:  # جواب باید حداقل ۱۰ حرف باشه
                            qa_pairs.append({
                                'question': sent,
                                'answer': answer,
                                'confidence': 0.7
                            })
        except:
            pass
        
        return qa_pairs
    
    def process_file(self, file_path, filename):
        """پردازش فایل و استخراج دانش"""
        extracted = []
        file_ext = filename.split('.')[-1].lower()
        text = ""
        
        try:
            # خوندن فایل
            if file_ext == 'txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            elif file_ext == 'pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages:
                            text += page.extract_text()
                except:
                    text = "خطا در خوندن PDF"
            
            elif file_ext == 'docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                except:
                    text = "خطا در خوندن DOCX"
            
            elif file_ext == 'csv':
                try:
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    text = df.to_string()
                except:
                    text = "خطا در خوندن CSV"
            
            if text:
                # تحلیل متن
                analysis = self.analyze_text(text)
                
                # استخراج سوال و جواب
                qa_pairs = self.extract_qa_from_text(text)
                
                # اضافه کردن به دانش
                for qa in qa_pairs:
                    know = Knowledge(
                        question=qa['question'][:500],
                        answer=qa['answer'][:500],
                        category='extracted',
                        source=filename
                    )
                    db.session.add(know)
                    extracted.append(qa)
                
                db.session.commit()
            
            return {
                'extracted': len(extracted),
                'file': filename
            }
            
        except Exception as e:
            print(f"خطا: {e}")
            return {'extracted': 0, 'error': str(e)}
    
    def think(self, question):
        """پاسخ هوشمند به سوال"""
        question = question.strip()
        
        # چک کردن کش
        if question in self.cache:
            return self.cache[question]
        
        # گرفتن همه دانش‌ها
        all_know = Knowledge.query.all()
        
        # حالت ساده
        best_match = None
        best_score = 0
        
        for k in all_know:
            # مقایسه ساده
            if question.lower() in k.question.lower() or k.question.lower() in question.lower():
                score = len(set(question.lower().split()) & set(k.question.lower().split()))
                if score > best_score:
                    best_score = score
                    best_match = k
        
        if best_match:
            best_match.usage += 1
            db.session.commit()
            answer = best_match.answer
            self.cache[question] = answer
            return answer
        
        return "نمی‌دونم. می‌تونم یاد بگیرم اگه بهم یاد بدی"
    
    def learn(self, question, answer, category='general'):
        """یادگیری مطلب جدید"""
        know = Knowledge(
            question=question,
            answer=answer,
            category=category,
            source='manual'
        )
        db.session.add(know)
        db.session.commit()
        return "✅ یاد گرفتم!"
    
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
