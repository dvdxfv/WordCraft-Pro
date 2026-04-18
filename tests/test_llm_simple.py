#!/usr/bin/env python3
"""
LLM 质量检测简化测试 - 直接测试 LLM API 调用
"""

import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from llm.client import create_llm_client, LLMConfig, ChatMessage

def test_llm_call():
    """直接测试 LLM API 调用"""
    print("测试 LLM API 调用...")
    
    # 创建 LLM 客户端
    config = LLMConfig.from_yaml("config.yaml")
    client = create_llm_client(config)
    
    if not client.is_available():
        print("LLM 客户端不可用，跳过测试")
        return
    
    # 测试 prompt
    prompt = """你是一个专业的中文文档错别字检测专家。请仔细检查以下文本，找出所有可能的错别字和用词错误。

检测范围：
1. 常见错别字
2. 的/地/得误用
3. 同音异形词误用
4. 成语错字

请用严格的 JSON 格式输出（不要包含 markdown 代码块标记）：
{"issues": [{"text": "错误片段", "suggestion": "建议修改为", "reason": "错误原因", "confidence": 0.9}]}

如果没有发现问题，输出：{"issues": []}

待检查文本：
这个项目的帐单需要按装新的软件系统。"""

    messages = [ChatMessage(role="user", content=prompt)]
    
    try:
        result = client.chat(messages, temperature=0.1)
        print(f"\nLLM 返回内容（前500字符）:")
        print(result[:500])
        print("\n" + "="*60)
        
        # 尝试解析 JSON
        print("\n尝试解析 JSON...")
        result_stripped = result.strip()
        
        # 移除 markdown
        if result_stripped.startswith("```"):
            import re
            result_stripped = re.sub(r"^```(?:json)?\s*\n?", "", result_stripped, flags=re.MULTILINE)
            result_stripped = re.sub(r"\s*```\s*$", "", result_stripped)
            print("已移除 markdown 标记")
        
        print(f"处理后的内容（前300字符）:")
        print(result_stripped[:300])
        
        # 解析 JSON
        try:
            data = json.loads(result_stripped)
            print(f"\nJSON 解析成功!")
            print(f"issues 数量: {len(data.get('issues', []))}")
            for issue in data.get('issues', []):
                print(f"  - {issue}")
        except json.JSONDecodeError as e:
            print(f"\nJSON 解析失败: {e}")
            # 尝试提取 JSON
            print("\n尝试提取 JSON...")
            start = result_stripped.find("{")
            end = result_stripped.rfind("}")
            if start >= 0 and end > start:
                json_str = result_stripped[start:end + 1]
                print(f"提取的 JSON 字符串（前200字符）: {json_str[:200]}")
                try:
                    data = json.loads(json_str)
                    print(f"提取后 JSON 解析成功!")
                    print(f"issues 数量: {len(data.get('issues', []))}")
                except json.JSONDecodeError as e2:
                    print(f"提取后仍然失败: {e2}")
            else:
                print("未找到 JSON 对象")
                
    except Exception as e:
        print(f"\nLLM 调用失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm_call()
