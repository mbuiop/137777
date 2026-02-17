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
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    AI_READY = True
    print("✅ هوش مصنوعی قوی آماده شد")
except:
    AI_READY = False
    print("⚠️ هوش مصنوعی قوی نصب نیست، از حالت ساده استفاده میشه")

class AdvancedAI:
    def __init__(self):
        self.name = "هوش مصنوعی پیشرفته"
        self.version = "3.0"
        self.knowledge_base = {}
        self.cache = {}
        
        if AI_READY:
            # مدل درک متن
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.dimension = 384
            self.stop_words = set(stopwords.words('english') + stopwords.words('persian'))
            print("✅ مدل درک متن آماده شد")
    
    def analyze_text(self, text):
        """تحلیل عمیق متن با ۱۰ تکنیک مختلف"""
        if not AI_READY:
            return {"error": "AI not ready"}
        
        analysis = {}
        
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
        if hasattr(self, 'model'):
            analysis['embedding'] = self.model.encode(text).tolist()
        
        return analysis
    
    def extract_qa_from_text(self, text):
        """استخراج سوال و جواب از متن"""
        qa_pairs = []
        sentences = sent_tokenize(text)
        
        for i, sent in enumerate(sentences):
            # اگه جمله سوال بود
            if '?' in sent or '؟' in sent:
                # جواب میتونه جمله بعدی باشه
                if i + 1 < len(sentences):
                    answer = sentences[i + 1]
                    if len(answer) > 20:  # جواب باید حداقل ۲۰ حرف باشه
                        qa_pairs.append({
                            'question': sent,
                            'answer': answer,
                            'confidence': 0.8
                        })
        
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
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text()
            
            elif file_ext == 'docx':
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            
            # تحلیل متن
            analysis = self.analyze_text(text)
            
            # استخراج سوال و جواب
            qa_pairs = self.extract_qa_from_text(text)
            
            # اضافه کردن به دانش
            for qa in qa_pairs:
                know = Knowledge(
                    question=qa['question'],
                    answer=qa['answer'],
                    category='extracted',
                    confidence=qa['confidence'],
                    source=filename
                )
                db.session.add(know)
                extracted.append(qa)
            
            db.session.commit()
            
            return {
                'extracted': len(extracted),
                'analysis': analysis,
                'file': filename
            }
            
        except Exception as e:
            print(f"خطا: {e}")
            return {'error': str(e)}
    
    def think(self, question):
        """پاسخ هوشمند به سوال"""
        question = question.strip()
        
        # چک کردن کش
        if question in self.cache:
            return self.cache[question]
        
        # گرفتن همه دانش‌ها
        all_know = Knowledge.query.all()
        
        if AI_READY and len(all_know) > 0:
            # تبدیل سوال به embedding
            q_emb = self.model.encode(question)
            
            best_match = None
            best_score = -1
            
            for k in all_know:
                # تحلیل سوال
                k_analysis = self.analyze_text(k.question)
                
                if 'embedding' in k_analysis:
                    # محاسبه شباهت
                    k_emb = np.array(k_analysis['embedding'])
                    similarity = cosine_similarity([q_emb], [k_emb])[0][0]
                    
                    if similarity > best_score and similarity > 0.5:
                        best_score = similarity
                        best_match = k
                        
                        # افزایش آمار استفاده
                        k.usage += 1
                        db.session.commit()
            
            if best_match:
                answer = f"[دقت: {best_score:.2%}]\n{best_match.answer}"
                self.cache[question] = answer
                if len(self.cache) > 100:
                    self.cache.pop(list(self.cache.keys())[0])
                return answer
        
        # حالت ساده
        for k in all_know:
            if question.lower() in k.question.lower() or k.question.lower() in question.lower():
                k.usage += 1
                db.session.commit()
                return k.answer
        
        return "نمی‌دونم. میشه بیشتر توضیح بدی یا به من یاد بدی؟"
    
    def learn(self, question, answer, category='general'):
        """یادگیری مطلب جدید"""
        know = Knowledge(
            question=question,
            answer=answer,
            category=category,
            confidence=1.0,
            source='manual'
        )
        db.session.add(know)
        db.session.commit()
        return "✅ یاد گرفتم!"
    
    def get_stats(self):
        """گرفتن آمار"""
        all_know = Knowledge.query.all()
        return {
            'total': len(all_know),
            'avg_usage': sum(k.usage for k in all_know) / max(len(all_know), 1),
            'categories': list(set(k.category for k in all_know))
        }

# ساخت نمونه از هوش مصنوعی
ai = AdvancedAI()
