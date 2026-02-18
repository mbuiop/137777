from m1_app import app, db, cache, redis_client
from m1_models import Knowledge
import numpy as np
import re
from datetime import datetime
import threading
import json
import pickle
from collections import defaultdict
import hashlib

# کتابخونه‌های هوش مصنوعی
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    from sklearn.metrics.pairwise import cosine_similarity
    from textblob import TextBlob
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    
    for pkg in ['punkt', 'stopwords', 'wordnet', 'punkt_tab']:
        try:
            nltk.download(pkg, quiet=True)
        except:
            pass
    
    AI_READY = True
    print("✅ هوش مصنوعی قوی آماده شد")
except Exception as e:
    AI_READY = False
    print(f"⚠️ خطا: {e}")

class MillionUserAI:
    def __init__(self):
        self.name = "هوش مصنوعی میلیون کاربر"
        self.version = "5.0"
        self.lock = threading.Lock()
        
        # آمار
        self.stats = defaultdict(int)
        self.stats['start_time'] = datetime.now()
        
        if AI_READY:
            try:
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.dimension = 384
                print(f"✅ مدل درک متن با ابعاد {self.dimension} آماده شد")
                
                # FAISS برای جستجوی سریع
                self.use_faiss = True
                self.index = faiss.IndexFlatIP(self.dimension)
                self.knowledge_list = []
                self.load_all_knowledge()
                
            except Exception as e:
                self.model = None
                self.use_faiss = False
                print(f"⚠️ خطا: {e}")
            
            # کلمات توقف
            try:
                english_stops = set(stopwords.words('english'))
            except:
                english_stops = set()
            
            persian_stops = {
                'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'را',
                'است', 'می', 'های', 'ها', 'کرد', 'شود', 'شده', 'نیز', 'یا',
                'اما', 'اگر', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی', 'بود',
                'دارد', 'کنید', 'شما', 'ما', 'ایشان', 'آنها', 'خواهد', 'باشند',
                'کردن', 'داشتن', 'گفتن', 'رفتن', 'آمدن', 'دادن', 'گرفتن'
            }
            self.stop_words = english_stops.union(persian_stops)
    
    def load_all_knowledge(self):
        """بارگذاری همه دانش‌ها در FAISS"""
        with app.app_context():
            try:
                all_know = Knowledge.query.all()
                
                if not all_know or not self.use_faiss:
                    return
                
                embeddings = []
                self.knowledge_list = []
                
                for k in all_know:
                    if k.question and len(k.question) > 5:
                        emb = self.model.encode(k.question)
                        embeddings.append(emb)
                        self.knowledge_list.append({
                            'id': k.id,
                            'question': k.question,
                            'answer': k.answer,
                            'category': k.category,
                            'usage': k.usage
                        })
                
                if embeddings:
                    embeddings_array = np.array(embeddings).astype('float32')
                    self.index.add(embeddings_array)
                    
                    # ذخیره در Redis برای دسترسی سریع
                    redis_client.set('faiss_size', len(embeddings))
                    
                    print(f"✅ {len(embeddings)} دانش در FAISS بارگذاری شد")
            except Exception as e:
                print(f"⚠️ خطا در بارگذاری FAISS: {e}")
    
    def think(self, question):
        """پاسخ با کش Redis"""
        self.stats['total_queries'] += 1
        question = question.strip()
        
        # ۱. چک کردن کش Redis
        cache_key = f"answer:{hashlib.md5(question.encode()).hexdigest()}"
        cached = redis_client.get(cache_key)
        if cached:
            self.stats['cache_hits'] += 1
            return cached
        
        # ۲. جستجوی سریع با FAISS
        if self.use_faiss and self.index.ntotal > 0:
            q_emb = self.model.encode(question).astype('float32').reshape(1, -1)
            scores, indices = self.index.search(q_emb, 5)
            
            if scores[0][0] > 0.7:  # شباهت بالا
                idx = indices[0][0]
                if idx < len(self.knowledge_list):
                    best = self.knowledge_list[idx]
                    
                    # آپدیت آمار در پس‌زمینه
                    try:
                        with app.app_context():
                            know = db.session.get(Knowledge, best['id'])
                            if know:
                                know.usage += 1
                                db.session.commit()
                    except:
                        pass
                    
                    # ذخیره در Redis
                    redis_client.setex(cache_key, 300, best['answer'])
                    
                    self.stats['faiss_hits'] += 1
                    return best['answer']
        
        # ۳. جستجوی مستقیم در دیتابیس
        with app.app_context():
            # استفاده از ایندکس برای سرعت
            all_know = Knowledge.query.order_by(Knowledge.usage.desc()).limit(100).all()
            
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
                
                # ذخیره در Redis
                redis_client.setex(cache_key, 300, best_match.answer)
                
                return best_match.answer
        
        return "نمی‌دونم. می‌تونم یاد بگیرم"
    
    def learn(self, question, answer, category='general'):
        """یادگیری با قفل"""
        with self.lock:
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
                
                # آپدیت FAISS
                if self.use_faiss and self.model:
                    emb = self.model.encode(question).astype('float32').reshape(1, -1)
                    self.index.add(emb)
                    self.knowledge_list.append({
                        'id': know.id,
                        'question': question,
                        'answer': answer,
                        'category': category,
                        'usage': 0
                    })
                
                # پاک کردن کش مربوطه
                cache_key = f"answer:{hashlib.md5(question.encode()).hexdigest()}"
                redis_client.delete(cache_key)
                
                self.stats['total_learns'] += 1
                return "✅ یاد گرفتم!"
                
            except Exception as e:
                return f"❌ خطا: {e}"
    
    def get_stats(self):
        """آمار کامل"""
        try:
            with app.app_context():
                total = Knowledge.query.count()
                top_used = Knowledge.query.order_by(Knowledge.usage.desc()).first()
            
            runtime = (datetime.now() - self.stats['start_time']).seconds
            hours = runtime // 3600
            minutes = (runtime % 3600) // 60
            
            return {
                'total_knowledge': total,
                'in_memory': len(self.knowledge_list) if hasattr(self, 'knowledge_list') else 0,
                'total_queries': self.stats['total_queries'],
                'cache_hits': self.stats['cache_hits'],
                'faiss_hits': self.stats.get('faiss_hits', 0),
                'cache_rate': (self.stats['cache_hits'] / max(self.stats['total_queries'], 1)) * 100,
                'total_learns': self.stats['total_learns'],
                'runtime': f"{hours}h {minutes}m",
                'top_question': top_used.question[:50] if top_used else 'None'
            }
        except Exception as e:
            return {'error': str(e)}

# ساخت نمونه
ai = MillionUserAI()
