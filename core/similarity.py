import numpy as np
from difflib import SequenceMatcher
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from collections import Counter
import hashlib
import threading
from .text_processor import TextProcessor

class SimilarityEngine:
    """موتور محاسبه شباهت پیشرفته"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 3),
            analyzer='char'
        )
        
        # کش شباهت‌ها
        self.similarity_cache = {}
        self.cache_lock = threading.Lock()
        
        # وزن‌دهی به معیارهای مختلف
        self.weights = {
            'exact_match': 1.0,      # تطابق دقیق
            'partial_match': 0.8,     # تطابق جزیی
            'word_overlap': 0.7,       # اشتراک کلمات
            'semantic': 0.6,           # شباهت معنایی
            'keyword': 0.9,            # کلمات کلیدی
            'length_similarity': 0.3    # شباهت طول
        }
    
    def exact_match(self, text1, text2):
        """تطابق دقیق (هش شده)"""
        hash1 = self.text_processor.get_text_hash(text1)
        hash2 = self.text_processor.get_text_hash(text2)
        return 1.0 if hash1 == hash2 else 0.0
    
    def partial_match(self, text1, text2):
        """تطابق جزیی با SequenceMatcher"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def word_overlap(self, text1, text2):
        """اشتراک کلمات"""
        words1 = set(self.text_processor.tokenize(text1))
        words2 = set(self.text_processor.tokenize(text2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard similarity
        return len(intersection) / len(union)
    
    def keyword_match(self, text1, text2):
        """تطابق بر اساس کلمات کلیدی"""
        keywords1 = set(self.text_processor.extract_keywords(text1, max_keywords=5))
        keywords2 = set(self.text_processor.extract_keywords(text2, max_keywords=5))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        common = keywords1.intersection(keywords2)
        
        # وزن‌دهی به کلمات کلیدی مشترک
        score = len(common) / max(len(keywords1), len(keywords2))
        
        return score
    
    def length_similarity(self, text1, text2):
        """شباهت بر اساس طول متن"""
        len1 = len(text1)
        len2 = len(text2)
        
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # نسبت طول‌ها
        ratio = min(len1, len2) / max(len1, len2)
        return ratio
    
    def combined_similarity(self, text1, text2):
        """ترکیب همه معیارهای شباهت"""
        
        # محاسبه همه معیارها
        similarities = {
            'exact_match': self.exact_match(text1, text2),
            'partial_match': self.partial_match(text1, text2),
            'word_overlap': self.word_overlap(text1, text2),
            'keyword_match': self.keyword_match(text1, text2),
            'length_similarity': self.length_similarity(text1, text2)
        }
        
        # محاسبه امتیاز نهایی با وزن‌ها
        total_score = 0
        total_weight = 0
        
        for metric, score in similarities.items():
            weight = self.weights.get(metric, 0.5)
            total_score += score * weight
            total_weight += weight
        
        final_score = total_score / total_weight if total_weight > 0 else 0
        
        return final_score, similarities
    
    def find_best_match(self, question, knowledge_items, threshold=0.6):
        """پیدا کردن بهترین تطابق"""
        
        cache_key = hashlib.md5(question.encode()).hexdigest()
        
        # بررسی کش
        with self.cache_lock:
            if cache_key in self.similarity_cache:
                cached = self.similarity_cache[cache_key]
                # کش به مدت 5 دقیقه معتبر است
                if cached['time'] > 0:
                    return cached['result']
        
        best_match = None
        best_score = 0
        all_matches = []
        
        for item in knowledge_items:
            score, details = self.combined_similarity(question, item.question)
            
            if score >= threshold:
                all_matches.append({
                    'item': item,
                    'score': score,
                    'details': details
                })
                
                if score > best_score:
                    best_score = score
                    best_match = item
        
        # مرتب‌سازی نتایج
        all_matches.sort(key=lambda x: x['score'], reverse=True)
        
        result = {
            'best': best_match,
            'best_score': best_score,
            'matches': all_matches[:5],  # ۵ نتیجه برتر
            'count': len(all_matches)
        }
        
        # ذخیره در کش
        with self.cache_lock:
            self.similarity_cache[cache_key] = {
                'result': result,
                'time': 300  # 5 دقیقه
            }
        
        return result
