"""临时脚本：删除旧百科文档并按新分片策略重新导入。"""
from dotenv import load_dotenv

load_dotenv()

from sqlmodel import select

from hermes_kb.database import get_session
from hermes_kb.models import Chunk, Document, QueryLog
from hermes_kb.seed import seed_encyclopedia


def reimport_encyclopedia() -> None:
    """删除旧百科文档并重新导入。"""
    with get_session() as session:
        # 查找所有百科文档
        enc_docs = session.exec(
            select(Document).where(Document.category == "encyclopedia")
        ).all()
        print(f"Found {len(enc_docs)} encyclopedia docs to delete")

        # 删除关联的 chunks（含 FTS 触发器自动清理）
        for doc in enc_docs:
            # 删除 chunks
            chunks = session.exec(
                select(Chunk).where(Chunk.doc_id == doc.doc_id)
            ).all()
            for chunk in chunks:
                session.delete(chunk)
            # 删除文档
            session.delete(doc)
        session.commit()
        print(f"Deleted {len(enc_docs)} encyclopedia docs + their chunks")

    # 重新导入（使用新的分片策略 800/120）
    print("\nRe-importing with new chunk strategy (800/120)...")
    result = seed_encyclopedia()
    print(f"Seeded: {result['seeded']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Failed: {result['failed']}")

    # 验证新分片
    with get_session() as session:
        enc_docs = session.exec(
            select(Document).where(Document.category == "encyclopedia")
        ).all()
        total_chunks = sum(d.chunk_count for d in enc_docs)
        print(f"\nVerification:")
        print(f"  Encyclopedia docs: {len(enc_docs)}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  Avg chunks/doc: {total_chunks / len(enc_docs) if enc_docs else 0:.1f}")
        for d in enc_docs[:5]:
            print(f"  - {d.title}: {d.chunk_count} chunks")


if __name__ == "__main__":
    reimport_encyclopedia()
