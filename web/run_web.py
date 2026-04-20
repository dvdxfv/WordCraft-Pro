#!/usr/bin/env python3
"""
WordCraft Pro - Web 应用启动脚本
启动简单的 HTTP 服务器来托管 Web 应用
"""

import http.server
import socketserver
import os
import webbrowser
import urllib.request
from pathlib import Path

# 设置服务器端口
PORT = 8081

# 设置 Web 目录路径
WEB_DIR = Path(__file__).parent

# 后端服务地址
BACKEND_URL = "http://localhost:5000"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """自定义 HTTP 请求处理器，支持 CORS 和 API 代理"""
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            self._proxy_request('GET')
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy_request('POST')
        else:
            super().do_POST()
    
    def _proxy_request(self, method):
        """代理 API 请求到后端服务"""
        try:
            # 构建后端 URL
            backend_url = f"{BACKEND_URL}{self.path}"
            
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            
            # 构建请求头
            headers = {}
            for key, value in self.headers.items():
                if key not in ['Host', 'Content-Length']:
                    headers[key] = value
            
            # 创建请求
            req = urllib.request.Request(backend_url, data=body, headers=headers, method=method)
            
            # 发送请求
            with urllib.request.urlopen(req) as response:
                # 发送响应头
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key not in ['Content-Encoding', 'Transfer-Encoding']:
                        self.send_header(key, value)
                self.end_headers()
                
                # 发送响应体
                self.wfile.write(response.read())
                
        except Exception as e:
            self.send_error(500, f"Proxy error: {str(e)}")

def main():
    # 切换到 Web 目录
    os.chdir(WEB_DIR)
    
    print("=" * 50)
    print("WordCraft Pro - Web 应用启动")
    print("=" * 50)
    print(f"服务器端口: {PORT}")
    print(f"Web 目录: {WEB_DIR}")
    print("=" * 50)
    print("正在启动服务器...")
    
    # 启动服务器
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"服务器已启动！请在浏览器中访问: http://localhost:{PORT}")
        print("按 Ctrl+C 停止服务器")
        
        # 自动打开浏览器
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")

if __name__ == "__main__":
    main()
