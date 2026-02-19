from flask import request, jsonify, redirect
from app import app, chat_history, smart_search

@app.route('/')
def home():
    return redirect('/chat')

@app.route('/chat')
def chat():
    return '''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>هوش مصنوعی پیشرفته</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif;}
            body{height:100vh;display:flex;background:linear-gradient(135deg,#1a237e,#0d47a1);}
            .chat{width:100%;height:100%;display:flex;flex-direction:column;background:white;}
            
            .header{
                padding:15px 20px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                display:flex;
                justify-content:space-between;
                align-items:center;
            }
            .header h2{display:flex;align-items:center;gap:10px;font-size:20px;}
            .menu-btn{
                background:rgba(255,255,255,0.2);
                border:none;
                color:white;
                padding:10px 20px;
                border-radius:30px;
                cursor:pointer;
                font-size:16px;
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
            }
            .menu-dropdown.show{display:block;}
            .menu-item{
                padding:15px 20px;
                color:#333;
                text-decoration:none;
                display:block;
                border-bottom:1px solid #eee;
            }
            .menu-item:hover{background:#f5f5f5;}
            
            .messages{
                flex:1;
                overflow-y:auto;
                padding:20px;
                background:#f5f7fa;
            }
            .message{margin:15px 0;display:flex;}
            .message.user{justify-content:flex-end;}
            .message.bot{justify-content:flex-start;}
            
            .message-content{
                max-width:70%;
                padding:12px 18px;
                border-radius:20px;
                word-wrap:break-word;
            }
            .user .message-content{
                background:#1a237e;
                color:white;
                border-bottom-right-radius:5px;
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
                0%,60%,100%{transform:translateY(0);}
                30%{transform:translateY(-10px);}
            }
            
            .time{font-size:11px;opacity:0.7;margin-top:5px;}
            
            .input-area{
                padding:20px;
                background:white;
                border-top:1px solid #eee;
            }
            .input-wrapper{
                display:flex;
                gap:10px;
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
                cursor:pointer;
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
                border:1px solid #e0e0e0;
            }
            .chip:hover{
                background:#1a237e;
                color:white;
            }
            
            .dark-mode .chat{background:#1a1a1a;}
            .dark-mode .messages{background:#2d2d2d;}
            .dark-mode .bot .message-content{
                background:#333;
                color:#fff;
            }
            .dark-mode .input-area{
                background:#1a1a1a;
                border-top-color:#333;
            }
        </style>
    </head>
    <body>
        <div class="chat">
            <div class="header">
                <h2>🤖 هوش مصنوعی پیشرفته <span>v2.0</span></h2>
                <button class="menu-btn" onclick="toggleMenu()">☰ منو</button>
            </div>
            
            <div class="menu-dropdown" id="menu">
                <a href="#" class="menu-item" onclick="toggleDarkMode()">🌙 حالت شب</a>
                <a href="/login" class="menu-item">⚙️ پنل مدیریت</a>
                <a href="#" class="menu-item" onclick="clearChat()">🗑️ پاک کردن چت</a>
            </div>
            
            <div class="messages" id="messages">
                <div class="message bot">
                    <div class="message-content">
                        👋 سلام! هر سوالی دارید بپرسید:<br><br>
                        💰 قیمت طلا، دلار، سکه<br>
                        📚 اطلاعات عمومی<br>
                        🔍 جستجو در گوگل
                        <div class="time">الان</div>
                    </div>
                </div>
            </div>
            
            <div class="input-area">
                <div class="suggestion-chips">
                    <span class="chip" onclick="useSuggestion('قیمت طلا امروز چنده؟')">💰 قیمت طلا</span>
                    <span class="chip" onclick="useSuggestion('دلار چند شد؟')">💵 قیمت دلار</span>
                    <span class="chip" onclick="useSuggestion('سکه امامی چند؟')">🪙 سکه امامی</span>
                    <span class="chip" onclick="useSuggestion('هوش مصنوعی چیست؟')">🤖 تعریف AI</span>
                </div>
                
                <div class="input-wrapper">
                    <input type="text" id="question" placeholder="سوال خود را بنویسید..." autofocus>
                    <button onclick="sendMessage()">ارسال</button>
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
                if(confirm('پاک شود؟')) {
                    document.getElementById('messages').innerHTML = `
                        <div class="message bot">
                            <div class="message-content">👋 چت پاک شد<div class="time">الان</div></div>
                        </div>
                    `;
                }
                toggleMenu();
            }
            
            function useSuggestion(text) {
                document.getElementById('question').value = text;
                sendMessage();
            }
            
            async function sendMessage() {
                let q = document.getElementById('question').value.trim();
                if (!q || isTyping) return;
                
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
                                ❌ خطا در ارتباط
                                <div class="time">${time}</div>
                            </div>
                        </div>
                    `;
                }
                
                isTyping = false;
                messages.scrollTop = messages.scrollHeight;
            }
            
            function escapeHtml(unsafe) {
                return unsafe.replace(/[&<>"]/g, function(m) {
                    if(m=='&') return '&amp;'; if(m=='<') return '&lt;'; 
                    if(m=='>') return '&gt;'; if(m=='"') return '&quot;';
                    return m;
                });
            }
            
            document.getElementById('question').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    '''

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
            *{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif;}
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
            }
            .logo{text-align:center;margin-bottom:30px;}
            .logo .icon{
                font-size:64px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                width:100px;
                height:100px;
                line-height:100px;
                border-radius:50%;
                margin:0 auto 20px;
            }
            .form-group{margin-bottom:20px;}
            label{display:block;margin-bottom:8px;color:#4a5568;}
            input{
                width:100%;
                padding:15px;
                border:2px solid #e2e8f0;
                border-radius:15px;
                font-size:16px;
            }
            input:focus{border-color:#1a237e;outline:none;}
            button{
                width:100%;
                padding:15px;
                background:linear-gradient(135deg,#1a237e,#0d47a1);
                color:white;
                border:none;
                border-radius:15px;
                font-size:18px;
                cursor:pointer;
            }
            button:hover{transform:translateY(-2px);}
            .error-message{
                background:#fed7d7;
                color:#742a2a;
                padding:12px;
                border-radius:10px;
                margin-top:15px;
                display:none;
            }
            .info-text{
                text-align:center;
                margin-top:20px;
                color:#718096;
            }
            .info-text a{color:#1a237e;text-decoration:none;}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <div class="icon">🔐</div>
                <h2>ورود به پنل مدیریت</h2>
            </div>
            
            <div class="form-group">
                <label>نام کاربری</label>
                <input type="text" id="username" placeholder="admin" autofocus>
            </div>
            
            <div class="form-group">
                <label>رمز عبور</label>
                <input type="password" id="password" placeholder="••••••••">
            </div>
            
            <button onclick="login()">ورود</button>
            
            <div id="errorMsg" class="error-message"></div>
            
            <div class="info-text">
                <p>رمز پیش‌فرض: <strong>admin / admin123</strong></p>
                <p><a href="/chat">🔙 بازگشت</a></p>
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
                    let response = await fetch('/admin', {method: 'GET', headers: headers});
                    
                    if(response.status === 200) {
                        sessionStorage.setItem('auth', btoa(username + ':' + password));
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
    data = request.json
    question = data.get('question', '')
    answer = smart_search(question)
    return jsonify({'answer': answer})
