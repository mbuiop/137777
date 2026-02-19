from flask import request, jsonify
from app import app, requires_auth, knowledge_base, file_history, chat_history, learn_from_text, learn_from_file
from werkzeug.utils import secure_filename
import os

@app.route('/admin')
@requires_auth
def admin():
    total_knowledge = len(knowledge_base)
    total_usage = sum(d['usage'] for d in knowledge_base.values())
    total_files = len(file_history)
    total_chats = len(chat_history)
    
    knowledge_list = ''
    for i, (q, data) in enumerate(list(knowledge_base.items())[:10]):
        knowledge_list += f'''
        <tr>
            <td>{i+1}</td>
            <td>{q[:40]}...</td>
            <td>{data['answer'][:40]}...</td>
            <td>{data['usage']}</td>
        </tr>
        '''
    
    file_list = ''
    for f in file_history[-10:]:
        file_list += f'<tr><td>{f["filename"]}</td><td>{f["extracted"]}</td><td>{f["time"]}</td></tr>'
    
    chat_list = ''
    for c in chat_history[-10:]:
        chat_list += f'<tr><td>{c["question"][:30]}...</td><td>{c["answer"][:30]}...</td><td>{c["time"]}</td></tr>'
    
    return f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>پنل مدیریت</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif;}}
            body{{background:linear-gradient(135deg,#1a237e,#0d47a1);padding:20px;}}
            .container{{max-width:1200px;margin:0 auto;background:white;border-radius:30px;padding:30px;}}
            h1{{color:#1a237e;margin-bottom:30px;}}
            .stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:30px;}}
            .stat-card{{background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;padding:20px;border-radius:15px;text-align:center;}}
            .stat-number{{font-size:32px;font-weight:bold;}}
            .section{{background:#f8fafc;padding:25px;border-radius:15px;margin-bottom:30px;}}
            h2{{color:#1a237e;margin-bottom:20px;}}
            input,textarea{{width:100%;padding:12px;margin:10px 0;border:2px solid #e2e8f0;border-radius:10px;}}
            button{{padding:12px 30px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;border:none;border-radius:10px;cursor:pointer;}}
            .file-upload{{border:3px dashed #1a237e;padding:30px;text-align:center;border-radius:15px;cursor:pointer;margin:20px 0;}}
            table{{width:100%;border-collapse:collapse;margin-top:20px;}}
            th{{background:#1a237e;color:white;padding:12px;}}
            td{{border:1px solid #ddd;padding:10px;}}
            .tabs{{display:flex;gap:10px;margin-bottom:20px;}}
            .tab{{padding:10px 20px;background:#e2e8f0;border-radius:10px;cursor:pointer;}}
            .tab.active{{background:#1a237e;color:white;}}
            .tab-content{{display:none;}}
            .tab-content.active{{display:block;}}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚙️ پنل مدیریت</h1>
            
            <div class="stats-grid">
                <div class="stat-card"><div class="stat-number">{total_knowledge}</div><div>دانش‌ها</div></div>
                <div class="stat-card"><div class="stat-number">{total_usage}</div><div>استفاده</div></div>
                <div class="stat-card"><div class="stat-number">{total_files}</div><div>فایل‌ها</div></div>
                <div class="stat-card"><div class="stat-number">{total_chats}</div><div>چت‌ها</div></div>
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
                    <input type="text" id="question" placeholder="سوال">
                    <textarea id="answer" placeholder="جواب" rows="3"></textarea>
                    <button onclick="manualLearn()">✅ یاد بده</button>
                    <div id="manualMsg" style="margin-top:10px;"></div>
                </div>
            </div>
            
            <div id="upload" class="tab-content">
                <div class="section">
                    <h2>📁 آپلود فایل</h2>
                    <div class="file-upload" onclick="document.getElementById('file').click()">
                        📤 کلیک کنید یا فایل را رها کنید<br>
                        <small>txt, pdf, docx, csv, json</small>
                    </div>
                    <input type="file" id="file" style="display:none" onchange="uploadFile()">
                    <div id="uploadMsg" style="margin-top:10px;"></div>
                </div>
            </div>
            
            <div id="knowledge" class="tab-content">
                <div class="section">
                    <h2>📖 دانش‌ها</h2>
                    <table><tr><th>#</th><th>سوال</th><th>جواب</th><th>استفاده</th></tr>
                    {knowledge_list if knowledge_list else '<tr><td colspan="4">خالی</td></tr>'}
                    </table>
                </div>
            </div>
            
            <div id="chats" class="tab-content">
                <div class="section">
                    <h2>💬 آخرین چت‌ها</h2>
                    <table><tr><th>سوال</th><th>پاسخ</th><th>زمان</th></tr>
                    {chat_list if chat_list else '<tr><td colspan="3">خالی</td></tr>'}
                    </table>
                </div>
            </div>
            
            <div style="margin-top:20px;text-align:center;">
                <a href="/chat" style="color:#1a237e;">🔙 بازگشت به چت</a> | 
                <a href="/logout" style="color:#1a237e;" onclick="logout()">🚪 خروج</a>
            </div>
        </div>
        
        <script>
            function showTab(tabName) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
                document.getElementById(tabName).classList.add('active');
                event.target.classList.add('active');
            }}
            
            async function manualLearn() {{
                let q = document.getElementById('question').value;
                let a = document.getElementById('answer').value;
                if(!q || !a) {{ alert('سوال و جواب را وارد کنید'); return; }}
                
                let auth = sessionStorage.getItem('auth');
                let headers = {{'Content-Type': 'application/json'}};
                if(auth) headers['Authorization'] = 'Basic ' + auth;
                
                let response = await fetch('/admin/learn', {{
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({{question: q, answer: a}})
                }});
                
                let data = await response.json();
                document.getElementById('manualMsg').innerHTML = data.message;
                if(data.success) setTimeout(() => location.reload(), 1000);
            }}
            
            async function uploadFile() {{
                let file = document.getElementById('file').files[0];
                if(!file) return;
                
                let formData = new FormData();
                formData.append('file', file);
                
                let auth = sessionStorage.getItem('auth');
                let headers = {{}};
                if(auth) headers['Authorization'] = 'Basic ' + auth;
                
                let response = await fetch('/admin/upload', {{
                    method: 'POST',
                    headers: headers,
                    body: formData
                }});
                
                let data = await response.json();
                document.getElementById('uploadMsg').innerHTML = data.message;
                if(data.success) setTimeout(() => location.reload(), 1000);
            }}
            
            function logout() {{
                sessionStorage.removeItem('auth');
                window.location.href = '/login';
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/admin/learn', methods=['POST'])
@requires_auth
def admin_learn():
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    
    if question and answer:
        learn_from_text(question, answer)
        return jsonify({'success': True, 'message': '✅ یاد گرفتم!'})
    return jsonify({'success': False, 'message': '❌ خطا'})

@app.route('/admin/upload', methods=['POST'])
@requires_auth
def admin_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '❌ فایلی انتخاب نشده'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '❌ فایل خالی است'})
    
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    
    from app import ALLOWED_EXTENSIONS
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'message': '❌ فرمت مجاز نیست'})
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    extracted = learn_from_file(filepath, filename)
    
    return jsonify({'success': True, 'message': f'✅ {extracted} مورد یادگیری شد'})
