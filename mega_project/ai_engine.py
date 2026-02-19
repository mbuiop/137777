from brain import knowledge_base, learn_from_text, smart_search as brain_search
from database import KnowledgeDB, db
from cache import RedisCache
import threading
import time
from difflib import SequenceMatcher
import numpy as np

class AIEngine:
    def __init__(self):
        self.cache = RedisCache()
        self.lock = threading.Lock()
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'db_hits': 0,
            'brain_hits': 0
        }
    
    def search(self, question, user_id=None):
        """جستجوی هوشمند با ۳ لایه"""
        self.stats['total_queries'] += 1
        
        # لایه ۱: کش
        cached = self.cache.get_answer(question)
        if cached:
            self.stats['cache_hits'] += 1
            return cached
        
        # لایه ۲: دیتابیس PostgreSQL
        db_result = self._search_db(question)
        if db_result:
            self.stats['db_hits'] += 1
            self.cache.set_answer(question, db_result)
            return db_result
        
        # لایه ۳: حافظه اصلی (brain)
        brain_result = brain_search(question)
        if brain_result != "نمی‌دونم. میشه بیشتر توضیح بدی؟":
            self.stats['brain_hits'] += 1
            self.cache.set_answer(question, brain_result)
            return brain_result
        
        return "نمی‌دونم"
    
    def _search_db(self, question):
        """جستجو در دیتابیس"""
        try:
            # پیدا کردن مشابه‌ترین سوال
            all_knowledge = KnowledgeDB.query.all()
            best_match = None
            best_ratio = 0
            
            for k in all_knowledge:
                ratio = SequenceMatcher(None, question.lower(), k.question.lower()).ratio()
                if ratio > best_ratio and ratio > 0.6:
                    best_ratio = ratio
                    best_match = k
            
            if best_match:
                best_match.usage += 1
                db.session.commit()
                return best_match.answer
        except:
            pass
        return None
    
    def learn(self, question, answer, category='general'):
        """یادگیری در همه لایه‌ها"""
        with self.lock:
            # یادگیری در حافظه اصلی
            learn_from_text(question, answer)
            
            # ذخیره در دیتابیس
            try:
                know = KnowledgeDB(
                    question=question,
                    answer=answer,
                    category=category
                )
                db.session.add(know)
                db.session.commit()
            except:
                pass
            
            # پاک کردن کش مربوطه
            self.cache.set_answer(question, answer)
            
            return True
    
    def get_stats(self):
        """آمار کامل"""
        return {
            **self.stats,
            'cache_info': self.cache.get_stats(),
            'brain_size': len(knowledge_base)
        }

ai = AIEngine()
