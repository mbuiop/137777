from m1_app import app, db
from m1_models import Knowledge
from m1_ai import MyAI
from flask import request, jsonify, render_template

ai = MyAI()

@app.route('/')
def home():
    return 'به ربات هوش مصنوعی خوش آمدید'

# ========== صفحه چت اصلی ==========
@app.route('/chat')
def chat():
    return '''
    <html>
        <head>
            <title>چت با هوش مصنوعی</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: Tahoma; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; justify-content: center; align-items: center; }
                .chat-container { width: 800px; height: 600px; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column; overflow: hidden; }
                .chat-header { background: #4a90e2; color: white; padding: 20px; text-align: center; }
                .chat-header h2 { margin: 0; font-size: 24px; }
                .chat-header p { margin: 5px 0 0; font-size: 14px; opacity: 0.9; }
                .chat-messages { flex: 1; padding: 20px; overflow-y: auto; background: #f5f7fb; }
                .message { margin-bottom: 20px; display: flex; }
                .message.user { justify-content: flex-end; }
                .message.bot { justify-content: flex-start; }
                .message-content { max-width: 70%; padding: 12px 18px; border-radius: 20px; position: relative; word-wrap: break-word; }
                .user .message-content { background: #4a90e2; color: white; border-bottom-right-radius: 5px; }
                .bot .message-content { background: white; color: #333; border-bottom-left-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .message-time { font-size: 11px; opacity: 0.7; margin-top: 5px; text-align: right; }
                .chat-input { display: flex; padding: 20px; background: white; border-top: 1px solid #eee; }
                .chat-input input { flex: 1; padding: 12px; border: 2px solid #e0e0e0; border-radius: 25px; font-size: 16px; outline: none; transition: border-color 0.3s; }
                .chat-input input:focus { border-color: #4a90e2; }
                .chat-input button { padding: 12px 25px; margin-left: 10px; background: #4a90e2; color: white; border: none; border-radius: 25px; font-size: 16px; cursor: pointer; transition: background 0.3s; }
                .chat-input button:hover { background: #357abd; }
                .typing { display: none; padding: 10px 20px; background: white; border-radius: 20px; margin-bottom: 10px; }
                .typing.show { display: inline-block; }
                .typing-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #999; margin: 0 2px; animation: typing 1.4s infinite; }
                .typing-dot:nth-child(2) { animation-delay: 0.2s; }
                .typing-dot:nth-child(3) { animation-delay: 0.4s; }
                @keyframes typing { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-10px); } }
                .admin-link { text-align: center; margin-top: 10px; font-size: 12px; }
                .admin-link a { color: #999; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="chat-container">
                <div class="chat-header">
                    <h2>🤖 هوش مصنوعی پیشرفته</h2>
                    <p>هر سوالی داری بپرس</p>
                </div>
                
                <div class="chat-messages" id="messages">
                    <div class="message bot">
                        <div class="message-content">
                            سلام! به ربات هوش مصنوعی خوش اومدی
                            <div class="message-time">الان</div>
                        </div>
                    </div>
                </div>
                
                <div class="typing" id="typing">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
                
                <div class="chat-input">
                    <input type="text" id="question" placeholder="سوال خود را بنویسید..." onkeypress="if(event.key=='Enter') send()">
                    <button onclick="send()">ارسال</button>
                </div>
                
                <div class="admin-link">
                    <a href="/learn_page">📚 آموزش به ربات</a> | 
                    <a href="/admin">⚙️ پنل مدیریت</a>
                </div>
            </div>

            <script>
                let messages = document.getElementById('messages');
                let typing = document.getElementById('typing');
                let question = document.getElementById('question');
                
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

# ========== صفحه یاد دادن ==========
@app.route('/learn_page')
def learn_page():
    return '''
    <html>
        <head>
            <title>یاد دادن به ربات</title>
            <style>
                body { font-family: Tahoma; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
                .container { background: white; padding: 40px; border-radius: 20px; width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
                h2 { text-align: center; color: #333; margin-bottom: 30px; }
                input, textarea { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #e0e0e0; border-radius: 10px; font-family: Tahoma; }
                input:focus, textarea:focus { outline: none; border-color: #4a90e2; }
                button { width: 100%; padding: 14px; background: #4a90e2; color: white; border: none; border-radius: 10px; font-size: 16px; cursor: pointer; }
                button:hover { background: #357abd; }
                #msg { text-align: center; margin-top: 10px; color: green; }
                .back-link { text-align: center; margin-top: 20px; }
                .back-link a { color: #666; text-decoration: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📚 آموزش به ربات</h2>
                <input id="q" placeholder="سوال را بنویس">
                <textarea id="a" placeholder="جواب را بنویس" rows="4"></textarea>
                <button onclick="teach()">یاد بده</button>
                <p id="msg"></p>
                <div class="back-link">
                    <a href="/chat">🔙 برگشت به چت</a>
                </div>
            </div>
            
            <script>
            function teach() {
                let q = document.getElementById('q').value
                let a = document.getElementById('a').value
                
                fetch('/learn', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q, answer: a})
                })
                .then(r => r.json())
                .then(d => {
                    document.getElementById('msg').innerHTML = d.message
                    document.getElementById('q').value = ''
                    document.getElementById('a').value = ''
                })
            }
            </script>
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
    result = ai.learn(q, a)
    return jsonify({'message': result})

@app.route('/admin')
def admin():
    return 'پنل مدیریت'
