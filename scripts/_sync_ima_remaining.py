#!/usr/bin/env python3
"""同步 IMA 知识库剩余内容。

配额重置后运行，尝试同步未导入的 IMA 文档。
使用多关键词循环搜索最大化召回，自动去重。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv()

from hermes_kb.ima_sync import IMAAPIError, IMAConfigError, sync_knowledge_base


def main() -> int:
    # 尝试同步剩余内容，limit 设大一些以最大化召回
    # 注意：IMA API 有配额限制，单次运行可能无法全部同步
    try:
        result = sync_knowledge_base(
            query="",  # 空串触发多关键词循环搜索
            limit=1000,  # 上限设大，实际受 API 配额限制
            category="IMA资料",
        )
        print("=== 同步结果 ===")
        print(f"知识库 ID: {result['kb_id']}")
        print(f"已导入: {result['imported']}")
        print(f"已跳过（重复）: {result['skipped']}")
        print(f"失败: {result['failed']}")
        print(f"条目数: {len(result['items'])}")
        if result["imported"] > 0:
            print("\n新导入条目（前 20 条）:")
            for item in result["items"][:20]:
                if item.get("status") == "imported":
                    print(f"  + {item['title']}")
        if result["imported"] == 0 and result["skipped"] > 0:
            print("\n所有条目均已存在（完全同步）")
    except IMAConfigError as e:
        print(f"Config Error: {e}")
        return 1
    except IMAAPIError as e:
        print(f"API Error: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
