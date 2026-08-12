"""临时 IMA 同步脚本（带 dotenv 加载）。

优先同步个人知识库（订阅知识库受 code=220030 限制）。
"""
import json
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

from hermes_kb.ima_sync import IMAAPIError, IMAConfigError, sync_knowledge_base
from hermes_kb.rag import ImportService


def sync_kb(kb_id: str, kb_name: str, limit: int = 100, category: str = "IMA资料"):
    """同步单个知识库。"""
    print(f"\n{'='*60}")
    print(f"同步知识库: {kb_name} (limit={limit})")
    print(f"kb_id: {kb_id}")
    print(f"{'='*60}")

    importer = ImportService()
    try:
        result = sync_knowledge_base(
            query="",
            kb_id=kb_id,
            limit=limit,
            category=category,
            importer=importer,
        )
        summary = {k: v for k, v in result.items() if k != "items"}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        items = result.get("items", [])
        print(f"\n导入条目数: {len(items)}")
        for i, item in enumerate(items[:15]):
            title = item.get("title", "?")[:60]
            status = item.get("status", "?")
            print(f"  {i+1}. [{status}] {title}")
        return result
    except IMAConfigError as e:
        print(f"配置错误: {e}")
    except IMAAPIError as e:
        print(f"API 错误: {e}")
    except Exception as e:  # noqa: BLE001
        print(f"未知错误: {type(e).__name__}: {e}")
    return None


if __name__ == "__main__":
    # 优先同步个人知识库（订阅知识库受 code=220030 限制）
    # 喝酒的的信号AI: 722 条（最丰富）
    # AI知识库: 36 条
    # 微信用户的知识库: 2 条
    kbs = [
        ("LMil_59p1x4GoO9hff28qmr3aTPlATeEBPVIymjFbVQ=", "喝酒的的信号AI", 200),
        ("vau9Bw9VNIYY-ehw4jRHm8BYO9rxoNuDqSCmWL9SPHk=", "AI知识库", 50),
        ("OcOj0mgj84zaDnmNao4mqlZg1yrBB8cqPVoxVZ-YusA=", "微信用户的知识库", 10),
    ]

    results = {}
    for kb_id, kb_name, limit in kbs:
        result = sync_kb(kb_id, kb_name, limit=limit)
        if result:
            results[kb_name] = {
                "imported": result.get("imported", 0),
                "skipped": result.get("skipped", 0),
                "failed": result.get("failed", 0),
            }
        else:
            results[kb_name] = {"error": True}

    print(f"\n{'='*60}")
    print("同步汇总:")
    print(json.dumps(results, ensure_ascii=False, indent=2))
