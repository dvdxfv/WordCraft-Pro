"""
LLM 客户端抽象层

提供统一的 LLM 调用接口，支持多种后端（豆包/OpenAI/ChatGLM）。
豆包 API 兼容 OpenAI 协议，通过 openai SDK 调用。
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "doubao"           # doubao / deepseek / openai / chatglm
    api_key: str = ""
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    model: str = "Doubao-Seed-1.6"
    temperature: float = 0.3
    max_tokens: int = 4096

    @classmethod
    def from_yaml(cls, path: str) -> LLMConfig:
        """从 YAML 文件加载配置"""
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        llm_data = data.get("llm", {})
        api_data = llm_data.get("api", {})
        
        # 优先使用豆包配置，如果额度用完则切换到 DeepSeek
        provider = api_data.get("provider", "doubao")
        api_key = api_data.get("api_key", "")
        
        # 检查是否应该使用 DeepSeek（豆包配置为空或显式指定）
        deepseek_data = llm_data.get("deepseek", {})
        if deepseek_data.get("api_key") and (not api_key or provider == "deepseek"):
            return cls(
                provider="deepseek",
                api_key=deepseek_data.get("api_key", ""),
                base_url=deepseek_data.get("base_url", "https://api.deepseek.com/v1"),
                model=deepseek_data.get("model", "deepseek-chat"),
                temperature=deepseek_data.get("temperature", 0.3),
                max_tokens=deepseek_data.get("max_tokens", 4096),
            )
        
        return cls(
            provider=provider,
            api_key=api_key,
            base_url=api_data.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"),
            model=api_data.get("model", "Doubao-Seed-1.6"),
            temperature=api_data.get("temperature", 0.3),
            max_tokens=api_data.get("max_tokens", 4096),
        )


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str          # system / user / assistant
    content: str


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def chat(self, messages: list[ChatMessage],
             temperature: float = None,
             max_tokens: int = None) -> str:
        """发送聊天请求，返回助手回复文本"""
        ...

    @abstractmethod
    def chat_json(self, messages: list[ChatMessage],
                  temperature: float = None) -> dict:
        """发送聊天请求，期望返回 JSON 格式"""
        ...

    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return bool(self._config.api_key)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """从文本中提取 JSON"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            import json
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                import json
                return json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
        return {"raw": text}


class DoubaoClient(LLMClient):
    """豆包大模型客户端（OpenAI 兼容协议）"""

    def __init__(self, config: LLMConfig = None):
        self._config = config or LLMConfig()
        self._client = None

    def _get_client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is not None:
            return self._client

        from openai import OpenAI
        self._client = OpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
        )
        return self._client

    def chat(self, messages: list[ChatMessage],
             temperature: float = None,
             max_tokens: int = None) -> str:
        """发送聊天请求"""
        client = self._get_client()
        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = client.chat.completions.create(
            model=self._config.model,
            messages=api_messages,
            temperature=temperature or self._config.temperature,
            max_tokens=max_tokens or self._config.max_tokens,
        )
        return response.choices[0].message.content.strip()

    def chat_json(self, messages: list[ChatMessage],
                  temperature: float = None) -> dict:
        """发送聊天请求，解析 JSON 返回"""
        result = self.chat(messages, temperature=temperature or 0.1)
        return self._parse_json(result)

    def is_available(self) -> bool:
        return bool(self._config.api_key)


class DeepSeekClient(LLMClient):
    """DeepSeek V3 客户端（OpenAI 兼容协议）"""

    def __init__(self, config: LLMConfig = None):
        self._config = config or LLMConfig(
            provider="deepseek",
            api_key="",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
        )
        self._client = None

    def _get_client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is not None:
            return self._client

        from openai import OpenAI
        self._client = OpenAI(
            api_key=self._config.api_key,
            base_url=self._config.base_url,
        )
        return self._client

    def chat(self, messages: list[ChatMessage],
             temperature: float = None,
             max_tokens: int = None) -> str:
        """发送聊天请求"""
        client = self._get_client()
        api_messages = [{"role": m.role, "content": m.content} for m in messages]

        response = client.chat.completions.create(
            model=self._config.model,
            messages=api_messages,
            temperature=temperature or self._config.temperature,
            max_tokens=max_tokens or self._config.max_tokens,
        )
        return response.choices[0].message.content.strip()

    def chat_json(self, messages: list[ChatMessage],
                  temperature: float = None) -> dict:
        """发送聊天请求，解析 JSON 返回"""
        result = self.chat(messages, temperature=temperature or 0.1)
        return self._parse_json(result)

    def is_available(self) -> bool:
        return bool(self._config.api_key)


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端（用于测试）"""

    def __init__(self):
        self._call_count = 0
        self._last_messages: list[ChatMessage] = []

    def chat(self, messages: list[ChatMessage],
             temperature: float = None,
             max_tokens: int = None) -> str:
        self._call_count += 1
        self._last_messages = messages

        # 检查所有消息内容的关键词
        all_content = "\n".join(m.content for m in messages)

        # QA 分析优先匹配（包含"质量检查报告"等特定关键词）
        if "质量检查报告" in all_content or "问题详情" in all_content:
            return json.dumps({
                "summary": "文档质量总体良好，发现少量问题需要修正。",
                "score": 85,
                "prioritized_issues": [
                    {"original": "帐号", "suggested": "账号", "reason": "常见错别字"},
                ],
            }, ensure_ascii=False)
        elif "交叉引用检查报告" in all_content or "交叉引用" in all_content:
            return json.dumps({
                "summary": "交叉引用基本正确，有1处悬空引用需要处理。",
                "actions": [
                    {"type": "fix_dangling", "detail": "检查悬空引用的编号是否正确"},
                ],
            }, ensure_ascii=False)
        elif "排版" in all_content or "格式" in all_content or "JSON" in all_content:
            return json.dumps({
                "page": {"paper_size": "A4", "margin_top_cm": 2.5,
                        "margin_bottom_cm": 2.5, "margin_left_cm": 3.0,
                        "margin_right_cm": 2.5},
                "heading1": {"font_name_cn": "黑体", "font_size_pt": 16, "bold": True},
                "body": {"font_name_cn": "宋体", "font_size_pt": 12,
                         "first_indent_chars": 2},
            }, ensure_ascii=False)
        elif "修改" in all_content or "建议" in all_content:
            return '建议将"帐号"修改为"账号"。'

        return "模拟回复"

    def chat_json(self, messages: list[ChatMessage],
                  temperature: float = None) -> dict:
        text = self.chat(messages, temperature)
        return self._parse_json(text)

    def is_available(self) -> bool:
        return True

    @property
    def call_count(self) -> int:
        return self._call_count


def create_llm_client(config: LLMConfig = None, config_path: str = None) -> LLMClient:
    """工厂方法：根据配置创建 LLM 客户端
    
    自动切换逻辑：
    1. 优先使用豆包（如果配置了 API Key）
    2. 豆包额度用完后，切换到 DeepSeek V3
    3. 都没有则使用 Mock 客户端（测试用）
    """
    if config is None:
        if config_path:
            config = LLMConfig.from_yaml(config_path)
        else:
            config = LLMConfig()

    # 根据 provider 选择客户端
    if config.provider == "deepseek" and config.api_key:
        print(f"[LLM] 使用 DeepSeek V3 模型：{config.model}")
        return DeepSeekClient(config)
    elif config.api_key:
        print(f"[LLM] 使用豆包模型：{config.model}")
        return DoubaoClient(config)
    else:
        print("[LLM] 未配置 API Key，使用 Mock 客户端（测试模式）")
        return MockLLMClient()
