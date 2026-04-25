#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Startup and lightweight API benchmark (manual script)."""

import logging
import os
import sys
import time
from unittest.mock import Mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from app import Api

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")


def main() -> int:
    print("\n" + "=" * 70)
    print("WordCraft Pro 启动和性能测试")
    print("=" * 70)

    start = time.time()
    api = Api(supabase_enabled=True)
    init_time = time.time() - start
    print(f"\nApi 初始化耗时: {init_time*1000:.2f}ms")

    api.set_window(Mock())
    ops = [("getSystemInfo", [], "获取系统信息"), ("getUserTemplates", [], "获取用户模板"), ("getTokenUsage", [], "获取 Token 用量")]
    total = 0.0
    for method_name, args, desc in ops:
        fn = getattr(api, method_name)
        st = time.time()
        fn(*args)
        elapsed = time.time() - st
        total += elapsed
        print(f"{desc:20} -> {elapsed*1000:6.2f}ms")

    print(f"\n平均响应: {(total/len(ops))*1000:.2f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

