# Windows Server 部署指南

> 适用：腾讯云 Windows Server + Nginx + NSSM + SSL

---

## 前置条件

| 软件 | 说明 | 下载 |
|---|---|---|
| Python 3.11+ | 运行后端 | python.org |
| Git | 拉取代码 | git-scm.com |
| Nginx for Windows | 反向代理 | nginx.org/en/download |
| NSSM | 将 Flask 注册为 Windows 服务 | nssm.cc/download |

---

## 一、拉取代码

```powershell
cd C:\www
git clone https://github.com/dvdxfv/WordCraft-Pro.git
cd WordCraft-Pro
```

---

## 二、安装 Python 依赖

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 三、配置环境变量

```powershell
# 复制模板
copy .env.example .env

# 用文本编辑器打开并填入真实值
notepad .env
```

`.env` 至少需要填写：

```
DEEPSEEK_API_KEY=sk-xxxx
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJxxx...
```

---

## 四、验证后端能正常启动

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_server.ps1
```

浏览器访问 `http://127.0.0.1:5000`，看到 API 说明页即成功，按 `Ctrl+C` 停止。

---

## 五、注册为 Windows 服务（开机自启）

> 需要**管理员权限**运行 PowerShell

```powershell
# 确保 nssm.exe 在 PATH 中，或指定完整路径
powershell -ExecutionPolicy Bypass -File .\scripts\install_service.ps1
```

验证：

```powershell
Get-Service WordCraftFlask   # 应显示 Running
```

常用命令：

```powershell
nssm stop  WordCraftFlask    # 停止
nssm start WordCraftFlask    # 启动
nssm restart WordCraftFlask  # 重启
nssm remove WordCraftFlask confirm  # 卸载服务
```

---

## 六、配置 Nginx

1. 将 `deploy/nginx.conf.example` 内容复制到 Nginx 的 `conf/nginx.conf`（或 `conf.d/wordcraft.conf`）
2. 替换以下占位符：
   - `your-domain.com` → 你的实际域名
   - `/path/to/wordcraft-pro` → 项目路径，如 `C:/www/WordCraft-Pro`
   - SSL 证书路径 → 腾讯云下载的 `.pem` 和 `.key`
3. 测试并重载：

```powershell
cd C:\nginx
.\nginx.exe -t           # 测试配置
.\nginx.exe -s reload    # 重载
```

---

## 七、SSL 证书

腾讯云控制台 → SSL 证书 → 下载 Nginx 格式证书，解压后得到 `.pem` 和 `.key`，路径填入 nginx.conf。

若使用 **Cloudflare**，在 Cloudflare 设置 DNS 代理（橙色云），SSL 模式选「完全（严格）」，腾讯云服务器上安装 Origin Certificate。

---

## 八、日志位置

| 日志 | 路径 |
|---|---|
| Flask 标准输出 | `logs/flask_stdout.log` |
| Flask 错误输出 | `logs/flask_stderr.log` |
| Nginx 访问日志 | `C:/nginx/logs/wordcraft_access.log` |
| Nginx 错误日志 | `C:/nginx/logs/wordcraft_error.log` |

---

## 九、更新部署

```powershell
git pull origin main
pip install -r requirements.txt   # 如有新依赖
nssm restart WordCraftFlask
```
