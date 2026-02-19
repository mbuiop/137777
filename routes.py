from flask import request, jsonify, redirect, render_template_string
from app import app, requires_auth, chat_history
import hashlib

# ==================== صفحه چت پیشرفته ====================
@app.route('/chat')
def chat():
    return '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
        <title>هوش مصنوعی پیشرفته</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
            body{height:100vh;display:flex;background:linear-gradient(135deg,#1a237e,#0d47a1);}
            .chat{width:100%;height:100%;display:flex;flex-direction:column;background:white;position:relative;}
            
            .header{
                padding:15px 20px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                display:flex;
                justify-content:space-between;
                align-items:center;
                box-shadow:0 4px 10px rgba(0,0,0,0.1);
            }
            .header h2{
                display:flex;
                align-items:center;
                gap:10px;
                font-size:20px;
            }
            .header h2 span{
                background:rgba(255,255,255,0.2);
                padding:5px 10px;
                border-radius:20px;
                font-size:12px;
            }
            .menu-btn{
                background:rgba(255,255,255,0.2);
                border:none;
                color:white;
                padding:10px 20px;
                border-radius:30px;
                cursor:pointer;
                font-size:16px;
                transition:all 0.3s;
                display:flex;
                align-items:center;
                gap:5px;
            }
            .menu-btn:hover{
                background:rgba(255,255,255,0.3);
                transform:scale(1.05);
            }
            
            .menu-dropdown{
                position:absolute;
                top:80px;
                left:20px;
                background:white;
                border-radius:15px;
                box-shadow:0 10px 40px rgba(0,0,0,0.2);
                display:none;
                z-index:1000;
                min-width:200px;
                overflow:hidden;
                animation: slideDown 0.3s ease;
            }
            @keyframes slideDown{
                from{opacity:0;transform:translateY(-10px);}
                to{opacity:1;transform:translateY(0);}
            }
            .menu-dropdown.show{display:block;}
            .menu-item{
                padding:15px 20px;
                color:#333;
                text-decoration:none;
                display:flex;
                align-items:center;
                gap:10px;
                border-bottom:1px solid #eee;
                transition:all 0.3s;
            }
            .menu-item:last-child{border-bottom:none;}
            .menu-item:hover{
                background:#f5f5f5;
                padding-right:25px;
            }
            .menu-item i{font-size:18px;}
            
            .messages{
                flex:1;
                overflow-y:auto;
                padding:20px;
                background:#f5f7fa;
                scroll-behavior:smooth;
            }
            .message{
                margin:15px 0;
                display:flex;
                animation: fadeIn 0.3s ease;
            }
            @keyframes fadeIn{
                from{opacity:0;transform:translateY(10px);}
                to{opacity:1;transform:translateY(0);}
            }
            .message.user{justify-content:flex-end;}
            .message.bot{justify-content:flex-start;}
            
            .message-content{
                max-width:70%;
                padding:12px 18px;
                border-radius:20px;
                word-wrap:break-word;
                position:relative;
            }
            .user .message-content{
                background:#1a237e;
                color:white;
                border-bottom-right-radius:5px;
                box-shadow:0 2px 10px rgba(26,35,126,0.2);
            }
            .bot .message-content{
                background:white;
                color:#333;
                border-bottom-left-radius:5px;
                box-shadow:0 2px 10px rgba(0,0,0,0.1);
            }
            
            .typing-indicator{
                display:flex;
                gap:5px;
                padding:10px 15px;
                background:white;
                border-radius:20px;
                box-shadow:0 2px 10px rgba(0,0,0,0.1);
                margin:10px 0;
            }
            .typing-dot{
                width:8px;
                height:8px;
                background:#1a237e;
                border-radius:50%;
                animation: typing 1.4s infinite;
            }
            .typing-dot:nth-child(2){animation-delay:0.2s;}
            .typing-dot:nth-child(3){animation-delay:0.4s;}
            @keyframes typing{
                0%,60%,100%{transform:translateY(0);opacity:0.6;}
                30%{transform:translateY(-10px);opacity:1;}
            }
            
            .time{
                font-size:11px;
                opacity:0.7;
                margin-top:5px;
                text-align:left;
            }
            
            .input-area{
                padding:20px;
                background:white;
                border-top:1px solid #eee;
            }
            .input-wrapper{
                display:flex;
                gap:10px;
                align-items:center;
                background:#f5f7fa;
                border-radius:30px;
                padding:5px;
            }
            .input-wrapper input{
                flex:1;
                padding:15px;
                border:none;
                background:transparent;
                font-size:16px;
                outline:none;
            }
            .input-wrapper button{
                padding:12px 25px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                border:none;
                border-radius:30px;
                font-size:16px;
                cursor:pointer;
                transition:all 0.3s;
                display:flex;
                align-items:center;
                gap:5px;
            }
            .input-wrapper button:hover:not(:disabled){
                transform:scale(1.05);
                box-shadow:0 5px 15px rgba(26,35,126,0.3);
            }
            .input-wrapper button:disabled{
                opacity:0.5;
                cursor:not-allowed;
            }
            
            .suggestion-chips{
                display:flex;
                gap:10px;
                margin-bottom:10px;
                flex-wrap:wrap;
            }
            .chip{
                padding:8px 15px;
                background:#f0f2f5;
                border-radius:20px;
                font-size:14px;
                cursor:pointer;
                transition:all 0.3s;
                border:1px solid #e0e0e0;
            }
            .chip:hover{
                background:#1a237e;
                color:white;
                border-color:#1a237e;
            }
            
            .dark-mode .chat{background:#1a1a1a;}
            .dark-mode .messages{background:#2d2d2d;}
            .dark-mode .message.bot .message-content{
                background:#333;
                color:#fff;
            }
            .dark-mode .input-area{
                background:#1a1a1a;
                border-top-color:#333;
            }
            .dark-mode .input-wrapper{
                background:#333;
            }
            .dark-mode .input-wrapper input{
                color:#fff;
            }
            .dark-mode .chip{
                background:#333;
                color:#fff;
                border-color:#444;
            }
            
            @media (max-width:768px){
                .message-content{max-width:85%;}
                .header h2 span{display:none;}
            }
        </style>
    </head>
    <body>
        <div class="chat">
            <div class="header">
                <h2>
                    🤖 هوش مصنوعی پیشرفته
                    <span>v2.0</span>
                </h2>
                <button class="menu-btn" onclick="toggleMenu()">
                    ☰ منو
                </button>
            </div>
            
            <div class="menu-dropdown" id="menu">
                <a href="#" class="menu-item" onclick="toggleDarkMode()">
                    <i>🌙</i> حالت شب
                </a>
                <a href="/login" class="menu-item">
                    <i>⚙️</i> پنل مدیریت
                </a>
                <a href="#" class="menu-item" onclick="clearChat()">
                    <i>🗑️</i> پاک کردن چت
                </a>
                <a href="#" class="menu-item" onclick="exportChat()">
                    <i>📥</i> خروجی چت
                </a>
            </div>
            
            <div class="messages" id="messages">
                <div class="message bot">
                    <div class="message-content">
                        👋 سلام! من یک هوش مصنوعی هستم. می‌توانم:
                        <br><br>
                        • به سوالات عمومی پاسخ دهم
                        • قیمت‌های لحظه‌ای (طلا، دلار، سکه) را پیدا کنم
                        • از فایل‌های شما یاد بگیرم
                        <br><br>
                        <small>💰 مثال: "قیمت طلا امروز چنده؟"</small>
                        <div class="time">الان</div>
                    </div>
                </div>
            </div>
            
            <div class="input-area">
                <div class="suggestion-chips" id="suggestions">
                    <span class="chip" onclick="useSuggestion('قیمت طلا امروز چنده؟')">💰 قیمت طلا</span>
                    <span class="chip" onclick="useSuggestion('دلار چند شد؟')">💵 قیمت دلار</span>
                    <span class="chip" onclick="useSuggestion('سکه امامی چند؟')">🪙 سکه امامی</span>
                    <span class="chip" onclick="useSuggestion('هوش مصنوعی چیست؟')">🤖 تعریف AI</span>
                </div>
                
                <div class="input-wrapper">
                    <input type="text" id="question" placeholder="سوال خود را بنویسید..." autofocus>
                    <button onclick="sendMessage()" id="sendBtn">
                        <span>ارسال</span>
                        <span>📤</span>
                    </button>
                </div>
            </div>
        </div>

        <script>
            let isTyping = false;
            let darkMode = localStorage.getItem('darkMode') === 'true';
            
            if(darkMode) document.body.classList.add('dark-mode');
            
            function toggleMenu() {
                document.getElementById('menu').classList.toggle('show');
            }
            
            function toggleDarkMode() {
                darkMode = !darkMode;
                localStorage.setItem('darkMode', darkMode);
                document.body.classList.toggle('dark-mode');
                toggleMenu();
            }
            
            function clearChat() {
                if(confirm('آیا می‌خواهید تاریخچه چت را پاک کنید؟')) {
                    document.getElementById('messages').innerHTML = `
                        <div class="message bot">
                            <div class="message-content">
                                👋 تاریخچه پاک شد. دوباره سلام!
                                <div class="time">الان</div>
                            </div>
                        </div>
                    `;
                }
                toggleMenu();
            }
            
            function exportChat() {
                let messages = document.getElementById('messages').innerText;
                let blob = new Blob([messages], {type: 'text/plain'});
                let url = URL.createObjectURL(blob);
                let a = document.createElement('a');
                a.href = url;
                a.download = 'chat_history_' + new Date().toISOString().slice(0,10) + '.txt';
                a.click();
                toggleMenu();
            }
            
            function useSuggestion(text) {
                document.getElementById('question').value = text;
                sendMessage();
            }
            
            async function sendMessage() {
                let q = document.getElementById('question').value.trim();
                if (!q || isTyping) return;
                
                document.getElementById('menu').classList.remove('show');
                
                let messages = document.getElementById('messages');
                let time = new Date().toLocaleTimeString('fa-IR');
                
                messages.innerHTML += `
                    <div class="message user">
                        <div class="message-content">
                            ${escapeHtml(q)}
                            <div class="time">${time}</div>
                        </div>
                    </div>
                `;
                
                document.getElementById('question').value = '';
                document.getElementById('sendBtn').disabled = true;
                messages.scrollTop = messages.scrollHeight;
                
                isTyping = true;
                messages.innerHTML += `
                    <div class="message bot" id="typingIndicator">
                        <div class="typing-indicator">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    </div>
                `;
                messages.scrollTop = messages.scrollHeight;
                
                try {
                    let response = await fetch('/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: q})
                    });
                    
                    let data = await response.json();
                    
                    document.getElementById('typingIndicator')?.remove();
                    
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content">
                                ${escapeHtml(data.answer).replace(/\\n/g, '<br>')}
                                <div class="time">${time}</div>
                            </div>
                        </div>
                    `;
                    
                } catch(error) {
                    document.getElementById('typingIndicator')?.remove();
                    messages.innerHTML += `
                        <div class="message bot">
                            <div class="message-content" style="background:#fed7d7;color:#742a2a;">
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
            
            function escapeHtml(unsafe) {
                return unsafe
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }
            
            document.getElementById('question').addEventListener('keypress', function(e) {
                if(e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            
            setInterval(() => {
                let messages = document.getElementById('messages').innerHTML;
                localStorage.setItem('chatHistory', messages);
            }, 10000);
            
            let savedChat = localStorage.getItem('chatHistory');
            if(savedChat) {
                document.getElementById('messages').innerHTML = savedChat;
            }
            
            document.addEventListener('click', function(event) {
                let menu = document.getElementById('menu');
                let menuBtn = document.querySelector('.menu-btn');
                if(!menu.contains(event.target) && !menuBtn.contains(event.target)) {
                    menu.classList.remove('show');
                }
            });
        </script>
    </body>
    </html>
    '''

# ==================== صفحه ورود ====================
@app.route('/login')
def login_page():
    return '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ورود به پنل مدیریت</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box;font-family:system-ui, -apple-system, sans-serif;}
            body{
                min-height:100vh;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                display:flex;
                align-items:center;
                justify-content:center;
                padding:20px;
            }
            .login-container{
                background:white;
                border-radius:30px;
                padding:40px;
                width:100%;
                max-width:400px;
                box-shadow:0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.5s ease;
            }
            @keyframes slideUp{
                from{opacity:0;transform:translateY(30px);}
                to{opacity:1;transform:translateY(0);}
            }
            .logo{
                text-align:center;
                margin-bottom:30px;
            }
            .logo h1{
                color:#1a237e;
                font-size:28px;
                margin-top:10px;
            }
            .logo .icon{
                font-size:64px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                width:100px;
                height:100px;
                line-height:100px;
                border-radius:50%;
                margin:0 auto 20px;
                box-shadow:0 10px 20px rgba(26,35,126,0.3);
            }
            .form-group{
                margin-bottom:20px;
            }
            label{
                display:block;
                margin-bottom:8px;
                color:#4a5568;
                font-weight:500;
            }
            input{
                width:100%;
                padding:15px;
                border:2px solid #e2e8f0;
                border-radius:15px;
                font-size:16px;
                transition:all 0.3s;
            }
            input:focus{
                border-color:#1a237e;
                outline:none;
                box-shadow:0 0 0 3px rgba(26,35,126,0.1);
            }
            button{
                width:100%;
                padding:15px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                border:none;
                border-radius:15px;
                font-size:18px;
                font-weight:bold;
                cursor:pointer;
                transition:all 0.3s;
                margin-top:10px;
            }
            button:hover{
                transform:translateY(-2px);
                box-shadow:0 10px 20px rgba(26,35,126,0.3);
            }
            .error-message{
                background:#fed7d7;
                color:#742a2a;
                padding:12px;
                border-radius:10px;
                margin-top:15px;
                display:none;
                text-align:center;
            }
            .back-link{
                text-align:center;
                margin-top:20px;
            }
            .back-link a{
                color:#718096;
                text-decoration:none;
                font-size:14px;
                transition:color 0.3s;
            }
            .back-link a:hover{
                color:#1a237e;
            }
            .input-icon{
                position:relative;
            }
            .input-icon i{
                position:absolute;
                right:15px;
                top:50%;
                transform:translateY(-50%);
                color:#a0aec0;
            }
            .input-icon input{
                padding-right:45px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <div class="icon">🔐</div>
                <h1>ورود به پنل مدیریت</h1>
            </div>
            
            <div class="form-group">
                <label>نام کاربری</label>
                <div class="input-icon">
                    <i>👤</i>
                    <input type="text" id="username" placeholder="admin" autofocus>
                </div>
            </div>
            
            <div class="form-group">
                <label>رمز عبور</label>
                <div class="input-icon">
                    <i>🔑</i>
                    <input type="password" id="password" placeholder="••••••••">
                </div>
            </div>
            
            <button onclick="login()">ورود به پنل</button>
            
            <div id="errorMsg" class="error-message"></div>
            
            <div class="back-link">
                <a href="/chat">🔙 بازگشت به صفحه چت</a>
            </div>
        </div>
        
        <script>
            async function login() {
                let username = document.getElementById('username').value;
                let password = document.getElementById('password').value;
                
                if(!username || !password) {
                    showError('لطفاً نام کاربری و رمز عبور را وارد کنید');
                    return;
                }
                
                let headers = new Headers();
                headers.set('Authorization', 'Basic ' + btoa(username + ':' + password));
                
                try {
                    let response = await fetch('/admin', {
                        method: 'GET',
                        headers: headers
                    });
                    
                    if(response.status === 200) {
                        localStorage.setItem('auth', btoa(username + ':' + password));
                        window.location.href = '/admin';
                    } else {
                        showError('نام کاربری یا رمز عبور اشتباه است');
                    }
                } catch(error) {
                    showError('خطا در ارتباط با سرور');
                }
            }
            
            function showError(message) {
                let errorEl = document.getElementById('errorMsg');
                errorEl.style.display = 'block';
                errorEl.innerHTML = '❌ ' + message;
            }
            
            document.getElementById('password').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') login();
            });
        </script>
    </body>
    </html>
    '''

@app.route('/ask', methods=['POST'])
def ask():
    from app import smart_search
    data = request.json
    question = data.get('question', '')
    answer = smart_search(question)
    return jsonify({'answer': answer})
