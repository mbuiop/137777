from m1_app import app, db
from m1_models import Knowledge, User
from m1_ai import MyAI
from flask import request, jsonify, redirect
from werkzeug.security import generate_password_hash, check_password_hash

ai = MyAI()

# ========== صفحه اصلی ==========
@app.route('/')
def home():
    return redirect('/chat')

# ========== صفحه چت تمام صفحه ==========
@app.route('/chat')
def chat():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
            .menu-btn:hover {
                background: rgba(255,255,255,0.3);
                transform: scale(1.05);
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
                padding: 12px 15px;
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
            .menu-item i {
                width: 24px;
                color: #1e3c72;
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
            .message-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 5px;
                text-align: right;
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
                transition: all 0.3s;
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
                transition: all 0.3s;
            }
            .input-wrapper button:hover {
                transform: scale(1.05);
                box-shadow: 0 5px 20px rgba(30,60,114,0.4);
            }
            .typing-indicator {
                display: none;
                padding: 15px 20px;
                background: white;
                border-radius: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .typing-indicator.show {
                display: inline-block;
            }
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
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h1>
                    🤖 هوش مصنوعی پیشرفته
                    <span>نسخه 2.0</span>
                </h1>
                <button class="menu-btn" onclick="toggleMenu()">☰</button>
            </div>
            
            <div class="chat-main">
                <div class="sidebar" id="sidebar">
                    <div class="sidebar-header">
                        <h3>منوی اصلی</h3>
                    </div>
                    <div class="sidebar-menu">
                        <div class="menu-item" onclick="window.location='/chat'">
                            <i>💬</i> صفحه چت
                        </div>
                        <div class="menu-item" onclick="window.location='/admin_panel'">
                            <i>⚙️</i> پنل مدیریت
                        </div>
                        <div class="menu-item" onclick="window.location='/learn_page'">
                            <i>📚</i> آموزش به ربات
                        </div>
                        <div class="menu-item" onclick="window.location='/stats'">
                            <i>📊</i> آمار
                        </div>
                    </div>
                </div>
                
                <div class="chat-area">
                    <div class="messages" id="messages">
                        <div class="message bot">
                            <div class="message-content">
                                سلام! به هوش مصنوعی پیشرفته خوش آمدید
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
                
                // Add user message
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

# ========== پنل مدیریت ==========
@app.route('/admin_panel')
def admin_panel():
    knows = ai.get_all_knowledge()
    
    table = ''
    for k in knows:
        table += f'''
        <tr>
            <td>{k.question[:50]}</td>
            <td>{k.answer[:50]}</td>
            <td>{k.category}</td>
            <td>{k.usage}</td>
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
                max-width: 1200px;
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
            .admin-header h1 {{ font-size: 32px; margin-bottom: 10px; }}
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
            .train-section {{
                background: #f8f9fa;
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
            }}
            .train-section h2 {{ margin-bottom: 20px; color: #1e3c72; }}
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
                transition: all 0.3s;
            }}
            button:hover {{ transform: scale(1.05); }}
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
            .back-link {{
                text-align: center;
                margin-top: 20px;
            }}
            .back-link a {{
                color: #666;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="admin-container">
            <div class="admin-header">
                <h1>⚙️ پنل مدیریت هوش مصنوعی</h1>
                <p>مدیریت دانش و آموزش ربات</p>
            </div>
            
            <div class="admin-content">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{len(knows)}</div>
                        <div>تعداد دانش</div>
                    </div>
                </div>
                
                <div class="train-section">
                    <h2>📚 آموزش به ربات</h2>
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
                
                <h2>📖 لیست دانش</h2>
                <table>
                    <tr>
                        <th>سوال</th>
                        <th>جواب</th>
                        <th>دسته</th>
                        <th>استفاده</th>
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
        </script>
    </body>
    </html>
    '''

# ========== صفحه آموزش ==========
@app.route('/learn_page')
def learn_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>آموزش به ربات</title>
        <style>
            body { font-family: Tahoma; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); height: 100vh; display: flex; justify-content: center; align-items: center; }
            .learn-box { background: white; padding: 40px; border-radius: 20px; width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            h2 { text-align: center; color: #1e3c72; margin-bottom: 30px; }
            input, textarea, select { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #ddd; border-radius: 10px; }
            button { width: 100%; padding: 14px; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; border: none; border-radius: 10px; cursor: pointer; }
            #msg { text-align: center; color: green; margin-top: 10px; }
            .back { text-align: center; margin-top: 20px; }
            .back a { color: #666; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="learn-box">
            <h2>📚 آموزش به ربات</h2>
            <input id="q" placeholder="سوال">
            <textarea id="a" placeholder="جواب" rows="4"></textarea>
            <select id="cat">
                <option value="general">عمومی</option>
                <option value="tech">فنی</option>
                <option value="science">علمی</option>
            </select>
            <button onclick="teach()">یاد بده</button>
            <p id="msg"></p>
            <div class="back"><a href="/chat">🔙 برگشت</a></div>
        </div>
        
        <script>
        function teach() {
            fetch('/learn', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    question: document.getElementById('q').value,
                    answer: document.getElementById('a').value,
                    category: document.getElementById('cat').value
                })
            })
            .then(r => r.json())
            .then(d => {
                document.getElementById('msg').innerHTML = d.message;
                document.getElementById('q').value = '';
                document.getElementById('a').value = '';
            });
        }
        </script>
    </body>
    </html>
    '''

@app.route('/stats')
def stats():
    knows = ai.get_all_knowledge()
    total = len(knows)
    most_used = knows[0] if knows else None
    
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
            .back {{ text-align: center; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="stats-box">
            <h2>📊 آمار</h2>
            <div class="stat-item">تعداد کل دانش: {total}</div>
            <div class="stat-item">پراستفاده ترین: {most_used.question if most_used else '-'}</div>
            <div class="stat-item">دفعات استفاده: {most_used.usage if most_used else '0'}</div>
            <div class="back"><a href="/chat">🔙 برگشت</a></div>
        </div>
    </body>
    </html>
    '''

@app.route('/ask', methods=['POST'])
def ask():
    q = request.json['question']
    answer = ai.think(q)
    return jsonify({'answer': answer})

@app.route('/learn', methods=['POST'])
def learn():
    q = request.json['question']
    a = request.json['answer']
    cat = request.json.get('category', 'general')
    result = ai.learn(q, a, cat)
    return jsonify({'message': result})
