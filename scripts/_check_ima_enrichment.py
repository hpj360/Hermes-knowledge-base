"""检查 IMA 文档富化匹配情况。

匹配口径（与 _enrich_ima_content._enrich_content 一致）：
  1. __OLD 后缀文档 → 标记 hidden，跳过富化
  2. 英文 slug → 新品类知识库（spirit/beer/cocktail/sake/liqueur/fortified/sparkling/process）
  3. 英文 slug → 复用既有中文标题知识库（wine_grape/wine_region/wine_wine/cider_fruit_wine）
  4. 中文标题直接匹配既有知识库
  5. 通用富化兜底（含酒类关键词 → 酒类知识；否则 → 行业资料）

匹配率 = (专项匹配 + 酒类知识) / (非 __OLD 文档数)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Document

from _enrich_ima_content import (
    _ALCOHOL_KEYWORDS,
    _FRUIT_WINE_PROFILES,
    _GRAPE_PROFILES,
    _OTHER_PROFILES,
    _REGION_PROFILES,
    _SLUG_PROFILES,
    _SLUG_TO_CHINESE,
    _WINE_TYPE_PROFILES,
    _lookup_chinese_profile,
)

# 既有中文标题知识库 → 类别标签
_CHINESE_KBS = (
    (_GRAPE_PROFILES, "葡萄品种"),
    (_REGION_PROFILES, "葡萄酒产区"),
    (_WINE_TYPE_PROFILES, "葡萄酒类型"),
    (_FRUIT_WINE_PROFILES, "果酒"),
    (_OTHER_PROFILES, "特色酒"),
)


def _classify(title: str) -> str:
    """返回文档富化后的类别标签（与 _enrich_content 的分派一致）。"""
    if title.endswith("__OLD"):
        return "__OLD(隐藏)"
    if title in _SLUG_PROFILES:
        return _SLUG_PROFILES[title][0]
    if title in _SLUG_TO_CHINESE:
        _, label = _lookup_chinese_profile(_SLUG_TO_CHINESE[title])
        if label:
            return label
    for kb, label in _CHINESE_KBS:
        if title in kb:
            return label
    # 通用富化
    if any(kw in title for kw in _ALCOHOL_KEYWORDS):
        return "酒类知识"
    return "行业资料"


def main() -> None:
    with get_session() as s:
        docs = s.exec(select(Document).where(Document.source == "ima")).all()

    total = len(docs)
    print(f"Total IMA docs: {total}")

    old_hidden = 0
    specific = 0
    alcohol_kw = 0
    pure_generic = 0
    by_category: dict[str, int] = {}
    generic_titles: list[str] = []

    for d in docs:
        title = d.title or ""
        label = _classify(title)
        by_category[label] = by_category.get(label, 0) + 1

        if label == "__OLD(隐藏)":
            old_hidden += 1
        elif label == "行业资料":
            pure_generic += 1
            generic_titles.append(title)
        elif label == "酒类知识":
            alcohol_kw += 1
        else:
            specific += 1

    non_old = total - old_hidden
    matched = specific + alcohol_kw
    match_rate = (matched / non_old * 100) if non_old else 0.0

    print(f"  __OLD(隐藏): {old_hidden}")
    print(f"  非 __OLD 文档: {non_old}")
    print()
    print("富化匹配统计（按类别）:")
    for label in sorted(by_category.keys()):
        print(f"  {label}: {by_category[label]}")
    print()
    print(f"专项匹配: {specific}")
    print(f"酒类知识(通用): {alcohol_kw}")
    print(f"未匹配(行业资料): {pure_generic}")
    print()
    print(f"匹配率 = (专项 + 酒类知识) / 非__OLD = {matched}/{non_old} = {match_rate:.1f}%")

    # 显示专项匹配文档示例
    print("\n专项匹配文档示例:")
    shown = 0
    for d in docs:
        title = d.title or ""
        label = _classify(title)
        if label not in ("__OLD(隐藏)", "酒类知识", "行业资料"):
            print(f"  - [{label}] {title}")
            shown += 1
            if shown >= 8:
                break

    # 显示未匹配文档标题样本（前 25 个）
    print(f"\n未匹配(行业资料)文档标题样本（共 {pure_generic}，前 25 个）:")
    for t in generic_titles[:25]:
        print(f"  - {t}")


if __name__ == "__main__":
    main()
