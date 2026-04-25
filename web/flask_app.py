import base64
import os
import sys
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import Api

app = Flask(__name__)
CORS(app)  # 启用CORS

api = Api()


@app.route("/")
def root():
    """5000 端口仅提供 /api/*；直接打开根路径会 404，这里给出说明。"""
    html = (
        "<!DOCTYPE html><html lang=zh-CN><head><meta charset=utf-8>"
        "<title>WordCraft Pro API</title></head><body style="
        "'font-family:system-ui,sans-serif;padding:24px;line-height:1.6'>"
        "<h2>这是后端 API（端口 5000）</h2>"
        "<p>本服务没有网页首页，只提供 <code>/api/...</code> 接口。</p>"
        "<p>请在浏览器打开前端页面：<strong>"
        "<a href=http://127.0.0.1:8081/>http://127.0.0.1:8081/</a></strong></p>"
        "</body></html>"
    )
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route('/api/openFile', methods=['POST'])
def open_file():
    data = request.json
    file_content = data.get('file_content')
    file_name = data.get('file_name')
    result = api.openFile(file_content, file_name)
    return result

@app.route('/api/saveFile', methods=['POST'])
def save_file():
    data = request.json
    content = data.get('content')
    file_name = data.get('file_name')
    result = api.saveFile(content, file_name)
    return result

@app.route('/api/exportDocx', methods=['POST'])
def export_docx():
    data = request.json
    content = data.get('content')
    format_params = data.get('format_params')
    file_name = data.get('file_name')
    result = api.exportDocx(content, format_params, file_name)
    return result

@app.route('/api/getSystemInfo', methods=['GET'])
def get_system_info():
    result = api.getSystemInfo()
    return result

@app.route('/api/qa/health', methods=['GET'])
def qa_health():
    result = api.getQAHealth()
    return result

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    result = api.login(email, password)
    return result

@app.route('/api/logout', methods=['POST'])
def logout():
    result = api.logout()
    return result

@app.route('/api/getTokenUsage', methods=['GET'])
def get_token_usage():
    result = api.getTokenUsage()
    return result

@app.route('/api/getUserTemplates', methods=['GET'])
def get_user_templates():
    result = api.getUserTemplates()
    return result

@app.route('/api/uploadTemplate', methods=['POST'])
def upload_template():
    data = request.json
    file_content_b64 = data.get('file_content', '')
    name = data.get('name', '未命名模板')
    file_name = data.get('file_name', 'template.docx')
    try:
        file_bytes = base64.b64decode(file_content_b64)
        suffix = os.path.splitext(file_name)[1] or '.docx'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        result = api.uploadTemplate(tmp_path, name)
        os.unlink(tmp_path)
        return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/api/convertDoc', methods=['POST'])
def convert_doc():
    data = request.json
    file_content_b64 = data.get('file_content', '')
    file_name = data.get('file_name', 'file.doc')
    try:
        file_bytes = base64.b64decode(file_content_b64)
        suffix = os.path.splitext(file_name)[1] or '.doc'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        from parsers.dispatcher import _convert_doc_to_docx
        docx_path = _convert_doc_to_docx(tmp_path)
        with open(docx_path, 'rb') as f:
            docx_b64 = base64.b64encode(f.read()).decode('utf-8')
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return jsonify({'success': True, 'content': docx_b64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/deleteTemplate', methods=['POST'])
def delete_template():
    data = request.json
    template_id = data.get('template_id', '')
    result = api.deleteTemplate(template_id)
    return result

@app.route('/api/saveTemplateSettings', methods=['POST'])
def save_template_settings():
    data = request.json
    name = data.get('name', '未命名模板')
    template_data = data.get('template_data', {})
    import json
    result = api.saveTemplateSettings(name, json.dumps(template_data))
    return result

@app.route('/api/getUserSettings', methods=['GET'])
def get_user_settings():
    result = api.getUserSettings()
    return result

@app.route('/api/saveUserSettings', methods=['POST'])
def save_user_settings():
    import json as _json
    data = request.json
    settings = data.get('settings', {})
    result = api.saveUserSettings(_json.dumps(settings))
    return result

@app.route('/api/runQA', methods=['POST'])
def run_qa():
    import json as _json
    data = request.json
    content = data.get('content')
    categories = data.get('categories')
    cats_str = _json.dumps(categories) if isinstance(categories, list) else (categories or '["typo","consistency","logic","format","crossref"]')
    result = api.runQA(content, cats_str)
    return result

@app.route('/api/runXRef', methods=['POST'])
def run_xref():
    data = request.json
    content = data.get('content')
    result = api.runXRef(content)
    return result

@app.route('/api/applyFormat', methods=['POST'])
def apply_format():
    data = request.json
    content = data.get('content')
    rules = data.get('rules')
    result = api.applyFormat(content, rules)
    return result

@app.route('/api/saveDocument', methods=['POST'])
def save_document():
    data = request.json
    content = data.get('content')
    title = data.get('title')
    result = api.saveDocument(content, title)
    return result

@app.route('/api/loadDocument', methods=['POST'])
def load_document():
    data = request.json
    doc_id = data.get('doc_id')
    result = api.loadDocument(doc_id)
    return result

@app.route('/api/getDocumentList', methods=['GET'])
def get_document_list():
    result = api.getDocumentList()
    return result

@app.route('/api/callAI', methods=['POST'])
def call_ai():
    data = request.json
    system_prompt = data.get('system_prompt')
    user_message = data.get('user_message')
    config = data.get('config')
    result = api.callAI(system_prompt, user_message, config)
    return result

@app.route('/api/refreshDocxFields', methods=['POST'])
def refresh_docx_fields():
    data = request.json
    docx_b64 = data.get('docx_b64', '')
    result = api.refreshDocxFields(docx_b64)
    return result

@app.route('/api/updateDocument', methods=['POST'])
def update_document():
    data = request.json
    doc_id = data.get('doc_id')
    content = data.get('content')
    title = data.get('title', '未命名文档')
    result = api.updateDocument(doc_id, content, title)
    return result

@app.route('/api/acceptSuggestion', methods=['POST'])
def accept_suggestion():
    data = request.json
    content = data.get('content')
    issue_id = data.get('issue_id')
    original_text = data.get('original_text')
    suggested_text = data.get('suggested_text')
    result = api.acceptSuggestion(content, issue_id, original_text, suggested_text)
    return result

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
