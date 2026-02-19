import threading
import time
import json
from collections import defaultdict
import numpy as np
from datetime import datetime
from .similarity import SimilarityEngine
from .text_processor import TextProcessor
from models.database import Knowledge, db
from utils.cache import Cache
import hashlib

class Brain:
    """مغز اصلی هوش مصنوعی - با قابلیت یادگیری و پاسخگویی"""
    
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
            self.setup_brain()
    
    def setup_brain(self):
        """راه‌اندازی مغز"""
        self.text_processor = TextProcessor()
        self.similarity_engine = SimilarityEngine()
        self.cache = Cache()
        
        # تنظیمات
        self.config = {
            'similarity_threshold': 0.65,
            'max_results': 5,
            'learning_rate': 0.1,
            'min_confidence': 0.5
        }
        
        # آمار عملکرد
        self.stats = {
            'total_queries': 0,
            'successful_matches': 0,
            'avg_response_time': 0,
            'cache_hits': 0
        }
        
        self.stats_lock = threading.Lock()
        
        # بارگذاری دانش
        self.load_knowledge()
    
    def load_knowledge(self):
        """بارگذاری دانش از دیتابیس به حافظه"""
        try:
            self.knowledge_items = Knowledge.query.filter_by(is_active=True).all()
            print(f"🧠 مغز آماده شد: {len(self.knowledge_items)} دانش بارگذاری شد")
        except:
            self.knowledge_items = []
    
    def think(self, question, user_id=None):
        """فکر کردن به سوال و پیدا کردن جواب"""
        start_time = time.time()
        
        with self.stats_lock:
            self.stats['total_queries'] += 1
        
        # پاکسازی سوال
        clean_question = self.text_processor.clean_text(question)
        
        if not clean_question:
            return {
                'answer': '❌ سوال وارد نشده است',
                'confidence': 0,
                'type': 'error'
            }
        
        # بررسی کش
        cache_key = f"answer:{hashlib.md5(clean_question.encode()).hexdigest()}"
        cached = self.cache.get(cache_key)
        if cached:
            with self.stats_lock:
                self.stats['cache_hits'] += 1
            cached['from_cache'] = True
            return cached
        
        # جستجو در دانش
        result = self.search_in_brain(clean_question)
        
        # محاسبه زمان پاسخ
        response_time = time.time() - start_time
        
        # به‌روزرسانی آمار
        with self.stats_lock:
            self.stats['avg_response_time'] = (
                self.stats['avg_response_time'] * 0.9 + response_time * 0.1
            )
            if result['best_match']:
                self.stats['successful_matches'] += 1
        
        # آماده‌سازی پاسخ
        answer = self.prepare_answer(result, question)
        
        # ذخیره در تاریخچه
        self.save_to_history(question, answer, result, user_id, response_time)
        
        # ذخیره در کش
        self.cache.set(cache_key, answer, timeout=300)
        
        return answer
    
    def search_in_brain(self, question):
        """جستجو در مغز با الگوریتم پیشرفته"""
        
        if not self.knowledge_items:
            return {
                'best_match': None,
                'best_score': 0,
                'matches': [],
                'type': 'no_knowledge'
            }
        
        # پیدا کردن بهترین تطابق
        matches = self.similarity_engine.find_best_match(
            question, 
            self.knowledge_items,
            threshold=self.config['similarity_threshold']
        )
        
        return matches
    
    def prepare_answer(self, result, original_question):
        """آماده‌سازی پاسخ برای کاربر"""
        
        if not result['best_match']:
            # هیچ تطابقی پیدا نشد
            return {
                'answer': '❌ متاسفانه جواب این سوال را نمی‌دانم. میتوانید به من یاد دهید؟',
                'confidence': 0,
                'type': 'not_found',
                'suggestions': []
            }
        
        best = result['best_match']
        score = result['best_score']
        
        # به‌روزرسانی آمار استفاده
        best.update_usage(success=True)
        db.session.commit()
        
        # آماده‌سازی پاسخ
        answer_text = best.answer
        
        # اگر امتیاز پایین است، اخطار بده
        if score < 0.7:
            answer_text = f"⚠️ {answer_text}\n\n(این جواب با {int(score*100)}% اطمینان داده می‌شود)"
        
        # پیشنهاد سوالات مشابه
        suggestions = []
        for match in result['matches'][1:3]:  # دو تا از بهترین‌های بعدی
            if match['score'] > 0.5:
                suggestions.append({
                    'question': match['item'].question[:50],
                    'score': match['score']
                })
        
        return {
            'answer': answer_text,
            'confidence': score,
            'type': 'knowledge',
            'matches_count': result['count'],
            'suggestions': suggestions,
            'answer_id': best.id
        }
    
    def save_to_history(self, question, answer, result, user_id, response_time):
        """ذخیره در تاریخچه"""
        try:
            from models.database import ChatHistory
            
            history = ChatHistory(
                user_id=user_id or 'anonymous',
                session_id='temp',
                question=question[:500],
                question_length=len(question),
                answer=answer['answer'][:500],
                answer_id=result['best_match'].id if result['best_match'] else None,
                answer_type=answer['type'],
                confidence=answer.get('confidence', 0),
                response_time=response_time,
                created_at=datetime.now()
            )
            db.session.add(history)
            db.session.commit()
        except:
            pass
    
    def learn(self, question, answer, source='manual'):
        """یادگیری مستقیم"""
        try:
            # بررسی تکراری نبودن
            existing = Knowledge.query.filter_by(
                question_hash=self.text_processor.get_text_hash(question)
            ).first()
            
            if existing:
                # به‌روزرسانی دانش قبلی
                existing.answer = answer
                existing.version += 1
                existing.updated_at = datetime.now()
                db.session.commit()
                
                # به‌روزرسانی حافظه
                self.load_knowledge()
                
                return {'success': True, 'message': '✅ دانش به‌روزرسانی شد', 'updated': True}
            
            # ایجاد دانش جدید
            keywords = self.text_processor.extract_keywords(question + ' ' + answer)
            
            knowledge = Knowledge(
                question=question,
                question_hash=self.text_processor.get_text_hash(question),
                question_length=len(question),
                answer=answer,
                answer_length=len(answer),
                keywords=json.dumps(keywords),
                important_words=json.dumps(keywords[:5]),
                source_file=source,
                confidence=1.0,
                quality_score=1.0,
                created_at=datetime.now()
            )
            
            db.session.add(knowledge)
            db.session.commit()
            
            # به‌روزرسانی حافظه
            self.load_knowledge()
            
            return {'success': True, 'message': '✅ یاد گرفتم!', 'id': knowledge.id}
            
        except Exception as e:
            return {'success': False, 'message': f'❌ خطا: {str(e)}'}
    
    def learn_from_file(self, filepath, filename):
        """یادگیری از فایل"""
        start_time = time.time()
        learned = 0
        errors = 0
        
        try:
            from .learner import FileLearner
            learner = FileLearner()
            
            # استخراج جواب‌ها از فایل
            answers = learner.extract_answers(filepath, filename)
            
            # یادگیری هر جواب
            for answer_data in answers:
                result = self.learn(
                    question=answer_data['question'],
                    answer=answer_data['answer'],
                    source=f'file:{filename}'
                )
                if result['success']:
                    learned += 1
                else:
                    errors += 1
            
            # ذخیره تاریخچه
            from models.database import FileLearningHistory
            
            history = FileLearningHistory(
                filename=filename,
                file_size=os.path.getsize(filepath),
                total_lines=len(answers),
                extracted_count=learned + errors,
                learned_count=learned,
                status='success' if errors == 0 else 'partial',
                processing_time=time.time() - start_time
            )
            db.session.add(history)
            db.session.commit()
            
            return {
                'success': True,
                'learned': learned,
                'errors': errors,
                'message': f'✅ {learned} مورد یادگیری موفق'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'❌ خطا در پردازش فایل: {str(e)}'
            }
    
    def get_stats(self):
        """دریافت آمار مغز"""
        return {
            'total_knowledge': len(self.knowledge_items),
            **self.stats,
            'cache_size': self.cache.size(),
            'brain_status': 'active'
        }
    
    def forget(self, knowledge_id):
        """فراموش کردن یک دانش"""
        try:
            knowledge = Knowledge.query.get(knowledge_id)
            if knowledge:
                knowledge.is_active = False
                db.session.commit()
                self.load_knowledge()
                return True
        except:
            pass
        return False
