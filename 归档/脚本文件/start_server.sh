#!/bin/bash

# WordCraft Pro 后端服务启动脚本
# 用于启动 Flask 后端服务，供 Nginx 代理

echo "Starting WordCraft Pro backend server..."

# 检查 Python 版本
echo "Checking Python version..."
python3 --version

# 安装依赖（如果尚未安装）
if [ ! -f "requirements.txt" ]; then
    echo "requirements.txt not found!"
    exit 1
fi

echo "Installing dependencies..."
pip3 install -r requirements.txt

# 确保安装Flask
echo "Installing Flask..."
pip3 install flask flask-cors

# 创建Flask应用包装器
echo "Creating Flask app wrapper..."
cat > flask_app.py << 'EOF'
from flask import Flask, request, jsonify
from flask_cors import CORS
from app import Api

app = Flask(__name__)
CORS(app)  # 启用CORS

api = Api()

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

@app.route('/api/runQA', methods=['POST'])
def run_qa():
    data = request.json
    content = data.get('content')
    categories = data.get('categories')
    result = api.runQA(content, categories)
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
EOF

# 启动 Flask 服务
echo "Starting Flask server on 127.0.0.1:5000..."
python3 flask_app.py
