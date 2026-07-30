#!/usr/bin/env python3
"""快速检查 IMA 知识库状态和配额。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv()

from hermes_kb.ima_sync import IMAAPIError, IMAConfigError, list_knowledge_bases


def main() -> int:
    try:
        kbs = list_knowledge_bases(limit=20)
        print(f"Found {len(kbs)} knowledge bases:")
        for kb in kbs:
            name = kb.get("kb_name", "?")
            kid = kb.get("kb_id", "?")
            count = kb.get("content_count", "?")
            print(f"  - {name} (id={kid[:20]}...) count={count}")
    except IMAConfigError as e:
        print(f"Config Error: {e}")
        return 1
    except IMAAPIError as e:
        print(f"API Error: {e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
