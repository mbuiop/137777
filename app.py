from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from datetime import timedelta
import os

# ==================== راه‌اندازی ====================
app = Flask(__name__)
app.config.from_object('config.Config')

# ==================== دیتابیس ====================
from models.database import db
db.init_app(app)

# ==================== کش ====================
cache = Cache(app)

# ==================== محدود کننده ====================
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=app.config['REDIS_URL']
)

# ==================== ایجاد دیتابیس ====================
with app.app_context():
    db.create_all()
    
    # ایجاد کاربر ادمین
    from models.database import User
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ کاربر ادمین ایجاد شد: admin / admin123")

# ==================== API ====================
from api.chat import chat_bp
from api.admin import admin_bp
from web.routes import web_bp

app.register_blueprint(chat_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(web_bp)

# ==================== API لاگین ====================
@app.route('/api/login', methods=['POST'])
def login():
    from flask import request, jsonify, session
    from models.database import User
    
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and user.check_password(data.get('password')):
        session['user_id'] = user.id
        session.permanent = True
        app.permanent_session_lifetime = timedelta(hours=24)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'اطلاعات وارد شده صحیح نیست'}), 401

# ==================== اجرا ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
