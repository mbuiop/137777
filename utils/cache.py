import time
import threading
from collections import OrderedDict

class Cache:
    """سیستم کش پیشرفته با قابلیت انقضا"""
    
    def __init__(self, max_size=10000, default_timeout=300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_timeout = default_timeout
        self.lock = threading.Lock()
    
    def get(self, key):
        """دریافت از کش"""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if expiry > time.time():
                    # انتقال به انتها (最近使用)
                    self.cache.move_to_end(key)
                    return value
                else:
                    # حذف منقضی شده
                    del self.cache[key]
        return None
    
    def set(self, key, value, timeout=None):
        """ذخیره در کش"""
        if timeout is None:
            timeout = self.default_timeout
        
        expiry = time.time() + timeout
        
        with self.lock:
            # اگر کلید وجود دارد، حذف کن
            if key in self.cache:
                del self.cache[key]
            
            # اگر کش پر شده، قدیمی‌ترین را حذف کن
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
            self.cache[key] = (value, expiry)
    
    def delete(self, key):
        """حذف از کش"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
        return False
    
    def clear(self):
        """پاک کردن کل کش"""
        with self.lock:
            self.cache.clear()
    
    def size(self):
        """اندازه کش"""
        return len(self.cache)
    
    def cleanup(self):
        """پاک کردن موارد منقضی شده"""
        now = time.time()
        with self.lock:
            expired = [k for k, (_, exp) in self.cache.items() if exp <= now]
            for k in expired:
                del self.cache[k]
            return len(expired)
