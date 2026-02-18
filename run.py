from app import create_app, db
from app.models import User, Knowledge, Message, Upload

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("="*60)
        print("🚀 MEGA AI SYSTEM v10.0")
        print("="*60)
        print("✅ Database ready")
        print("✅ AI Engine ready")
        print("✅ Redis cache ready")
        print("="*60)
        print("🌐 http://localhost:5000")
        print("👤 Admin: admin / admin123")
        print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
