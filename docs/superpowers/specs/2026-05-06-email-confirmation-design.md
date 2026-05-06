# 邮件确认页面优化设计

**日期**: 2026-05-06  
**范围**: 用户邮箱验证的确认页面和流程优化  
**状态**: 已批准

---

## 背景

当前注册用户收到 Supabase 的确认邮件，点击 "Confirm your mail" 链接后显示空白页面。需要优化邮件确认流程，让用户在确认页面看到清晰的反馈和指导。

---

## 需求

### 核心需求
1. **强制邮箱验证** — 用户必须确认邮箱才能使用 WordCraft Pro
2. **完整的确认页面** — 用户点击邮件链接后看到有意义的内容，而不是空白
3. **区分处理不同状态** — 成功、失败、已验证等情况显示不同的提示和操作指南
4. **用户清晰的反馈** — 用户清楚地知道发生了什么，以及接下来该做什么

### 约束
- 确认链接有效期：24 小时（Supabase 默认）
- 验证成功后跳转到登录页（不自动登入）
- 已验证的邮箱重复点击链接时，只显示提示信息，不进行跳转

---

## 设计决策

### 1. 邮箱验证模式：强制验证
- 用户注册成功后，邮箱必须验证才能正常使用
- 确认后直接跳转到 landing.html 登录页面

### 2. 确认页面架构：独立页面
- 创建 `web/confirm.html` 作为专用的邮件确认页面
- Supabase 邮件模板配置为指向这个页面，携带 token 参数
- 前端在 confirm.html 中读取参数并调用后端 API 验证

### 3. 错误处理：区分状态
- 加载状态：验证中的加载动画
- 成功：显示邮箱和时间，3 秒后自动跳转登录
- 过期：显示链接过期提示，提供重新发送确认邮件选项
- 已验证：显示邮箱已在某日验证过的提示，不进行跳转

---

## 实现方案

### 文件结构
```
web/
├── confirm.html          (新增) 邮件确认页面
├── landing.html          (改动) 可选：添加重新发送确认邮件功能
└── index.html            (无改动)
```

### 用户流程

```
邮件链接
  ↓
confirm.html?type=signup&token=xxx
  ↓
加载动画 ("正在验证邮箱...")
  ↓
调用 /api/confirm API
  ↓
根据响应显示状态页面：
  ├─ success    → 显示成功提示 → 3秒后跳转 landing.html
  ├─ expired    → 显示过期提示 + 重新发送按钮
  └─ already_verified → 显示已验证提示 (无跳转)
```

### 后端 API：`/api/confirm`

**请求方式**: POST

**请求参数**:
```json
{
  "token": "xxx",           // Supabase 确认 token
  "type": "signup"          // 确认类型
}
```

**响应格式**:

成功验证：
```json
{
  "status": "success",
  "message": "邮箱已验证",
  "email": "user@example.com",
  "verified_at": "2026-05-06 14:30:45"
}
```

链接过期：
```json
{
  "status": "expired",
  "message": "链接已过期"
}
```

邮箱已验证（重复验证）：
```json
{
  "status": "already_verified",
  "message": "邮箱已在 2026-05-05 验证过",
  "verified_at": "2026-05-05"
}
```

**实现位置**: `app.py` 中的 `Api` 类添加 `confirmEmail` 方法

### 前端：confirm.html

**页面结构**:
```html
<!DOCTYPE html>
<html>
<head>
  <!-- 样式：与 landing.html 保持一致 -->
</head>
<body>
  <!-- 四个状态的 UI -->
  
  <!-- 1. 加载状态 -->
  <div id="loadingState">
    <spinner/>
    <p>正在验证邮箱...</p>
  </div>
  
  <!-- 2. 成功状态 -->
  <div id="successState" style="display:none">
    <h2>✓ 邮箱已验证</h2>
    <p>已验证邮箱：<span id="successEmail"></span></p>
    <p>验证时间：<span id="successTime"></span></p>
    <p id="redirectMsg">正在跳转到登录页... (3 秒后自动跳转)</p>
  </div>
  
  <!-- 3. 过期状态 -->
  <div id="expiredState" style="display:none">
    <h2>✗ 链接已过期</h2>
    <p>此确认链接有效期为 24 小时，已失效</p>
    <button id="resendBtn">重新发送确认邮件</button>
  </div>
  
  <!-- 4. 已验证状态 -->
  <div id="alreadyVerifiedState" style="display:none">
    <h2>⚠️ 邮箱已在 <span id="verifiedDate"></span> 验证过</h2>
    <p>无需重复操作</p>
  </div>
</body>
</html>
```

**前端逻辑**:
1. 页面加载时显示加载状态
2. 从 URL 解析 `type` 和 `token` 参数
3. 调用 `window.WC_API.confirmEmail(token, type)`（通过 `flask_app.py` 路由到 `/api/confirm`）
4. 根据响应的 `status` 字段显示对应状态
5. 成功时调用 `setTimeout(() => window.location.href = 'landing.html', 3000)`

### Supabase 邮件模板配置

**修改位置**: Supabase 控制台 → Authentication → Email Templates → Confirm signup

**邮件链接模板**:
```
https://yourdomain.com/confirm.html?type=signup&token={{ .ConfirmationURL }}
```

> 注：实际部署时需要替换 `yourdomain.com` 为真实域名

---

## 可选功能

### 重新发送确认邮件
在 `landing.html` 的登录表单下方可添加：
```html
<p>没有收到邮件？<a href="#" onclick="resendConfirmation()">重新发送确认邮件</a></p>
```

实现方式：调用 Supabase 的 `auth.resend({ type: 'signup', email: 'user@example.com' })`

---

## 测试场景

| 场景 | 预期结果 |
|------|---------|
| 首次点击有效链接 | 显示成功页面 + 邮箱和时间 + 3秒后跳转登录 |
| 24小时后点击链接 | 显示过期提示 + 重新发送按钮 |
| 已验证邮箱再点链接 | 显示"已在XX时间验证过"的提示，无跳转 |
| 点击重新发送按钮 | 重新发送确认邮件到该邮箱 |
| 网络异常 | 显示通用错误提示 |

---

## 后续步骤

1. **实现后端 API** (`/api/confirm`) — 调用 Supabase 验证 token
2. **创建前端页面** (`web/confirm.html`) — 实现四个状态的 UI
3. **配置 Supabase 邮件模板** — 修改确认链接指向 confirm.html
4. **可选：添加重新发送功能** — 在 landing.html 中集成
5. **测试和部署** — 手动测试各个场景，部署到生产环境

---

## 相关文件

- `app.py` — 添加 `confirmEmail` 方法
- `web/flask_app.py` — 添加 `/api/confirm` 路由
- `web/confirm.html` — 新增确认页面
- `web/landing.html` — 可选改动

---

## 实现差异说明（2026-05-06 实施后）

- 实际实现取消了 `/api/confirm` 后端 API。Supabase 邮件链接已是服务器端验证 URL，验证后通过 `emailRedirectTo` 直接重定向到 confirm.html，前端通过解析 URL hash 即可。
- 状态 4（已验证再点击）实际不会触发 — Supabase 对"已使用链接"和"过期链接"返回相同 `error_code=otp_expired`，无法可靠区分。该状态保留为防御性代码。
- Supabase Dashboard 的 Redirect URLs 必须包含 `/confirm.html` 路径，否则重定向会被拒绝。
