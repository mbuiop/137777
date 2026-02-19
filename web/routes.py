from flask import Blueprint, render_template_string, session, redirect
from models.database import Knowledge, ChatHistory
from config import Config
import json

web_bp = Blueprint('web', __name__)

# صفحه چت
@web_bp.route('/')
def home():
    return redirect('/chat')

@web_bp.route('/chat')
def chat():
    return render_template_string(CHAT_TEMPLATE)

@web_bp.route('/login')
def login():
    return render_template_string(LOGIN_TEMPLATE)

@web_bp.route('/admin')
def admin_panel():
    if 'user_id' not in session:
        return redirect('/login')
    
    # آمار
    stats = {
        'knowledge_count': Knowledge.query.filter_by(is_active=True).count(),
        'file_count': 0,  # TODO
        'chat_count': ChatHistory.query.count()
    }
    
    # دانش‌ها
    knowledge = Knowledge.query.filter_by(is_active=True)\
        .order_by(Knowledge.usage_count.desc())\
        .limit(20).all()
    
    # چت‌ها
    chats = ChatHistory.query.order_by(ChatHistory.created_at.desc()).limit(20).all()
    
    return render_template_string(ADMIN_TEMPLATE,
        stats=stats,
        knowledge=[k.to_dict() for k in knowledge],
        chats=[c.to_dict() for c in chats]
    )

@web_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

# ==================== HTML Templates ====================

