from m1_models import Knowledge

class MyAI:
    def __init__(self):
        print("🤖 هوش مصنوعی آماده شد")
    
    def think(self, question):
        know = Knowledge.query.filter_by(question=question).first()
        if know:
            return know.answer
        return "نمی‌دونم. به من یاد بده"
    
    def learn(self, question, answer):
        know = Knowledge(question=question, answer=answer)
        db.session.add(know)
        db.session.commit()
        return "یاد گرفتم!"
