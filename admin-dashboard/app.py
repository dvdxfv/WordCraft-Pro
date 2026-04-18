#!/usr/bin/env python3
"""
WordCraft Pro 管理后台 - FastAPI 应用
管理者可以查看用户、管理 Token 额度、查看统计数据
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_tracker import TokenTracker
from core.user_data_manager import UserDataManager

app = FastAPI(title="WordCraft Pro Admin Dashboard", version="1.0.0")

# 初始化数据管理器
DATA_DIR = os.environ.get('WORDCRAFT_DATA_DIR', os.path.join(os.path.expanduser('~'), 'WordCraft-Pro'))
user_manager = UserDataManager(DATA_DIR)
token_tracker = TokenTracker(DATA_DIR)

# ------------------------------------------------------------------
#  数据模型
# ------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str

class QuotaUpdate(BaseModel):
    quota: int

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None

# ------------------------------------------------------------------
#  管理员认证（简化版，实际应使用 JWT）
# ------------------------------------------------------------------

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "wordcraft2026"

def verify_admin(username: str, password: str) -> bool:
    """验证管理员账号"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

# ------------------------------------------------------------------
#  页面路由
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def admin_home():
    """管理后台首页"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WordCraft Pro 管理后台</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
            .header { background: #1890ff; color: white; padding: 20px; }
            .header h1 { font-size: 24px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
            .stat-card .value { font-size: 32px; font-weight: bold; color: #1890ff; }
            .nav { display: flex; gap: 10px; margin: 20px 0; }
            .nav a { padding: 10px 20px; background: white; border-radius: 4px; text-decoration: none; color: #333; }
            .nav a:hover { background: #1890ff; color: white; }
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
            th { background: #fafafa; font-weight: 600; }
            .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #1890ff; color: white; }
            .btn-danger { background: #ff4d4f; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>WordCraft Pro 管理后台</h1>
            <p>管理用户、模板和 Token 额度</p>
        </div>
        <div class="container">
            <div class="nav">
                <a href="/dashboard">仪表盘</a>
                <a href="/users">用户管理</a>
                <a href="/tokens">Token 管理</a>
                <a href="/templates">模板管理</a>
                <a href="/logs">日志查看</a>
            </div>
            <h2>仪表盘</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>总用户数</h3>
                    <div class="value" id="total-users">--</div>
                </div>
                <div class="stat-card">
                    <h3>总 Token 用量</h3>
                    <div class="value" id="total-tokens">--</div>
                </div>
                <div class="stat-card">
                    <h3>模板数量</h3>
                    <div class="value" id="total-templates">--</div>
                </div>
                <div class="stat-card">
                    <h3>文档数量</h3>
                    <div class="value" id="total-documents">--</div>
                </div>
            </div>
        </div>
        <script>
            fetch('/api/stats').then(r => r.json()).then(data => {
                document.getElementById('total-users').textContent = data.total_users || 0;
                document.getElementById('total-tokens').textContent = (data.total_tokens || 0).toLocaleString();
                document.getElementById('total-templates').textContent = data.total_templates || 0;
                document.getElementById('total-documents').textContent = data.total_documents || 0;
            });
        </script>
    </body>
    </html>
    """

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """管理员登录页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>管理员登录</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; align-items: center; justify-content: center; }
            .login-box { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 400px; }
            h2 { text-align: center; margin-bottom: 30px; color: #333; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #666; }
            input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
            input:focus { border-color: #667eea; outline: none; }
            .btn { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }
            .btn:hover { background: #5568d3; }
            .error { color: #ff4d4f; text-align: center; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>管理员登录</h2>
            <form id="loginForm">
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" id="username" required>
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input type="password" id="password" required>
                </div>
                <button type="submit" class="btn">登录</button>
                <div id="error" class="error"></div>
            </form>
        </div>
        <script>
            document.getElementById('loginForm').onsubmit = async (e) => {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = '/';
                } else {
                    document.getElementById('error').textContent = data.error || '登录失败';
                }
            };
        </script>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """仪表盘页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>仪表盘 - 管理后台</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
            .header { background: #1890ff; color: white; padding: 20px; }
            .header h1 { font-size: 24px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
            .stat-card .value { font-size: 32px; font-weight: bold; color: #1890ff; }
            .nav { display: flex; gap: 10px; margin: 20px 0; }
            .nav a { padding: 10px 20px; background: white; border-radius: 4px; text-decoration: none; color: #333; }
            .nav a:hover { background: #1890ff; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>WordCraft Pro 管理后台 - 仪表盘</h1>
        </div>
        <div class="container">
            <div class="nav">
                <a href="/">首页</a>
                <a href="/users">用户管理</a>
                <a href="/tokens">Token 管理</a>
                <a href="/templates">模板管理</a>
                <a href="/logs">日志查看</a>
            </div>
            <h2>系统概览</h2>
            <div class="stats-grid">
                <div class="stat-card"><h3>总用户数</h3><div class="value" id="total-users">--</div></div>
                <div class="stat-card"><h3>总 Token 用量</h3><div class="value" id="total-tokens">--</div></div>
                <div class="stat-card"><h3>模板数量</h3><div class="value" id="total-templates">--</div></div>
                <div class="stat-card"><h3>文档数量</h3><div class="value" id="total-documents">--</div></div>
            </div>
        </div>
        <script>
            fetch('/api/stats').then(r => r.json()).then(data => {
                document.getElementById('total-users').textContent = data.total_users || 0;
                document.getElementById('total-tokens').textContent = (data.total_tokens || 0).toLocaleString();
                document.getElementById('total-templates').textContent = data.total_templates || 0;
                document.getElementById('total-documents').textContent = data.total_documents || 0;
            });
        </script>
    </body>
    </html>
    """

@app.get("/users", response_class=HTMLResponse)
async def users_page():
    """用户管理页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>用户管理 - 管理后台</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
            .header { background: #1890ff; color: white; padding: 20px; }
            .header h1 { font-size: 24px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .nav { display: flex; gap: 10px; margin: 20px 0; }
            .nav a { padding: 10px 20px; background: white; border-radius: 4px; text-decoration: none; color: #333; }
            .nav a:hover { background: #1890ff; color: white; }
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
            th { background: #fafafa; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>用户管理</h1>
        </div>
        <div class="container">
            <div class="nav">
                <a href="/">首页</a>
                <a href="/dashboard">仪表盘</a>
                <a href="/tokens">Token 管理</a>
                <a href="/templates">模板管理</a>
                <a href="/logs">日志查看</a>
            </div>
            <h2>用户列表</h2>
            <table>
                <thead>
                    <tr><th>用户 ID</th><th>邮箱</th><th>昵称</th><th>Token 配额</th><th>已用量</th></tr>
                </thead>
                <tbody id="user-list"></tbody>
            </table>
        </div>
        <script>
            fetch('/api/users').then(r => r.json()).then(data => {
                const tbody = document.getElementById('user-list');
                if (data.success && data.users) {
                    data.users.forEach(u => {
                        tbody.innerHTML += `<tr><td>${u.id || '--'}</td><td>${u.email || '--'}</td><td>${u.nickname || '--'}</td><td>${u.token_quota || 100000}</td><td>${u.token_used || 0}</td></tr>`;
                    });
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/tokens", response_class=HTMLResponse)
async def tokens_page():
    """Token 管理页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Token 管理 - 管理后台</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
            .header { background: #1890ff; color: white; padding: 20px; }
            .header h1 { font-size: 24px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .nav { display: flex; gap: 10px; margin: 20px 0; }
            .nav a { padding: 10px 20px; background: white; border-radius: 4px; text-decoration: none; color: #333; }
            .nav a:hover { background: #1890ff; color: white; }
            .info-card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
            .info-card h3 { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Token 管理</h1>
        </div>
        <div class="container">
            <div class="nav">
                <a href="/">首页</a>
                <a href="/dashboard">仪表盘</a>
                <a href="/users">用户管理</a>
                <a href="/templates">模板管理</a>
                <a href="/logs">日志查看</a>
            </div>
            <div class="info-card">
                <h3>Token 使用统计</h3>
                <div id="stats">加载中...</div>
            </div>
            <div class="info-card">
                <h3>使用历史</h3>
                <div id="history">加载中...</div>
            </div>
        </div>
        <script>
            fetch('/api/tokens/usage').then(r => r.json()).then(data => {
                const stats = data.stats;
                document.getElementById('stats').innerHTML = `
                    <p>总使用量: ${stats.total_usage || 0} tokens</p>
                    <p>总请求数: ${stats.total_requests || 0}</p>
                    <p>平均每次: ${stats.avg_usage || 0} tokens</p>
                `;
                const history = data.history;
                if (history && history.length > 0) {
                    document.getElementById('history').innerHTML = history.slice(-10).map(h => `<p>${h.created_at}: ${h.amount} tokens (${h.purpose})</p>`).join('');
                } else {
                    document.getElementById('history').innerHTML = '<p>暂无记录</p>';
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/templates", response_class=HTMLResponse)
async def templates_page():
    """模板管理页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>模板管理 - 管理后台</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
            .header { background: #1890ff; color: white; padding: 20px; }
            .header h1 { font-size: 24px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .nav { display: flex; gap: 10px; margin: 20px 0; }
            .nav a { padding: 10px 20px; background: white; border-radius: 4px; text-decoration: none; color: #333; }
            .nav a:hover { background: #1890ff; color: white; }
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
            th { background: #fafafa; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>模板管理</h1>
        </div>
        <div class="container">
            <div class="nav">
                <a href="/">首页</a>
                <a href="/dashboard">仪表盘</a>
                <a href="/users">用户管理</a>
                <a href="/tokens">Token 管理</a>
                <a href="/logs">日志查看</a>
            </div>
            <h2>模板列表</h2>
            <table>
                <thead>
                    <tr><th>模板 ID</th><th>名称</th><th>分类</th><th>创建时间</th></tr>
                </thead>
                <tbody id="template-list"></tbody>
            </table>
        </div>
        <script>
            fetch('/api/templates').then(r => r.json()).then(data => {
                const tbody = document.getElementById('template-list');
                if (data.success && data.templates) {
                    data.templates.forEach(t => {
                        tbody.innerHTML += `<tr><td>${t.id || '--'}</td><td>${t.name || '--'}</td><td>${t.category || '--'}</td><td>${t.created_at || '--'}</td></tr>`;
                    });
                } else {
                    tbody.innerHTML = '<tr><td colspan="4">暂无模板</td></tr>';
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/logs", response_class=HTMLResponse)
async def logs_page():
    """日志查看页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>日志查看 - 管理后台</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
            .header { background: #1890ff; color: white; padding: 20px; }
            .header h1 { font-size: 24px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .nav { display: flex; gap: 10px; margin: 20px 0; }
            .nav a { padding: 10px 20px; background: white; border-radius: 4px; text-decoration: none; color: #333; }
            .nav a:hover { background: #1890ff; color: white; }
            .info-card { background: white; border-radius: 8px; padding: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>日志查看</h1>
        </div>
        <div class="container">
            <div class="nav">
                <a href="/">首页</a>
                <a href="/dashboard">仪表盘</a>
                <a href="/users">用户管理</a>
                <a href="/tokens">Token 管理</a>
                <a href="/templates">模板管理</a>
            </div>
            <div class="info-card">
                <h3>操作日志</h3>
                <p>日志功能开发中...</p>
            </div>
        </div>
    </body>
    </html>
    """

# ------------------------------------------------------------------
#  API 路由
# ------------------------------------------------------------------

@app.post("/api/login")
async def api_login(request: LoginRequest):
    """管理员登录 API"""
    if verify_admin(request.username, request.password):
        return {"success": True, "message": "登录成功"}
    return {"success": False, "error": "用户名或密码错误"}

@app.get("/api/stats")
async def get_stats():
    """获取统计数据"""
    try:
        quota_info = token_tracker.get_quota()
        usage_stats = token_tracker.get_usage_stats(days=30)
        templates = user_manager.list_cached_templates()
        recent_files = user_manager.load_recent_files()
        
        return {
            "total_users": 1,  # 本地模式，固定为1
            "total_tokens": quota_info['used'],
            "total_templates": len(templates),
            "total_documents": len(recent_files),
            "token_quota": quota_info['quota'],
            "token_remaining": quota_info['remaining'],
            "usage_percentage": quota_info['usage_percentage'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def get_users():
    """获取用户列表"""
    user_info = user_manager.load_user_info()
    if user_info:
        return {"success": True, "users": [user_info]}
    return {"success": True, "users": []}

@app.put("/api/users/{user_id}/quota")
async def update_user_quota(user_id: str, request: QuotaUpdate):
    """更新用户 Token 配额"""
    success = token_tracker.set_quota(request.quota)
    if success:
        return {"success": True, "message": "配额已更新"}
    raise HTTPException(status_code=500, detail="更新配额失败")

@app.get("/api/tokens/usage")
async def get_token_usage(days: int = 30):
    """获取 Token 使用统计"""
    stats = token_tracker.get_usage_stats(days=days)
    history = token_tracker.get_usage_history(limit=50)
    warning = token_tracker.check_warning()
    return {
        "stats": stats,
        "history": history,
        "warning": warning,
    }

@app.get("/api/templates")
async def get_templates():
    """获取模板列表"""
    templates = user_manager.list_cached_templates()
    return {"success": True, "templates": templates}

@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    """删除模板"""
    success = user_manager.delete_cached_template(template_id)
    if success:
        return {"success": True, "message": "模板已删除"}
    raise HTTPException(status_code=500, detail="删除模板失败")

@app.get("/api/logs")
async def get_logs():
    """获取操作日志"""
    # TODO: 实现日志查看
    return {"success": True, "logs": []}

# ------------------------------------------------------------------
#  启动
# ------------------------------------------------------------------

def main():
    """启动管理后台"""
    import uvicorn
    print("=" * 50)
    print("WordCraft Pro 管理后台")
    print("=" * 50)
    print(f"数据目录: {DATA_DIR}")
    print(f"管理地址: http://localhost:8080")
    print(f"默认账号: admin / wordcraft2026")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    main()
