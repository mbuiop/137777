from flask import request, jsonify, render_template_string
from app import app, requires_auth, knowledge_base, file_history, chat_history, learn_from_text, learn_from_file, auto_save, OnlinePriceSearcher
from werkzeug.utils import secure_filename
import os
import json
import hashlib
from datetime import datetime

@app.route('/admin')
@requires_auth
def admin():
    total_knowledge = len(knowledge_base)
    total_usage = sum(d['usage'] for d in knowledge_base.values())
    total_files = len(file_history)
    total_chats = len(chat_history)
    online_searches = len([c for c in chat_history if c.get('type') == 'online_price'])
    
    knowledge_list = ''
    for i, (q, data) in enumerate(list(knowledge_base.items())[:10]):
        confidence = data.get('confidence', 70)
        confidence_color = 'green' if confidence > 80 else 'orange' if confidence > 50 else 'red'
        knowledge_list += f'''
        <tr>
            <td>{i+1}</td>
            <td>{q[:50]}...</td>
            <td>{data['answer'][:50]}...</td>
            <td style="color:{confidence_color};">{confidence}%</td>
            <td>{data['usage']}</td>
            <td>{data.get('version', 1)}</td>
        </tr>
        '''
    
    file_list = ''
    for f in file_history[-10:]:
        file_list += f'''
        <tr>
            <td>{f['filename']}</td>
            <td>{f.get('extracted', 0)}</td>
            <td>{f.get('total_pairs', 0)}</td>
            <td>{f['time']}</td>
        </tr>
        '''
    
    chat_list = ''
    for c in chat_history[-10:]:
        chat_type = '💰' if c.get('type') == 'online_price' else '📚' if c.get('type') == 'knowledge_base' else '❓'
        chat_list += f'''
        <tr>
            <td>{chat_type}</td>
            <td>{c['question'][:40]}...</td>
            <td>{c['answer'][:40]}...</td>
            <td>{c['time']}</td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>پنل مدیریت هوش مصنوعی</title>
        <style>
            *{{margin:0;padding:0;box-sizing:border-box;font-family:system-ui, -apple-system, sans-serif;}}
            body{{background:linear-gradient(135deg,#1a237e,#0d47a1);padding:20px;min-height:100vh;}}
            .container{{max-width:1400px;margin:0 auto;background:white;border-radius:30px;padding:30px;box-shadow:0 20px 60px rgba(0,0,0,0.3);}}
            h1{{color:#1a237e;margin-bottom:30px;font-size:32px;display:flex;align-items:center;gap:10px;}}
            .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:20px;margin-bottom:30px;}}
            .stat-card{{background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;padding:20px;border-radius:20px;text-align:center;box-shadow:0 10px 20px rgba(0,0,0,0.2);}}
            .stat-number{{font-size:36px;font-weight:bold;margin-bottom:5px;}}
            .stat-label{{font-size:14px;opacity:0.9;}}
            .section{{background:#f8fafc;padding:25px;border-radius:20px;margin-bottom:30px;border:1px solid #e2e8f0;}}
            h2{{color:#1a237e;margin-bottom:20px;display:flex;align-items:center;gap:10px;font-size:24px;}}
            .form-group{{margin-bottom:15px;}}
            label{{display:block;margin-bottom:5px;color:#4a5568;font-weight:500;}}
            input,textarea,select{{width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:10px;font-size:16px;transition:all 0.3s;}}
            input:focus,textarea:focus{{border-color:#1a237e;outline:none;box-shadow:0 0 0 3px rgba(26,35,126,0.1);}}
            button{{padding:12px 30px;background:linear-gradient(135deg,#1a237e,#0d47a1);color:white;border:none;border-radius:10px;font-size:16px;cursor:pointer;transition:all 0.3s;}}
            button:hover{{transform:translateY(-2px);box-shadow:0 10px 20px rgba(0,0,0,0.2);}}
            .file-upload{{border:3px dashed #1a237e;padding:40px;text-align:center;border-radius:20px;cursor:pointer;margin:20px 0;background:#f8fafc;transition:all 0.3s;}}
            .file-upload:hover{{background:#e2e8f0;border-color:#0d47a1;}}
            .file-upload i{{font-size:48px;color:#1a237e;margin-bottom:10px;display:block;}}
            table{{width:100%;border-collapse:collapse;margin-top:20px;background:white;border-radius:10px;overflow:hidden;}}
            th{{background:#1a237e;color:white;padding:12px;font-weight:500;}}
            td{{padding:12px;border-bottom:1px solid #e2e8f0;}}
            tr:hover{{background:#f8fafc;}}
            .badge{{padding:4px 8px;border-radius:20px;font-size:12px;font-weight:bold;}}
            .badge-success{{background:#c6f6d5;color:#22543d;}}
            .badge-warning{{background:#feebc8;color:#744210;}}
            .badge-info{{background:#bee3f8;color:#2c5282;}}
            .tabs{{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;}}
            .tab{{padding:10px 20px;background:#e2e8f0;border-radius:10px;cursor:pointer;transition:all 0.3s;}}
            .tab.active{{background:#1a237e;color:white;}}
            .tab-content{{display:none;}}
            .tab-content.active{{display:block;}}
            .progress-bar{{width:100%;height:20px;background:#e2e8f0;border-radius:10px;overflow:hidden;margin:10px 0;}}
            .progress-fill{{height:100%;background:linear-gradient(90deg,#1a237e,#0d47a1);transition:width 0.3s;}}
            @media (max-width:768px){{
                .container{{padding:15px;}}
                .stats-grid{{grid-template-columns:repeat(2,1fr);}}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚙️ پنل مدیریت هوش مصنوعی پیشرفته</h1>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_knowledge}</div>
                    <div class="stat-label">تعداد دانش‌ها</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_usage}</div>
                    <div class="stat-label">کل استفاده</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_files}</div>
                    <div class="stat-label">فایل‌های آپلود</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_chats}</div>
                    <div class="stat-label">تعداد چت‌ها</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{online_searches}</div>
                    <div class="stat-label">جستجوی آنلاین</div>
                </div>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('learn')">📚 آموزش</div>
                <div class="tab" onclick="showTab('upload')">📁 آپلود فایل</div>
                <div class="tab" onclick="showTab('knowledge')">📖 دانش‌ها</div>
                <div class="tab" onclick="showTab('files')">📂 فایل‌ها</div>
                <div class="tab" onclick="showTab('chats')">💬 چت‌ها</div>
                <div class="tab" onclick="showTab('settings')">⚙️ تنظیمات</div>
            </div>
            
            <div id="learn" class="tab-content active">
                <div class="section">
                    <h2>📚 آموزش دستی</h2>
                    <div class="form-group">
                        <label>سوال:</label>
                        <input type="text" id="question" placeholder="سوال خود را وارد کنید...">
                    </div>
                    <div class="form-group">
                        <label>جواب:</label>
                        <textarea id="answer" placeholder="جواب را وارد کنید..." rows="4"></textarea>
                    </div>
                    <div class="form-group">
                        <label>اعتماد (Confidence):</label>
                        <input type="range" id="confidence" min="0" max="100" value="90" oninput="this.nextElementSibling.value = this.value">
                        <output>90%</output>
                    </div>
                    <button onclick="manualLearn()">✅ یاد بده</button>
                    <div id="manualMsg" style="margin-top:15px;padding:10px;border-radius:10px;display:none;"></div>
                </div>
            </div>
            
            <div id="upload" class="tab-content">
                <div class="section">
                    <h2>📁 آپلود فایل</h2>
                    <div class="file-upload" onclick="document.getElementById('file').click()">
                        <i>📤</i>
                        کلیک کنید یا فایل را اینجا رها کنید<br>
                        <small>فرمت‌های مجاز: txt, pdf, docx, csv, json (حداکثر 500MB)</small>
                    </div>
                    <input type="file" id="file" style="display:none" onchange="uploadFile()">
                    <div id="uploadProgress" style="margin-top:20px;display:none;">
                        <div class="progress-bar">
                            <div id="progressBar" class="progress-fill" style="width:0%;"></div>
                        </div>
                        <p id="uploadStatus" style="text-align:center;margin-top:10px;">در حال پردازش...</p>
                    </div>
                    <div id="uploadMsg" style="margin-top:15px;padding:10px;border-radius:10px;display:none;"></div>
                </div>
            </div>
            
            <div id="knowledge" class="tab-content">
                <div class="section">
                    <h2>📖 دانش‌های ذخیره شده</h2>
                    <div style="overflow-x:auto;">
                        <table>
                            <tr>
                                <th>#</th>
                                <th>سوال</th>
                                <th>جواب</th>
                                <th>اعتماد</th>
                                <th>استفاده</th>
                                <th>نسخه</th>
                            </tr>
                            {knowledge_list if knowledge_list else '<tr><td colspan="6" style="text-align:center;">هیچ دانشی ثبت نشده</td></tr>'}
                        </table>
                    </div>
                </div>
            </div>
            
            <div id="files" class="tab-content">
                <div class="section">
                    <h2>📂 آخرین فایل‌های آپلود شده</h2>
                    <div style="overflow-x:auto;">
                        <table>
                            <tr>
                                <th>نام فایل</th>
                                <th>تعداد استخراج</th>
                                <th>جفت سوال-جواب</th>
                                <th>زمان</th>
                            </tr>
                            {file_list if file_list else '<tr><td colspan="4" style="text-align:center;">هیچ فایلی آپلود نشده</td></tr>'}
                        </table>
                    </div>
                </div>
            </div>
            
            <div id="chats" class="tab-content">
                <div class="section">
                    <h2>💬 آخرین مکالمات</h2>
                    <div style="overflow-x:auto;">
                        <table>
                            <tr>
                                <th>نوع</th>
                                <th>سوال</th>
                                <th>پاسخ</th>
                                <th>زمان</th>
                            </tr>
                            {chat_list if chat_list else '<tr><td colspan="4" style="text-align:center;">هیچ مکالمه‌ای ثبت نشده</td></tr>'}
                        </table>
                    </div>
                </div>
            </div>
            
            <div id="settings" class="tab-content">
                <div class="section">
                    <h2>⚙️ تنظیمات پیشرفته</h2>
                    <div class="form-group">
                        <label>آستانه شباهت (Similarity Threshold):</label>
                        <input type="range" id="similarity" min="0.1" max="0.9" step="0.1" value="0.6" oninput="this.nextElementSibling.value = this.value">
                        <output>0.6</output>
                    </div>
                    <div class="form-group">
                        <label>مدت اعتبار کش (ثانیه):</label>
                        <input type="number" id="cache_duration" value="1800" min="60" max="3600">
                    </div>
                    <button onclick="saveSettings()">💾 ذخیره تنظیمات</button>
                    <div id="settingsMsg" style="margin-top:15px;padding:10px;border-radius:10px;display:none;"></div>
                </div>
            </div>
            
            <div style="margin-top:30px;text-align:center;">
                <a href="/chat" style="color:#1a237e;text-decoration:none;font-size:18px;">🔙 بازگشت به صفحه چت</a>
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
                let c = document.getElementById('confidence').value;
                
                if(!q || !a) {{
                    showMessage('manualMsg', '❌ لطفاً سوال و جواب را وارد کنید', 'error');
                    return;
                }}
                
                let response = await fetch('/admin/learn', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{question: q, answer: a, confidence: parseInt(c)}})
                }});
                
                let data = await response.json();
                
                if(data.success) {{
                    showMessage('manualMsg', '✅ یاد گرفتم! صفحه در حال به‌روزرسانی...', 'success');
                    document.getElementById('question').value = '';
                    document.getElementById('answer').value = '';
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    showMessage('manualMsg', '❌ خطا در یادگیری', 'error');
                }}
            }}
            
            async function uploadFile() {{
                let file = document.getElementById('file').files[0];
                if(!file) return;
                
                let formData = new FormData();
                formData.append('file', file);
                
                document.getElementById('uploadProgress').style.display = 'block';
                document.getElementById('uploadMsg').style.display = 'none';
                
                let response = await fetch('/admin/upload', {{
                    method: 'POST',
                    body: formData
                }});
                
                let data = await response.json();
                document.getElementById('uploadProgress').style.display = 'none';
                
                if(data.success) {{
                    showMessage('uploadMsg', '✅ ' + data.message, 'success');
                    setTimeout(() => location.reload(), 1500);
                }} else {{
                    showMessage('uploadMsg', '❌ ' + data.message, 'error');
                }}
            }}
            
            function showMessage(elementId, message, type) {{
                let el = document.getElementById(elementId);
                el.style.display = 'block';
                el.innerHTML = message;
                el.style.backgroundColor = type === 'success' ? '#c6f6d5' : '#fed7d7';
                el.style.color = type === 'success' ? '#22543d' : '#742a2a';
            }}
            
            async function saveSettings() {{
                let similarity = document.getElementById('similarity').value;
                let cacheDuration = document.getElementById('cache_duration').value;
                
                let response = await fetch('/admin/settings', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        similarity_threshold: parseFloat(similarity),
                        cache_duration: parseInt(cacheDuration)
                    }})
                }});
                
                let data = await response.json();
                showMessage('settingsMsg', '✅ تنظیمات ذخیره شد', 'success');
            }}
        </script>
    </body>
    </html>
    '''

