from m1_app import app, db
from m1_models import Knowledge
from m1_ai import MyAI
from flask import request, jsonify, render_template

ai = MyAI()

@app.route('/')
def home():
    return 'به ربات هوش مصنوعی خوش آمدید'

@app.route('/chat')
def chat():
    return '''
    <html>
        <head>
            <title>چت با هوش مصنوعی</title>
            <style>
                body { font-family: Tahoma; text-align: center; padding: 50px; }
                .chat-box { max-width: 500px; margin: auto; }
                input { width: 70%; padding: 10px; }
                button { padding: 10px 20px; background: blue; color: white; border: none; }
                #answer { margin-top: 20px; padding: 20px; background: #f0f0f0; }
            </style>
        </head>
        <body>
            <div class="chat-box">
                <h2>🤖 هوش مصنوعی من</h2>
                <p>بهت یاد دادم جواب بده</p>
                <input id="q" placeholder="سوالت رو بنویس">
                <button onclick="ask()">بپرس</button>
                <div id="answer"></div>
            </div>
            
            <script>
            function ask() {
                let q = document.getElementById('q').value
                fetch('/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q})
                })
                .then(r => r.json())
                .then(d => document.getElementById('answer').innerHTML = d.answer)
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
