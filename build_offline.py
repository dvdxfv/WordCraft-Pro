#!/usr/bin/env python3
"""
生成 WordCraft Pro 离线版 HTML
将 CDN 引用的 JS 库内嵌到 HTML 中，双击即可使用（无需网络）
"""

import urllib.request
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

INPUT = "web/index.html"
OUTPUT = "dist/WordCraft-Pro-离线版.html"

# CDN 资源列表: (原始 script 标签中的 src, 用于注释的名称)
REPLACEMENTS = [
    'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2',
    'https://cdn.jsdelivr.net/npm/mammoth@1.6.0/mammoth.browser.min.js',
    'https://cdn.jsdelivr.net/npm/docx@8.5.0/build/index.umd.min.js',
    'https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js',
]

print("=" * 50)
print("  WordCraft Pro 离线版生成工具")
print("=" * 50)
print()

# 读取原始 HTML
with open(INPUT, "r", encoding="utf-8") as f:
    html = f.read()

# 下载并内嵌每个 CDN 库
for url in REPLACEMENTS:
    name = url.split("/")[-1] or "lib"
    print(f"📦 下载 {name}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            js_code = resp.read().decode("utf-8")
        old_tag = f'<script src="{url}"></script>'
        new_tag = f'<script>\n/* {name} (embedded for offline use) */\n{js_code}\n</script>'
        if old_tag in html:
            html = html.replace(old_tag, new_tag, 1)
            print(f"  ✅ 已内嵌 {name} ({len(js_code)//1024}KB)")
        else:
            print(f"  ⚠️ 未找到: {old_tag[:60]}...")
    except Exception as e:
        print(f"  ❌ 下载失败 {name}: {e}")
        old_tag = f'<script src="{url}"></script>'
        fallback = f'<script>console.warn("{name}: 离线不可用，请联网");</script>'
        html = html.replace(old_tag, fallback, 1)

# 添加离线标识
html = html.replace(
    "<title>WordCraft Pro",
    "<title>WordCraft Pro (离线版)"
)

# 确保输出目录存在
os.makedirs("dist", exist_ok=True)

# 写入离线版
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(OUTPUT) // 1024
print()
print("=" * 50)
print(f"✅ 离线版生成成功！")
print(f"📁 文件: {OUTPUT}")
print(f"📦 大小: {size_kb} KB")
print()
print("💡 使用方式: 双击打开即可在浏览器中使用")
print("   - 排版检查、QA 规则检查: 无需网络")
print("   - AI 排版解析、AI 深度分析: 需要联网")
print("=" * 50)
