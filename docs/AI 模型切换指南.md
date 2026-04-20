# AI 模型切换指南

## 📋 概述

WordCraft Pro 支持多种 AI 模型，当前已集成：
- ✅ **豆包（Doubao-Seed-1.6）** - 当前使用
- ✅ **DeepSeek V3（deepseek-chat）** - 备用模型
- ⏳ **本地 ChatGLM** - 离线备用

## 🔄 切换方式

### 方式 1：自动切换（推荐）

**原理：** 系统自动检测豆包 API Key 状态，额度用完后自动切换到 DeepSeek

**操作步骤：**

1. **当前使用豆包**
   ```yaml
   llm:
     api:
       provider: "doubao"
       api_key: "your-doubao-api-key"  # 当前额度
   ```

2. **豆包额度用完后**
   - 将豆包 API Key 清空或保留
   - 填写 DeepSeek API Key
   ```yaml
   llm:
     api:
       provider: "doubao"
       api_key: ""  # 留空或保留原 key
       
     deepseek:
       provider: "deepseek"
       api_key: "your-deepseek-api-key"  # 填写新的 API Key
   ```

3. **系统自动切换**
   - 重启应用
   - 系统检测到豆包 API Key 为空，自动使用 DeepSeek
   - 启动日志显示：`[LLM] 使用 DeepSeek V3 模型：deepseek-chat`

---

### 方式 2：手动切换

**直接指定使用 DeepSeek：**

```yaml
llm:
  api:
    provider: "deepseek"  # 直接指定
    api_key: "your-deepseek-api-key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
```

---

## 📝 DeepSeek API Key 获取

### 1. 注册 DeepSeek 账号
访问：https://platform.deepseek.com/

### 2. 创建 API Key
- 进入控制台
- 点击"API Keys"
- 创建新的 API Key
- 复制保存

### 3. 充值（如需要）
- DeepSeek 按 Token 计费
- 价格参考：输入 ¥0.002/1K tokens，输出 ¥0.008/1K tokens
- 建议充值：¥10-50 元（根据使用量）

---

## ⚙️ 配置文件示例

### 当前配置（使用豆包）
```yaml
llm:
  mode: "api"
  
  # 云端 API 配置（豆包）
  api:
    provider: "doubao"
    api_key: "d9523eb2-f741-4122-ab0f-e6ed95ce59f2"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    model: "Doubao-Seed-1.6"
    temperature: 0.3
    max_tokens: 4096

  # DeepSeek 配置（备用）
  deepseek:
    provider: "deepseek"
    api_key: ""  # 暂时为空
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    temperature: 0.3
    max_tokens: 4096
```

### 切换后配置（使用 DeepSeek）
```yaml
llm:
  mode: "api"
  
  # 云端 API 配置（豆包 - 额度用完）
  api:
    provider: "doubao"
    api_key: ""  # 留空
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    model: "Doubao-Seed-1.6"
    temperature: 0.3
    max_tokens: 4096

  # DeepSeek 配置（主用）
  deepseek:
    provider: "deepseek"
    api_key: "sk-xxxxxxxxxxxx"  # 填写您的 DeepSeek API Key
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    temperature: 0.3
    max_tokens: 4096
```

---

## 🧪 测试验证

### 测试当前模型
```bash
python main.py --test
```

查看输出日志：
- `[LLM] 使用豆包模型：Doubao-Seed-1.6` - 当前使用豆包
- `[LLM] 使用 DeepSeek V3 模型：deepseek-chat` - 当前使用 DeepSeek

### 测试 AI 功能
1. 打开应用
2. 点击"质量检查" → "AI 深度分析"
3. 查看是否正常调用 AI

---

## 📊 模型对比

| 特性 | 豆包 Doubao-Seed-1.6 | DeepSeek V3 |
|------|---------------------|-------------|
| **提供商** | 字节跳动 | 深度求索 |
| **上下文** | 128K | 128K |
| **价格** | ¥0.008/1K tokens | ¥0.002/1K tokens |
| **速度** | 快 | 快 |
| **中文能力** | 优秀 | 优秀 |
| **代码能力** | 良好 | 优秀 |
| **推荐场景** | 通用任务 | 性价比优先 |

---

## 🔧 故障排查

### 问题 1：切换后无法使用
**检查：**
1. API Key 是否正确填写
2. `config.yaml` 语法是否正确
3. 重启应用

### 问题 2：API 调用失败
**检查：**
1. 网络连接正常
2. API Key 余额充足
3. 查看错误日志

### 问题 3：模型响应慢
**解决：**
1. 检查网络延迟
2. 降低 `max_tokens` 参数
3. 尝试其他模型

---

## 💡 最佳实践

### 1. 额度管理
- 优先使用免费额度
- 监控 API 使用量
- 设置使用提醒

### 2. 成本控制
- 使用 Mock 客户端测试（不消耗额度）
- 批量处理时选择性价比高的模型
- 本地能处理的任务不调用 AI

### 3. 性能优化
- 设置合理的 `temperature`（0.3 推荐）
- 限制 `max_tokens` 避免过长响应
- 使用缓存减少重复调用

---

## 📞 技术支持

如有问题，请查看：
- `llm/client.py` - LLM 客户端源码
- `config.yaml` - 配置文件
- 启动日志 - 查看模型加载信息

---

**最后更新**：2026 年 4 月 16 日  
**版本**：v0.9.0
