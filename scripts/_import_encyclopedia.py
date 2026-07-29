"""临时脚本：导入百科种子数据并验证。"""
from dotenv import load_dotenv

load_dotenv()

from hermes_kb.seed import seed_encyclopedia

result = seed_encyclopedia()
print(f"Seeded: {result['seeded']}")
print(f"Skipped: {result['skipped']}")
print(f"Failed: {result['failed']}")
for item in result["items"]:
    title = item.get("title", "unknown")
    status = item.get("status", "unknown")
    print(f"  - {title}: {status}")
