from m1_app import app, db
from m1_models import *
from m1_routes import *

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ دیتابیس ساخته شد")
    print("🚀 ربات اجرا شد روی http://localhost:5000")
    app.run(debug=True, port=5000)
