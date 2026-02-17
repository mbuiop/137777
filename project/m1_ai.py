from m1_models import Knowledge
from m1_app import db

class MyAI:
    def __init__(self):
        print("🤖 هوش مصنوعی آماده شد")
    
    def think(self, question):
        question = question.lower().strip()
        all_know = Knowledge.query.all()
        
        best_answer = "نمی‌دونم. به من یاد بده"
        best_score = 0
        
        for k in all_know:
            q = k.question.lower()
            if question in q or q in question:
                score = len(set(question.split()) & set(q.split()))
                if score > best_score:
                    best_score = score
                    best_answer = k.answer
                    k.usage += 1
                    db.session.commit()
        
        return best_answer
    
    def learn(self, question, answer, category='general'):
        know = Knowledge(question=question, answer=answer, category=category)
        db.session.add(know)
        db.session.commit()
        return "یاد گرفتم!"
    
    def get_all_knowledge(self):
        return Knowledge.query.order_by(Knowledge.usage.desc()).all()
