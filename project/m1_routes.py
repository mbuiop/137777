from m1_app import app, db
from m1_models import Knowledge
from m1_ai import MyAI
from flask import request, jsonify, render_template

ai = MyAI()

@app.route('/')
def home():
    return 'به ربات هوش مصنوعی خوش آمدید'

# ========== صفحه چت ==========
@app.route('/chat')
def chat():
    return '''
    <html>
        <head>
            <title>چت با هوش مصنوعی</title>
            <style>
                body { font-family: Tahoma; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; justify-content: center; align-items: center; }
                .chat-box { width: 800px; height: 600px; background: white; border-radius: 10px; display: flex; flex-direction: column; }
                .header { background: #4a90e2; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
                .messages { flex: 1; padding: 20px; overflow-y: auto; background: #f5f5f5; }
                .user { text-align: right; margin: 10px; }
                .user span { background: #4a90e2; color: white; padding: 10px; border-radius: 10px; display: inline-block; }
                .bot { text-align: left; margin: 10px; }
                .bot span { background: white; padding: 10px; border-radius: 10px; display: inline-block; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                .input-area { display: flex; padding: 20px; background: white; border-top: 1px solid #ddd; }
                input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; }
                button { padding: 10px 20px; background: #4a90e2; color: white; border: none; border-radius: 5px; cursor: pointer; }
                .admin-link { text-align: center; margin: 10px; }
                .admin-link a { color: #666; text-decoration: none; margin: 0 10px; }
            </style>
        </head>
        <body>
            <div class="chat-box">
                <div class="header">
                    <h2>🤖 هوش مصنوعی</h2>
                    <p>هر چی یاد گرفتم جواب میدم</p>
                </div>
                
                <div class="messages" id="messages">
                    <div class="bot"><span>سلام! چطور میتونم کمک کنم؟</span></div>
                </div>
                
                <div class="input-area">
                    <input type="text" id="question" placeholder="سوال خود را بنویس..." onkeypress="if(event.key=='Enter') send()">
                    <button onclick="send()">ارسال</button>
                </div>
                
                <div class="admin-link">
                    <a href="/learn_page">📚 آموزش</a> | 
                    <a href="/admin">⚙️ مدیریت</a>
                </div>
            </div>
            
            <script>
                function send() {
                    let q = document.getElementById('question').value
                    if (!q) return
                    
                    let m = document.getElementById('messages')
                    m.innerHTML += '<div class="user"><span>' + q + '</span></div>'
                    document.getElementById('question').value = ''
                    
                    fetch('/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: q})
                    })
                    .then(r => r.json())
                    .then(d => {
                        m.innerHTML += '<div class="bot"><span>' + d.answer + '</span></div>'
                        m.scrollTop = m.scrollHeight
                    })
                }
            </script>
        </body>
    </html>
    '''

# ========== صفحه آموزش ==========
@app.route('/learn_page')
def learn_page():
    return '''
    <html>
        <head>
            <title>آموزش به ربات</title>
            <style>
                body { font-family: Tahoma; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; justify-content: center; align-items: center; }
                .learn-box { background: white; padding: 40px; border-radius: 10px; width: 500px; }
                h2 { text-align: center; color: #333; }
                input, textarea { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
                button { width: 100%; padding: 10px; background: #4a90e2; color: white; border: none; border-radius: 5px; cursor: pointer; }
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
                        answer: document.getElementById('a').value
                    })
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
