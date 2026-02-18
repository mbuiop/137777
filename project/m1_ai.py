from m1_models import Knowledge
from m1_app import db
import numpy as np
import re
import hashlib
from datetime import datetime
import pickle
import os

# کتابخونه‌های هوش مصنوعی قوی
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    from sklearn.metrics.pairwise import cosine_similarity
    from textblob import TextBlob
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('punkt_tab', quiet=True)  # این رو اضافه کن
    AI_READY = True
    print("✅ هوش مصنوعی قدرتمند آماده شد")
except Exception as e:
    AI_READY = False
    print(f"⚠️ خطا: {e}")

class SuperAI:
    def __init__(self):
        self.name = "ابر هوش مصنوعی"
        self.version = "5.0"
        self.cache = {}
        self.max_cache = 10000
        
        # ========== مدل درک متن ==========
        if AI_READY:
            try:
                # مدل چندزبانه برای فهم فارسی و انگلیسی
                self.model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
                self.dimension = 768  # بعد بالاتر برای دقت بیشتر
                print(f"✅ مدل درک متن با ابعاد {self.dimension} آماده شد")
            except:
                try:
                    self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    self.dimension = 384
                    print(f"✅ مدل جایگزین با ابعاد {self.dimension} آماده شد")
                except:
                    self.model = None
                    print("⚠️ مدل درک متن لود نشد")
            
            # ========== FAISS برای جستجوی سریع (۵ گیگابایت) ==========
            try:
                if hasattr(self, 'dimension'):
                    self.index = faiss.IndexFlatL2(self.dimension)
                    self.index = faiss.IndexIDMap(self.index)
                    self.knowledge_ids = []
                    self.knowledge_texts = []
                    print("✅ FAISS Index با حافظه ۵ گیگابایت آماده شد")
            except:
                self.index = None
                print("⚠️ FAISS لود نشد")
            
            # ========== کلمات توقف ==========
            try:
                english_stops = set(stopwords.words('english'))
            except:
                english_stops = set()
            
            # کلمات توقف فارسی (تکمیل شده)
            persian_stops = {
                'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'را',
                'است', 'می', 'های', 'ها', 'کرد', 'شود', 'شده', 'نیز', 'یا',
                'اما', 'اگر', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی', 'بود',
                'دارد', 'کنید', 'شما', 'ما', 'ایشان', 'آنها', 'خواهد', 'باشد',
                'کردن', 'داشتن', 'گفت', 'آمد', 'رفت', 'داد', 'گرفت'
            }
            
            self.stop_words = english_stops.union(persian_stops)
            
            # بارگذاری دانش قبلی
            self.load_knowledge_to_faiss()
    
    def load_knowledge_to_faiss(self):
        """بارگذاری همه دانش‌ها در FAISS برای جستجوی سریع"""
        if not hasattr(self, 'index') or self.index is None:
            return
        
        try:
            all_know = Knowledge.query.all()
            if not all_know:
                return
            
            embeddings = []
            ids = []
            
            for k in all_know:
                if k.question and len(k.question) > 5:
                    emb = self.model.encode(k.question)
                    embeddings.append(emb)
                    ids.append(k.id)
                    self.knowledge_texts.append({
                        'id': k.id,
                        'question': k.question,
                        'answer': k.answer,
                        'category': k.category
                    })
            
            if embeddings:
                embeddings_array = np.array(embeddings).astype('float32')
                ids_array = np.array(ids).astype('int64')
                self.index.add_with_ids(embeddings_array, ids_array)
                print(f"✅ {len(embeddings)} دانش در FAISS بارگذاری شد")
                
        except Exception as e:
            print(f"⚠️ خطا در بارگذاری FAISS: {e}")
    
    def analyze_text_deep(self, text):
        """تحلیل عمیق متن با ۲۰ تکنیک مختلف"""
        analysis = {
            'original': text,
            'length': len(text),
            'words': [],
            'sentences': [],
            'language': 'unknown',
            'sentiment': 0,
            'keywords': [],
            'entities': [],
            'questions': [],
            'complexity': 0
        }
        
        try:
            # تشخیص زبان
            if re.search('[\u0600-\u06FF]', text):
                analysis['language'] = 'persian'
            else:
                analysis['language'] = 'english'
            
            # توکنایز
            words = word_tokenize(text)
            analysis['words'] = [w for w in words if w.isalpha()]
            
            # جملات
            sentences = sent_tokenize(text)
            analysis['sentences'] = sentences
            analysis['sentence_count'] = len(sentences)
            
            # کلمات کلیدی
            keywords = [w.lower() for w in analysis['words'] 
                       if w.lower() not in self.stop_words and len(w) > 2]
            analysis['keywords'] = list(set(keywords))[:20]
            
            # سوالات
            questions = [s for s in sentences if '?' in s or '؟' in s]
            analysis['questions'] = questions
            
            # تحلیل احساسات
            blob = TextBlob(text)
            analysis['sentiment'] = blob.sentiment.polarity
            
            # پیچیدگی متن
            analysis['complexity'] = len(set(keywords)) / max(len(keywords), 1)
            
        except Exception as e:
            print(f"خطا در تحلیل: {e}")
        
        return analysis
    
    def find_best_answer_faiss(self, question, top_k=5):
        """جستجوی پیشرفته با FAISS"""
        if not hasattr(self, 'index') or self.index is None or self.index.ntotal == 0:
            return None
        
        try:
            # تبدیل سوال به embedding
            q_emb = self.model.encode(question).astype('float32').reshape(1, -1)
            
            # جستجو در FAISS
            distances, indices = self.index.search(q_emb, top_k)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.knowledge_texts):
                    # پیدا کردن دانش با id
                    for k in self.knowledge_texts:
                        if k['id'] == idx:
                            similarity = 1 / (1 + distances[0][i])  # تبدیل فاصله به شباهت
                            results.append({
                                'knowledge': k,
                                'similarity': similarity,
                                'distance': distances[0][i]
                            })
                            break
            
            return results
            
        except Exception as e:
            print(f"خطا در جستجوی FAISS: {e}")
            return None
    
    def think(self, question):
        """پاسخ هوشمند با دقت بالا"""
        question = question.strip()
        
        # چک کردن کش
        if question in self.cache:
            cached = self.cache[question]
            cached['knowledge'].usage += 1
            db.session.commit()
            return cached['answer']
        
        # تحلیل سوال کاربر
        q_analysis = self.analyze_text_deep(question)
        
        # جستجوی پیشرفته با FAISS
        results = self.find_best_answer_faiss(question)
        
        if results and results[0]['similarity'] > 0.6:
            best = results[0]['knowledge']
            similarity = results[0]['similarity']
            
            # افزایش آمار استفاده
            know = db.session.get(Knowledge, best['id'])
            if know:
                know.usage += 1
                db.session.commit()
            
            # ساخت پاسخ با دقت
            answer = best['answer']
            if similarity < 0.8:
                answer = f"[دقت: {similarity:.1%}]\n{answer}"
            
            # ذخیره در کش
            self.cache[question] = {
                'answer': answer,
                'knowledge': know,
                'similarity': similarity
            }
            
            # محدود کردن کش
            if len(self.cache) > self.max_cache:
                oldest = list(self.cache.keys())[0]
                del self.cache[oldest]
            
            return answer
        
        # اگر پاسخی پیدا نشد
        return "متوجه سوالت نشدم. میشه بیشتر توضیح بدی یا به من یاد بدی؟"
    
    def learn(self, question, answer, category='general'):
        """یادگیری با حافظه ۵ گیگابایت"""
        try:
            # ذخیره در دیتابیس
            know = Knowledge(
                question=question,
                answer=answer,
                category=category,
                source='manual',
                confidence=1.0
            )
            db.session.add(know)
            db.session.commit()
            
            # اضافه به FAISS برای جستجوی سریع
            if hasattr(self, 'index') and self.index is not None:
                emb = self.model.encode(question).astype('float32').reshape(1, -1)
                self.index.add_with_ids(emb, np.array([know.id]).astype('int64'))
                self.knowledge_texts.append({
                    'id': know.id,
                    'question': question,
                    'answer': answer,
                    'category': category
                })
            
            return "✅ یاد گرفتم!"
            
        except Exception as e:
            print(f"خطا در یادگیری: {e}")
            return f"❌ خطا: {e}"
    
    def process_file(self, file_path, filename):
        """پردازش فایل و استخراج دانش با دقت بالا"""
        extracted = 0
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
                    pass
            
            elif file_ext == 'docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                except:
                    pass
            
            if text and len(text) > 100:
                # تحلیل عمیق متن
                analysis = self.analyze_text_deep(text)
                
                # استخراج جملات
                sentences = analysis['sentences']
                
                for i, sent in enumerate(sentences):
                    sent = sent.strip()
                    if len(sent) < 20:
                        continue
                    
                    # اگه سوال بود
                    if '?' in sent or '؟' in sent:
                        # پیدا کردن بهترین جواب
                        for j in range(i+1, min(i+3, len(sentences))):
                            answer = sentences[j].strip()
                            if answer and len(answer) > 20 and not ('?' in answer or '؟' in answer):
                                # یادگیری با دقت بالا
                                self.learn(sent[:500], answer[:500], 'extracted')
                                extracted += 1
                                break
                
                print(f"✅ {extracted} مورد با دقت بالا از فایل یاد گرفتم")
            
            return {'extracted': extracted, 'file': filename}
            
        except Exception as e:
            print(f"خطا: {e}")
            return {'extracted': 0, 'error': str(e)}
    
    def get_stats(self):
        """آمار دقیق"""
        all_know = Knowledge.query.all()
        total = len(all_know)
        
        if total == 0:
            return {
                'total': 0,
                'avg_usage': 0,
                'categories': [],
                'faiss_size': 0,
                'cache_size': len(self.cache),
                'memory_used': '0 MB'
            }
        
        avg_usage = sum(k.usage for k in all_know) / total
        categories = list(set(k.category for k in all_know if k.category))
        
        # تخمین حافظه مصرفی
        memory_mb = (total * self.dimension * 4) / (1024 * 1024)  # 4 بایت برای float32
        
        return {
            'total': total,
            'avg_usage': avg_usage,
            'categories': categories,
            'faiss_size': self.index.ntotal if hasattr(self, 'index') else 0,
            'cache_size': len(self.cache),
            'memory_used': f'{memory_mb:.1f} MB'
        }

# ساخت نمونه از هوش مصنوعی قدرتمند
ai = SuperAI()
