import numpy as np
import pickle
import json
import hashlib
from datetime import datetime
from collections import defaultdict
import threading
from app import db, cache, app
from app.models import Knowledge
import os

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    from sklearn.metrics.pairwise import cosine_similarity
    from textblob import TextBlob
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    
    for pkg in ['punkt', 'stopwords', 'wordnet']:
        try:
            nltk.download(pkg, quiet=True)
        except:
            pass
    
    AI_READY = True
except Exception as e:
    AI_READY = False
    print(f"⚠️ AI Libraries Warning: {e}")

class MegaAI:
    def __init__(self):
        self.name = "Mega AI System"
        self.version = "10.0"
        self.lock = threading.RLock()
        
        # Stats
        self.stats = defaultdict(int)
        self.stats['start_time'] = datetime.now()
        
        # Cache
        self.local_cache = {}
        self.max_cache = 100000
        
        # Initialize AI
        if AI_READY:
            self._init_ai_models()
            self._init_faiss()
            self._init_stopwords()
            self._load_knowledge()
    
    def _init_ai_models(self):
        """Initialize AI models"""
        try:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.dimension = 384
            print(f"✅ AI Model loaded (dim={self.dimension})")
        except Exception as e:
            self.model = None
            print(f"⚠️ Model load failed: {e}")
    
    def _init_faiss(self):
        """Initialize FAISS index"""
        try:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIDMap(self.index)
            self.knowledge_map = {}
            self.use_faiss = True
            print("✅ FAISS index ready")
        except:
            self.use_faiss = False
            print("⚠️ FAISS not available")
    
    def _init_stopwords(self):
        """Initialize stopwords"""
        try:
            english_stops = set(stopwords.words('english'))
        except:
            english_stops = set()
        
        persian_stops = set([
            'و', 'در', 'به', 'از', 'که', 'این', 'آن', 'با', 'برای', 'را',
            'است', 'می', 'های', 'ها', 'کرد', 'شود', 'شده', 'نیز', 'یا',
            'اما', 'اگر', 'تا', 'چه', 'چی', 'چرا', 'کجا', 'کی', 'بود',
            'دارد', 'کنید', 'شما', 'ما', 'ایشان', 'آنها', 'خواهد'
        ])
        
        self.stop_words = english_stops.union(persian_stops)
    
    def _load_knowledge(self):
        """Load all knowledge into FAISS"""
        if not self.use_faiss:
            return
        
        with app.app_context():
            try:
                knowledge = Knowledge.query.all()
                if not knowledge:
                    return
                
                embeddings = []
                ids = []
                
                for k in knowledge:
                    if k.question and len(k.question) > 3:
                        emb = self.model.encode(k.question)
                        embeddings.append(emb)
                        ids.append(k.id)
                        self.knowledge_map[k.id] = k
                
                if embeddings:
                    embeddings_array = np.array(embeddings).astype('float32')
                    ids_array = np.array(ids).astype('int64')
                    self.index.add_with_ids(embeddings_array, ids_array)
                    
                    app.redis_client.set('faiss_size', len(embeddings))
                    print(f"✅ Loaded {len(embeddings)} knowledge items")
                    
            except Exception as e:
                print(f"⚠️ Load knowledge failed: {e}")
    
    @cache.memoize(timeout=600)
    def think(self, question, user_id=None):
        """Get answer with caching"""
        self.stats['total_queries'] += 1
        question = question.strip()
        
        # Redis cache
        cache_key = f"answer:{hashlib.md5(question.encode()).hexdigest()}"
        cached = app.redis_client.get(cache_key)
        if cached:
            self.stats['cache_hits'] += 1
            return cached
        
        # FAISS search
        if self.use_faiss and self.index.ntotal > 0:
            q_emb = self.model.encode(question).astype('float32').reshape(1, -1)
            scores, indices = self.index.search(q_emb, 5)
            
            if scores[0][0] > 0.65:  # Similarity threshold
                knowledge_id = indices[0][0]
                if knowledge_id in self.knowledge_map:
                    knowledge = self.knowledge_map[knowledge_id]
                    
                    # Update usage async
                    self._update_usage(knowledge.id)
                    
                    # Cache result
                    app.redis_client.setex(cache_key, 600, knowledge.answer)
                    
                    self.stats['faiss_hits'] += 1
                    return knowledge.answer
        
        # Database search
        return self._db_search(question, cache_key)
    
    def _db_search(self, question, cache_key):
        """Search in database"""
        with app.app_context():
            try:
                # Get most relevant knowledge
                knowledge = Knowledge.query.order_by(
                    Knowledge.usage.desc()
                ).limit(100).all()
                
                best_match = None
                best_score = 0
                q_words = set(question.lower().split())
                
                for k in knowledge:
                    k_words = set(k.question.lower().split())
                    score = len(q_words.intersection(k_words))
                    
                    if score > best_score and score > 1:
                        best_score = score
                        best_match = k
                
                if best_match:
                    self._update_usage(best_match.id)
                    app.redis_client.setex(cache_key, 600, best_match.answer)
                    return best_match.answer
                    
            except Exception as e:
                app.logger.error(f"DB search error: {e}")
        
        return "متوجه نشدم. میشه بیشتر توضیح بدید؟"
    
    def _update_usage(self, knowledge_id):
        """Update usage count in background"""
        try:
            with app.app_context():
                knowledge = db.session.get(Knowledge, knowledge_id)
                if knowledge:
                    knowledge.usage += 1
                    db.session.commit()
        except:
            pass
    
    def learn(self, question, answer, category='general', source='manual'):
        """Add new knowledge"""
        with self.lock:
            try:
                knowledge = Knowledge(
                    question=question,
                    answer=answer,
                    category=category,
                    source=source,
                    language=self.detect_language(question)
                )
                db.session.add(knowledge)
                db.session.commit()
                
                # Update FAISS
                if self.use_faiss and self.model:
                    emb = self.model.encode(question).astype('float32').reshape(1, -1)
                    self.index.add_with_ids(emb, np.array([knowledge.id]))
                    self.knowledge_map[knowledge.id] = knowledge
                
                # Clear cache
                cache_key = f"answer:{hashlib.md5(question.encode()).hexdigest()}"
                app.redis_client.delete(cache_key)
                
                self.stats['total_learns'] += 1
                return True, "✅ یاد گرفتم!"
                
            except Exception as e:
                return False, f"❌ خطا: {e}"
    
    def detect_language(self, text):
        """Detect text language"""
        if re.search('[\u0600-\u06FF]', text):
            return 'fa'
        return 'en'
    
    def process_file(self, file_path, filename, user_id=None):
        """Process uploaded file"""
        extracted = 0
        file_ext = filename.split('.')[-1].lower()
        
        try:
            text = self._extract_text(file_path, file_ext)
            
            if text and len(text) > 100:
                sentences = sent_tokenize(text)
                
                for i, sent in enumerate(sentences):
                    if '?' in sent or '؟' in sent:
                        for j in range(i+1, min(i+3, len(sentences))):
                            answer = sentences[j].strip()
                            if answer and len(answer) > 20:
                                success, _ = self.learn(
                                    sent[:500], 
                                    answer[:500], 
                                    category='extracted',
                                    source=filename
                                )
                                if success:
                                    extracted += 1
                                break
            
            return extracted
            
        except Exception as e:
            app.logger.error(f"File processing error: {e}")
            return 0
    
    def _extract_text(self, file_path, file_ext):
        """Extract text from file"""
        text = ""
        
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
                text = "\n".join([p.text for p in doc.paragraphs])
            except:
                pass
        
        elif file_ext == 'csv':
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                text = df.to_string()
            except:
                pass
        
        return text
    
    def get_stats(self):
        """Get system stats"""
        with app.app_context():
            total_knowledge = Knowledge.query.count()
            top_used = Knowledge.query.order_by(
                Knowledge.usage.desc()
            ).first()
        
        runtime = (datetime.now() - self.stats['start_time']).seconds
        hours = runtime // 3600
        minutes = (runtime % 3600) // 60
        
        return {
            'name': self.name,
            'version': self.version,
            'total_knowledge': total_knowledge,
            'in_memory': len(self.knowledge_map) if hasattr(self, 'knowledge_map') else 0,
            'total_queries': self.stats['total_queries'],
            'cache_hits': self.stats['cache_hits'],
            'faiss_hits': self.stats.get('faiss_hits', 0),
            'cache_rate': (self.stats['cache_hits'] / max(self.stats['total_queries'], 1)) * 100,
            'total_learns': self.stats['total_learns'],
            'runtime': f"{hours}h {minutes}m",
            'top_question': top_used.question[:50] if top_used else 'None'
        }

# Global AI instance
ai = MegaAI()
