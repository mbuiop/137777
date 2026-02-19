import redis
import json
import hashlib
from datetime import timedelta

class RedisCache:
    def __init__(self, host='localhost', port=6379, db=0):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_keepalive=True,
            max_connections=100,
            socket_timeout=5
        )
    
    def get_answer(self, question):
        """گرفتن پاسخ از کش"""
        key = hashlib.md5(question.encode()).hexdigest()
        cached = self.client.get(f"answer:{key}")
        if cached:
            return json.loads(cached)
        return None
    
    def set_answer(self, question, answer, ttl=3600):
        """ذخیره پاسخ در کش"""
        key = hashlib.md5(question.encode()).hexdigest()
        self.client.setex(f"answer:{key}", ttl, json.dumps(answer))
    
    def get_stats(self):
        """آمار کش"""
        info = self.client.info()
        return {
            'connected': self.client.ping(),
            'used_memory': info.get('used_memory_human', '0'),
            'total_connections': info.get('total_connections_received', 0)
        }
    
    def clear_cache(self):
        """پاک کردن کش"""
        self.client.flushdb()
