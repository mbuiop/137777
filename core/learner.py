import re
import os
from .text_processor import TextProcessor
from concurrent.futures import ThreadPoolExecutor
import PyPDF2
import docx

class FileLearner:
    """یادگیرنده از فایل‌ها"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.answer_marker = '!این'
    
    def extract_answers(self, filepath, filename):
        """استخراج جواب‌ها از فایل"""
        ext = filename.rsplit('.', 1)[1].lower()
        
        # خواندن فایل
        if ext == 'txt':
            text = self._read_txt(filepath)
        elif ext == 'pdf':
            text = self._read_pdf(filepath)
        elif ext == 'docx':
            text = self._read_docx(filepath)
        elif ext == 'csv':
            text = self._read_csv(filepath)
        else:
            return []
        
        # استخراج جواب‌ها
        return self._parse_text(text)
    
    def _read_txt(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _read_pdf(self, filepath):
        text = ""
        with open(filepath, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _read_docx(self, filepath):
        doc = docx.Document(filepath)
        return "\n".join([p.text for p in doc.paragraphs])
    
    def _read_csv(self, filepath):
        text = ""
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                text += line.replace(',', ' ') + "\n"
        return text
    
    def _parse_text(self, text):
        """پارس کردن متن و استخراج جواب‌ها"""
        answers = []
        lines = text.split('\n')
        
        current_question = None
        current_answer = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # اگر نشانگر جواب بود
            if self.answer_marker in line:
                # اگر جواب قبلی داریم، ذخیره کن
                if current_question and current_answer:
                    answers.append({
                        'question': current_question,
                        'answer': '\n'.join(current_answer),
                        'line': i
                    })
                
                # شروع جواب جدید
                parts = line.split(self.answer_marker, 1)
                if len(parts) > 1:
                    current_question = parts[0].strip()
                    answer_text = parts[1].strip()
                    if answer_text:
                        current_answer = [answer_text]
                    else:
                        current_answer = []
                else:
                    current_question = "مطلب آموزشی"
                    current_answer = []
            
            # اگر در حال خواندن جواب هستیم
            elif current_answer is not None:
                # اگر خط بعدی هم نشانگر داشت، ادامه
                if i + 1 < len(lines) and self.answer_marker in lines[i + 1]:
                    # جواب تمام شد
                    if current_question and current_answer:
                        answers.append({
                            'question': current_question,
                            'answer': '\n'.join(current_answer),
                            'line': i
                        })
                    current_question = None
                    current_answer = []
                else:
                    current_answer.append(line)
        
        # جواب آخر
        if current_question and current_answer:
            answers.append({
                'question': current_question,
                'answer': '\n'.join(current_answer),
                'line': len(lines)
            })
        
        # ایجاد سوال برای جواب‌های بدون سوال
        processed = []
        for i, ans in enumerate(answers):
            if not ans['question'] or ans['question'] == "مطلب آموزشی":
                # از محتوای جواب سوال می‌سازیم
                first_line = ans['answer'].split('\n')[0][:50]
                ans['question'] = f"در مورد {first_line} توضیح بده"
            processed.append(ans)
        
        return processed
