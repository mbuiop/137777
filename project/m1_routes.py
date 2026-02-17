from m1_app import app, db
from m1_models import Knowledge, User
from m1_ai import ai
from flask import request, jsonify, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import json

# ========== تنظیمات آپلود ==========
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== صفحه اصلی ==========
@app.route('/')
def home():
    return redirect('/chat')

# ========== صفحه چت ==========
@app.route('/chat')
def chat():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>هوش مصنوعی پیشرفته</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                height: 100vh;
                overflow: hidden;
            }
            .chat-container {
                display: flex;
                flex-direction: column;
                height: 100vh;
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                box-shadow: 0 0 50px rgba(0,0,0,0.3);
            }
            .chat-header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 20px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .chat-header h1 {
                font-size: 24px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .chat-header h1 span {
                background: #ffd700;
                color: #1e3c72;
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 14px;
            }
            .menu-btn {
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                font-size: 24px;
                padding: 10px 15px;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .chat-main {
                flex: 1;
                display: flex;
                background: #f0f2f5;
            }
            .sidebar {
                width: 300px;
                background: white;
                border-right: 1px solid #e0e0e0;
                display: none;
                flex-direction: column;
            }
            .sidebar.show {
                display: flex;
            }
            .sidebar-header {
                padding: 20px;
                background: #f8f9fa;
                border-bottom: 1px solid #e0e0e0;
            }
            .sidebar-menu {
                flex: 1;
                padding: 10px;
            }
            .menu-item {
                padding: 15px;
                margin: 5px 0;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .menu-item:hover {
                background: #f0f2f5;
            }
            .chat-area {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            .messages {
                flex: 1;
                padding: 30px;
                overflow-y: auto;
            }
            .message {
                margin-bottom: 25px;
                display: flex;
                animation: fadeIn 0.3s;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .message.user { justify-content: flex-end; }
            .message.bot { justify-content: flex-start; }
            .message-content {
                max-width: 70%;
                padding: 15px 20px;
                border-radius: 20px;
                word-wrap: break-word;
                line-height: 1.5;
            }
            .user .message-content {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border-bottom-right-radius: 5px;
            }
            .bot .message-content {
                background: white;
                color: #333;
                border-bottom-left-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .input-area {
                background: white;
                border-top: 2px solid #f0f2f5;
                padding: 25px 30px;
            }
            .input-wrapper {
                display: flex;
                gap: 15px;
                align-items: center;
                background: #f8f9fa;
                border-radius: 50px;
                padding: 5px 5px 5px 25px;
                border: 2px solid transparent;
            }
            .input-wrapper:focus-within {
                border-color: #1e3c72;
                background: white;
            }
            .input-wrapper input {
                flex: 1;
                padding: 15px 0;
                border: none;
                background: transparent;
                font-size: 16px;
                outline: none;
            }
            .input-wrapper button {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 50px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }
            .typing-indicator {
                display: none;
                padding: 15px 20px;
                background: white;
                border-radius: 20px;
                margin-bottom: 20px;
            }
            .typing-indicator.show { display: inline-block; }
            .typing-dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #999;
                margin: 0 2px;
                animation: typing 1.4s infinite;
            }
            .typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-dot:nth-child(3) { animation-delay: 0.4s; }
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
            .admin-link { position: fixed; bottom: 20px; right: 20px; }
            .admin-link a {
                background: #1e3c72;
                color: white;
                padding: 12px 24px;
                border-radius: 50px;
                text-decoration: none;
                box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h1>🤖 هوش مصنوعی پیشرفته <span>نسخه 3.0</span></h1>
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
            </div>
            
            <div class="chat-main">
                <div class="sidebar" id="sidebar">
                    <div class="sidebar-header">
                        <h3>منوی اصلی</h3>
                    </div>
                    <div class="sidebar-menu">
                        <div class="menu-item" onclick="window.location='/chat'">💬 صفحه چت</div>
                        <div class="menu-item" onclick="window.location='/admin_panel'">⚙️ پنل مدیریت</div>
                        <div class="menu-item" onclick="window.location='/stats'">📊 آمار</div>
                    </div>
                </div>
                
                <div class="chat-area">
                    <div class="messages" id="messages">
                        <div class="message bot">
                            <div class="message-content">
                                سلام! من یک هوش مصنوعی قوی هستم. هر سوالی داری بپرس
                                <div class="message-time">الان</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="typing-indicator" id="typing">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                    
                    <div class="input-area">
                        <div class="input-wrapper">
                            <input type="text" id="question" 
                                   placeholder="سوال خود را بنویسید ..."
                                   onkeypress="if(event.key=='Enter') send()">
                            <button onclick="send()">ارسال</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="admin-link">
            <a href="/admin_panel">⚙️ پنل مدیریت</a>
        </div>
        
        <script>
            let sidebar = document.getElementById('sidebar');
            let messages = document.getElementById('messages');
            let typing = document.getElementById('typing');
            let question = document.getElementById('question');
            
            function toggleMenu() {
                sidebar.classList.toggle('show');
            }
            
            function send() {
                let q = question.value.trim();
                if (!q) return;
                
                messages.innerHTML += `
                    <div class="message user">
                        <div class="message-content">
                            ${q}
                            <div class="message-time">الان</div>
                        </div>
                    </div>
                `;
                
                question.value = '';
                messages.scrollTop = messages.scrollHeight;
                typing.classList.add('show');
                
                fetch('/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q})
                })
                .then(r => r.json())
                .then(d => {
                    typing.classList.remove('show');
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content">
                                ${d.answer}
                                <div class="message-time">الان</div>
                            </div>
                        </div>
                    `;
                    messages.scrollTop = messages.scrollHeight;
                });
            }
            
            question.focus();
        </script>
    </body>
    </html>
    '''

# ========== پنل مدیریت (فقط برای مدیر) ==========
@app.route('/admin_panel')
def admin_panel():
    # اینجا بعداً لاگین اضافه میکنیم
    knows = Knowledge.query.order_by(Knowledge.usage.desc()).all()
    
    table = ''
    for k in knows:
        table += f'''
        <tr>
            <td>{k.question[:50]}...</td>
            <td>{k.answer[:50]}...</td>
            <td>{k.category}</td>
            <td>{k.usage}</td>
            <td>{k.confidence}</td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>پنل مدیریت</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .admin-container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .admin-header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .admin-content {{ padding: 30px; }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
            }}
            .stat-number {{ font-size: 36px; font-weight: bold; color: #1e3c72; }}
            .section {{
                background: #f8f9fa;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
            }}
            .section h2 {{ margin-bottom: 20px; color: #1e3c72; }}
            input, textarea, select {{
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 16px;
            }}
            button {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 10px;
                font-size: 16px;
                cursor: pointer;
                margin: 5px;
            }}
            .file-upload {{
                border: 3px dashed #1e3c72;
                padding: 40px;
                text-align: center;
                border-radius: 15px;
                margin: 20px 0;
                cursor: pointer;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background: #1e3c72;
                color: white;
                padding: 12px;
            }}
            td {{
                border: 1px solid #ddd;
                padding: 10px;
            }}
            .back-link {{ text-align: center; margin-top: 20px; }}
            .back-link a {{ color: #666; text-decoration: none; }}
            .progress {{ display: none; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="admin-container">
            <div class="admin-header">
                <h1>⚙️ پنل مدیریت هوش مصنوعی</h1>
                <p>فقط برای مدیر - آموزش و مدیریت دانش</p>
            </div>
            
            <div class="admin-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{len(knows)}</div>
                        <div>تعداد دانش</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{sum(k.usage for k in knows)}</div>
                        <div>کل استفاده</div>
                    </div>
                </div>
                
                <!-- بخش آموزش دستی -->
                <div class="section">
                    <h2>📚 آموزش دستی</h2>
                    <input type="text" id="q" placeholder="سوال">
                    <textarea id="a" placeholder="جواب" rows="3"></textarea>
                    <select id="cat">
                        <option value="general">عمومی</option>
                        <option value="tech">فنی</option>
                        <option value="science">علمی</option>
                    </select>
                    <button onclick="teach()">یاد بده</button>
                    <p id="msg" style="color:green; margin-top:10px;"></p>
                </div>
                
                <!-- بخش آپلود فایل -->
                <div class="section">
                    <h2>📁 آپلود فایل برای آموزش</h2>
                    <div class="file-upload" onclick="document.getElementById('file').click()">
                        📤 کلیک کنید یا فایل را اینجا رها کنید
                        <br>
                        <small>فرمت‌های مجاز: txt, pdf, docx, csv</small>
                    </div>
                    <input type="file" id="file" style="display:none" onchange="uploadFile()">
                    <div id="progress" class="progress">در حال پردازش...</div>
                </div>
                
                <!-- لیست دانش -->
                <h2>📖 لیست دانش</h2>
                <table>
                    <tr>
                        <th>سوال</th>
                        <th>جواب</th>
                        <th>دسته</th>
                        <th>استفاده</th>
                        <th>دقت</th>
                    </tr>
                    {table}
                </table>
                
                <div class="back-link">
                    <a href="/chat">🔙 برگشت به صفحه چت</a>
                </div>
            </div>
        </div>
        
        <script>
        function teach() {{
            fetch('/learn', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    question: document.getElementById('q').value,
                    answer: document.getElementById('a').value,
                    category: document.getElementById('cat').value
                }})
            }})
            .then(r => r.json())
            .then(d => {{
                document.getElementById('msg').innerHTML = d.message;
                document.getElementById('q').value = '';
                document.getElementById('a').value = '';
                setTimeout(() => location.reload(), 1000);
            }});
        }}
        
        function uploadFile() {{
            let file = document.getElementById('file').files[0];
            let formData = new FormData();
            formData.append('file', file);
            
            document.getElementById('progress').style.display = 'block';
            
            fetch('/upload', {{
                method: 'POST',
                body: formData
            }})
            .then(r => r.json())
            .then(d => {{
                document.getElementById('progress').innerHTML = d.message;
                setTimeout(() => location.reload(), 2000);
            }});
        }}
        </script>
    </body>
    </html>
    '''

# ========== آپلود فایل ==========
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'فایلی انتخاب نشده'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'فایل خالی است'})
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # پردازش با هوش مصنوعی
    result = ai.process_file(filepath, filename)
    
    if 'error' in result:
        return jsonify({'message': f'خطا: {result["error"]}'})
    
    return jsonify({'message': f'✅ {result["extracted"]} مورد یادگیری استخراج شد'})

# ========== API چت ==========
@app.route('/ask', methods=['POST'])
def ask():
    q = request.json['question']
    answer = ai.think(q)
    return jsonify({'answer': answer})

# ========== یادگیری ==========
@app.route('/learn', methods=['POST'])
def learn():
    q = request.json['question']
    a = request.json['answer']
    cat = request.json.get('category', 'general')
    result = ai.learn(q, a, cat)
    return jsonify({'message': result})

# ========== آمار ==========
@app.route('/stats')
def stats():
    knows = Knowledge.query.all()
    stats = ai.get_stats()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>آمار</title>
        <style>
            body {{ font-family: Tahoma; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }}
            .stats-box {{ background: white; padding: 40px; border-radius: 20px; width: 500px; }}
            h2 {{ text-align: center; color: #1e3c72; }}
            .stat-item {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }}
        </style>
    </head>
    <body>
        <div class="stats-box">
            <h2>📊 آمار هوش مصنوعی</h2>
            <div class="stat-item">تعداد کل دانش: {stats["total"]}</div>
            <div class="stat-item">میانگین استفاده: {stats["avg_usage"]:.1f}</div>
            <div class="stat-item">دسته‌بندی‌ها: {", ".join(stats["categories"])}</div>
            <div style="text-align:center; margin-top:20px;">
                <a href="/chat" style="color:#1e3c72;">🔙 برگشت</a>
            </div>
        </div>
    </body>
    </html>
    '''
