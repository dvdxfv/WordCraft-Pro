#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manual LLM probe script (not CI pytest)."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from llm.client import ChatMessage, LLMConfig, create_llm_client


def main() -> int:
    config = LLMConfig.from_yaml("config.yaml")
    client = create_llm_client(config)
    if not client.is_available():
        print("LLM client unavailable.")
        return 0

    prompt = (
        "你是中文文档错别字检测专家。请返回 JSON: "
        '{"issues":[{"text":"错误片段","suggestion":"建议","reason":"原因","confidence":0.9}]}. '
        "无问题时返回 {\"issues\":[]}。文本：这个项目的帐单需要按装新的软件系统。"
    )
    out = client.chat([ChatMessage(role="user", content=prompt)], temperature=0.1)
    print(out[:600])
    try:
        data = json.loads(out.strip())
        print(f"issues={len(data.get('issues', []))}")
    except Exception:
        print("response is not strict json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