@app.route('/admin/learn', methods=['POST'])
@requires_auth
def admin_learn():
    from app import learn_from_text
    data = request.json
    question = data.get('question')
    answer = data.get('answer')
    confidence = data.get('confidence', 100)
    
    if question and answer:
        learn_from_text(question, answer, confidence=confidence)
        return jsonify({'success': True, 'message': '✅ یاد گرفتم!'})
    
    return jsonify({'success': False, 'message': '❌ لطفاً سوال و جواب را وارد کنید'})

@app.route('/admin/upload', methods=['POST'])
@requires_auth
def admin_upload():
    from app import learn_from_file, app
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '❌ فایلی انتخاب نشده'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '❌ فایل خالی است'})
    
    from app import allowed_file
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    
    if not allowed_file(filename):
        return jsonify({'success': False, 'message': '❌ فرمت فایل مجاز نیست'})
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    extracted = learn_from_file(filepath, filename)
    
    return jsonify({'success': True, 'message': f'✅ {extracted} مورد یادگیری از فایل استخراج شد'})

@app.route('/admin/settings', methods=['POST'])
@requires_auth
def save_settings():
    from app import app, OnlinePriceSearcher
    data = request.json
    
    if 'similarity_threshold' in data:
        app.config['SIMILARITY_THRESHOLD'] = data['similarity_threshold']
    
    if 'cache_duration' in data:
        OnlinePriceSearcher.cache_duration = data['cache_duration']
    
    return jsonify({'success': True, 'message': 'تنظیمات ذخیره شد'})