CHAT_TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>هوش مصنوعی پیشرفته</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Vazir', system-ui, sans-serif;
        }
        
        body {
            height: 100vh;
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .chat-container {
            width: 90%;
            max-width: 1200px;
            height: 90vh;
            background: white;
            border-radius: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.5rem;
        }
        
        .brain-status {
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        
        .menu-btn {
            background: none;
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 20px;
            display: flex;
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message.bot {
            justify-content: flex-start;
        }
        
        .message-content {
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 20px;
            position: relative;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .user .message-content {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            border-bottom-right-radius: 5px;
        }
        
        .bot .message-content {
            background: white;
            color: #333;
            border-bottom-left-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .time {
            font-size: 0.7rem;
            opacity: 0.7;
            margin-top: 5px;
        }
        
        .typing {
            display: flex;
            gap: 5px;
            padding: 15px 20px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }
        
        .suggestions {
            display: flex;
            gap: 10px;
            padding: 15px 30px;
            background: white;
            border-top: 1px solid #eee;
            flex-wrap: wrap;
        }
        
        .suggestion-chip {
            padding: 8px 15px;
            background: #f0f2f5;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.3s;
        }
        
        .suggestion-chip:hover {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
        }
        
        .input-area {
            padding: 20px 30px;
            background: white;
            border-top: 1px solid #eee;
        }
        
        .input-wrapper {
            display: flex;
            gap: 10px;
        }
        
        #question {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 15px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s;
        }
        
        #question:focus {
            border-color: #1a2980;
        }
        
        #sendBtn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            border: none;
            border-radius: 15px;
            cursor: pointer;
            font-size: 1rem;
            transition: transform 0.3s;
        }
        
        #sendBtn:hover {
            transform: scale(1.05);
        }
        
        #sendBtn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .confidence-badge {
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.7rem;
            margin-left: 10px;
        }
        
        @media (max-width: 768px) {
            .message-content { max-width: 85%; }
            .suggestions { display: none; }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>
                🧠 هوش مصنوعی پیشرفته
                <span class="brain-status">v3.0</span>
            </h1>
            <button class="menu-btn" onclick="window.location.href='/login'">⚙️</button>
        </div>
        
        <div class="messages" id="messages">
            <div class="message bot">
                <div class="message-content">
                    👋 سلام! من هوش مصنوعی هستم.<br><br>
                    💡 هر سوالی دارید بپرسید. من از فایل‌هایی که به من یاد داده‌اید پاسخ می‌دهم.<br><br>
                    <small>مثال: "قیمت طلا چنده؟" یا "هوش مصنوعی چیست؟"</small>
                </div>
            </div>
        </div>
        
        <div class="suggestions">
            <span class="suggestion-chip" onclick="ask('سلام')">👋 سلام</span>
            <span class="suggestion-chip" onclick="ask('قیمت طلا چنده؟')">💰 قیمت طلا</span>
            <span class="suggestion-chip" onclick="ask('دلار چند شد؟')">💵 قیمت دلار</span>
            <span class="suggestion-chip" onclick="ask('هوش مصنوعی چیست؟')">🤖 تعریف هوش</span>
        </div>
        
        <div class="input-area">
            <div class="input-wrapper">
                <input type="text" id="question" placeholder="سوال خود را بپرسید..." autofocus>
                <button onclick="sendMessage()" id="sendBtn">ارسال</button>
            </div>
        </div>
    </div>
    
    <script>
        let isTyping = false;
        
        function ask(text) {
            document.getElementById('question').value = text;
            sendMessage();
        }
        
        async function sendMessage() {
            const question = document.getElementById('question').value.trim();
            if (!question || isTyping) return;
            
            const messages = document.getElementById('messages');
            const time = new Date().toLocaleTimeString('fa-IR');
            
            // نمایش سوال کاربر
            messages.innerHTML += `
                <div class="message user">
                    <div class="message-content">
                        ${escapeHtml(question)}
                        <div class="time">${time}</div>
                    </div>
                </div>
            `;
            
            document.getElementById('question').value = '';
            document.getElementById('sendBtn').disabled = true;
            messages.scrollTop = messages.scrollHeight;
            
            // نمایش تایپ
            isTyping = true;
            messages.innerHTML += `
                <div class="message bot" id="typing">
                    <div class="typing">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            messages.scrollTop = messages.scrollHeight;
            
            try {
                const response = await fetch('/api/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question})
                });
                
                const data = await response.json();
                
                document.getElementById('typing')?.remove();
                
                if (data.success) {
                    let answerHtml = escapeHtml(data.answer);
                    
                    // نمایش اطمینان
                    if (data.confidence > 0) {
                        const confidencePercent = Math.round(data.confidence * 100);
                        answerHtml += `<br><br><small>🎯 اطمینان: ${confidencePercent}%</small>`;
                    }
                    
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content">
                                ${answerHtml.replace(/\\n/g, '<br>')}
                                <div class="time">${time}</div>
                            </div>
                        </div>
                    `;
                } else {
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content" style="background: #fee; color: #c00;">
                                ❌ ${escapeHtml(data.answer)}
                                <div class="time">${time}</div>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('typing')?.remove();
                messages.innerHTML += `
                    <div class="message bot">
                        <div class="message-content" style="background: #fee; color: #c00;">
                            ❌ خطا در ارتباط با سرور
                            <div class="time">${time}</div>
                        </div>
                    </div>
                `;
            }
            
            isTyping = false;
            document.getElementById('sendBtn').disabled = false;
            messages.scrollTop = messages.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        document.getElementById('question').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ورود به پنل مدیریت</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: system-ui, sans-serif;
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 400px;
        }
        
        h2 {
            color: #1a2980;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
        }
        
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        
        input:focus {
            border-color: #1a2980;
            outline: none;
        }
        
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            cursor: pointer;
        }
        
        button:hover {
            opacity: 0.9;
        }
        
        .error {
            color: #c00;
            margin-top: 10px;
            text-align: center;
            display: none;
        }
        
        .back {
            text-align: center;
            margin-top: 20px;
        }
        
        .back a {
            color: #666;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 ورود به پنل مدیریت</h2>
        
        <div class="form-group">
            <label>نام کاربری</label>
            <input type="text" id="username" value="admin" autofocus>
        </div>
        
        <div class="form-group">
            <label>رمز عبور</label>
            <input type="password" id="password" value="admin123">
        </div>
        
        <button onclick="login()">ورود</button>
        
        <div class="error" id="errorMsg"></div>
        
        <div class="back">
            <a href="/chat">🔙 بازگشت به چت</a>
        </div>
    </div>
    
    <script>
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, password})
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.location.href = '/admin';
            } else {
                document.getElementById('errorMsg').style.display = 'block';
                document.getElementById('errorMsg').textContent = '❌ ' + (data.message || 'خطا در ورود');
            }
        }
        
        document.getElementById('password').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') login();
        });
    </script>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>پنل مدیریت هوش مصنوعی</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: system-ui, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        h1 {
            color: #1a2980;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .tab {
            padding: 12px 25px;
            background: #f0f2f5;
            border-radius: 10px;
            cursor: pointer;
        }
        
        .tab.active {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .section {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
        }
        
        h2 {
            color: #1a2980;
            margin-bottom: 20px;
        }
        
        input, textarea {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 1rem;
        }
        
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
        }
        
        .file-upload {
            border: 3px dashed #1a2980;
            padding: 40px;
            text-align: center;
            border-radius: 15px;
            cursor: pointer;
            margin: 20px 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            padding: 12px;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        
        .message {
            padding: 12px;
            border-radius: 10px;
            margin-top: 15px;
            display: none;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        
        .logout {
            text-align: center;
            margin-top: 30px;
        }
        
        .logout a {
            color: #1a2980;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ پنل مدیریت هوش مصنوعی</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.knowledge_count }}</div>
                <div>تعداد دانش‌ها</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.file_count }}</div>
                <div>فایل‌های آپلود</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.chat_count }}</div>
                <div>تعداد چت‌ها</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('learn')">📚 آموزش</div>
            <div class="tab" onclick="showTab('upload')">📁 آپلود</div>
            <div class="tab" onclick="showTab('knowledge')">📖 دانش‌ها</div>
            <div class="tab" onclick="showTab('chats')">💬 چت‌ها</div>
        </div>
        
        <div id="learn" class="tab-content active">
            <div class="section">
                <h2>📚 آموزش دستی</h2>
                <input type="text" id="question" placeholder="سوال را وارد کنید">
                <textarea id="answer" placeholder="جواب را وارد کنید"></textarea>
                <button onclick="manualLearn()">✅ ذخیره</button>
                <div id="learnMessage" class="message"></div>
            </div>
        </div>
        
        <div id="upload" class="tab-content">
            <div class="section">
                <h2>📁 آپلود فایل</h2>
                <div class="file-upload" onclick="document.getElementById('file').click()">
                    📤 کلیک کنید یا فایل را رها کنید<br>
                    <small>فرمت‌های مجاز: txt, pdf, docx, csv</small>
                </div>
                <input type="file" id="file" style="display:none" onchange="uploadFile()">
                <div id="uploadMessage" class="message"></div>
            </div>
        </div>
        
        <div id="knowledge" class="tab-content">
            <div class="section">
                <h2>📖 دانش‌ها</h2>
                <table>
                    <tr>
                        <th>#</th>
                        <th>سوال</th>
                        <th>جواب</th>
                        <th>استفاده</th>
                    </tr>
                    {% for k in knowledge %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ k.question }}</td>
                        <td>{{ k.answer }}</td>
                        <td>{{ k.usage }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        
        <div id="chats" class="tab-content">
            <div class="section">
                <h2>💬 چت‌ها</h2>
                <table>
                    <tr>
                        <th>سوال</th>
                        <th>پاسخ</th>
                        <th>زمان</th>
                    </tr>
                    {% for c in chats %}
                    <tr>
                        <td>{{ c.question }}</td>
                        <td>{{ c.answer }}</td>
                        <td>{{ c.time }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
        
        <div class="logout">
            <a href="/logout">🚪 خروج</a>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }
        
        async function manualLearn() {
            const question = document.getElementById('question').value;
            const answer = document.getElementById('answer').value;
            
            if (!question || !answer) {
                showMessage('learnMessage', 'لطفاً سوال و جواب را وارد کنید', 'error');
                return;
            }
            
            const response = await fetch('/api/admin/learn', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question, answer})
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage('learnMessage', '✅ ' + data.message, 'success');
                document.getElementById('question').value = '';
                document.getElementById('answer').value = '';
                setTimeout(() => location.reload(), 1000);
            } else {
                showMessage('learnMessage', '❌ ' + data.message, 'error');
            }
        }
        
        async function uploadFile() {
            const file = document.getElementById('file').files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/admin/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                showMessage('uploadMessage', '✅ ' + data.message, 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showMessage('uploadMessage', '❌ ' + data.message, 'error');
            }
        }
        
        function showMessage(elementId, message, type) {
            const el = document.getElementById(elementId);
            el.className = 'message ' + type;
            el.textContent = message;
        }
    </script>
</body>
</html>
'''
