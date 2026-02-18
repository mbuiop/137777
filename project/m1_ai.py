from m1_app import app, db, cache
from m1_models import Knowledge
import numpy as np
import re
from datetime import datetime
import threading
from collections import defaultdict

# کتابخونه‌های هوش مصنوعی
try:
    from sentence_transformers import SentenceTransformer
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

class SuperAI:
    def __init__(self):
        self.name = "هوش مصنوعی قوی"
        self.version = "4.0"
        self.cache = {}
        self.max_cache = 5000
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
                import faiss
                self.use_faiss = True
                self.index = faiss.IndexFlatL2(self.dimension)
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
                'اما', 'اگر', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی', 'بود'
            }
            self.stop_words = english_stops.union(persian_stops)
    
    def load_all_knowledge(self):
        """بارگذاری همه دانش‌ها"""
        with app.app_context():
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
                print(f"✅ {len(embeddings)} دانش در حافظه بارگذاری شد")
    
    @cache.memoize(timeout=300)
    def think(self, question):
        """پاسخ با کش"""
        self.stats['total_queries'] += 1
        question = question.strip()
        
        # جستجوی سریع با FAISS
        if self.use_faiss and self.index.ntotal > 0:
            q_emb = self.model.encode(question).astype('float32').reshape(1, -1)
            distances, indices = self.index.search(q_emb, 3)
            
            if distances[0][0] < 1.0:
                idx = indices[0][0]
                if idx < len(self.knowledge_list):
                    best = self.knowledge_list[idx]
                    
                    # آپدیت آمار
                    with app.app_context():
                        know = db.session.get(Knowledge, best['id'])
                        if know:
                            know.usage += 1
                            db.session.commit()
                    
                    self.stats['cache_hits'] += 1
                    return best['answer']
        
        # جستجوی ساده
        with app.app_context():
            all_know = Knowledge.query.all()
            
            best_match = None
            best_score = 0
            
            for k in all_know:
                if question.lower() in k.question.lower() or k.question.lower() in question.lower():
                    score = len(set(question.lower().split()) & set(k.question.lower().split()))
                    if score > best_score:
                        best_score = score
                        best_match = k
            
            if best_match:
                best_match.usage += 1
                db.session.commit()
                return best_match.answer
        
        return "نمی‌دونم. می‌تونم یاد بگیرم"
    
    def learn(self, question, answer, category='general'):
        """یادگیری"""
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
                
                cache.clear()
                self.stats['total_learns'] += 1
                return "✅ یاد گرفتم!"
                
            except Exception as e:
                return f"❌ خطا: {e}"
    
    def process_file(self, file_path, filename):
        """پردازش فایل"""
        extracted = 0
        text = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if text and len(text) > 100:
                sentences = sent_tokenize(text)
                
                for i, sent in enumerate(sentences):
                    sent = sent.strip()
                    if len(sent) < 20:
                        continue
                    
                    if '?' in sent or '؟' in sent:
                        for j in range(i+1, min(i+3, len(sentences))):
                            answer = sentences[j].strip()
                            if answer and len(answer) > 20:
                                self.learn(sent[:500], answer[:500], 'extracted')
                                extracted += 1
                                break
            
            self.stats['total_files'] += 1
            return {'extracted': extracted, 'file': filename}
            
        except Exception as e:
            return {'extracted': 0, 'error': str(e)}
    
    def get_stats(self):
        """آمار"""
        with app.app_context():
            total = Knowledge.query.count()
        
        runtime = (datetime.now() - self.stats['start_time']).seconds
        
        return {
            'total_knowledge': total,
            'in_memory': len(self.knowledge_list) if hasattr(self, 'knowledge_list') else 0,
            'total_queries': self.stats['total_queries'],
            'cache_hits': self.stats['cache_hits'],
            'total_learns': self.stats['total_learns'],
            'total_files': self.stats['total_files'],
            'runtime': f"{runtime//3600}h {(runtime%3600)//60}m"
        }

# ساخت نمونه
ai = SuperAI()
