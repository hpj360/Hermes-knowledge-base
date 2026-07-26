"""parser.py + query_rewriter.py 覆盖率补强测试（阶段6 批次1）。

覆盖目标：
- parser.py: _parse_pdf 主体 / pdf 文件解析路径 / chunk 边界（空 buffer / idx 回退）
- query_rewriter.py: 空 query / LLM 改写长度异常 / _llm_rewrite 主体
"""
from __future__ import annotations

import pytest


# ============================================================
# parser.py 覆盖率补强
# ============================================================


def test_parse_pdf_file_with_mocked_reader(tmp_path, monkeypatch):
    """parse_file 对 .pdf 后缀走 _parse_pdf，返回提取的文本。"""
    from hermes_kb.parser import DocumentParser

    p = tmp_path / "sample.pdf"
    p.write_bytes(b"%PDF-1.4 fake")  # 占位内容，实际由 mock reader 解析

    # mock pypdf.PdfReader，返回两页文本
    class _FakePage:
        def __init__(self, text: str):
            self._t = text

        def extract_text(self) -> str:
            return self._t

    class _FakeReader:
        def __init__(self, path):
            self.pages = [_FakePage("第一页内容"), _FakePage("第二页内容")]

    # 注入到 sys.modules，使 `from pypdf import PdfReader` 命中 mock
    import sys
    import types

    fake_module = types.ModuleType("pypdf")
    fake_module.PdfReader = _FakeReader
    monkeypatch.setitem(sys.modules, "pypdf", fake_module)

    parser = DocumentParser()
    doc = parser.parse_file(p)
    assert doc.file_type == "pdf"
    assert "第一页内容" in doc.content
    assert "第二页内容" in doc.content
    # 两页之间用双换行连接
    assert "\n\n" in doc.content


def test_parse_pdf_page_extract_text_failure_skipped(tmp_path, monkeypatch):
    """_parse_pdf 中 page.extract_text() 抛异常时跳过该页（不中断）。"""
    from hermes_kb.parser import DocumentParser

    p = tmp_path / "broken.pdf"
    p.write_bytes(b"%PDF-1.4 fake")

    class _BadPage:
        def extract_text(self):
            raise RuntimeError("page corrupt")

    class _GoodPage:
        def extract_text(self):
            return "正常页"

    class _FakeReader:
        def __init__(self, path):
            self.pages = [_BadPage(), _GoodPage()]

    import sys
    import types

    fake_module = types.ModuleType("pypdf")
    fake_module.PdfReader = _FakeReader
    monkeypatch.setitem(sys.modules, "pypdf", fake_module)

    parser = DocumentParser()
    doc = parser.parse_file(p)
    # 坏页被跳过，只保留正常页
    assert "正常页" in doc.content
    assert doc.file_type == "pdf"


def test_parse_pdf_empty_pages_produce_empty_string(tmp_path, monkeypatch):
    """_parse_pdf 所有页 extract_text 返回空 → 结果为空字符串。"""
    from hermes_kb.parser import DocumentParser

    p = tmp_path / "empty.pdf"
    p.write_bytes(b"%PDF-1.4 fake")

    class _EmptyPage:
        def extract_text(self):
            return ""

    class _FakeReader:
        def __init__(self, path):
            self.pages = [_EmptyPage(), _EmptyPage()]

    import sys
    import types

    fake_module = types.ModuleType("pypdf")
    fake_module.PdfReader = _FakeReader
    monkeypatch.setitem(sys.modules, "pypdf", fake_module)

    parser = DocumentParser()
    doc = parser.parse_file(p)
    assert doc.content == ""
    assert doc.file_type == "pdf"


def test_chunk_whitespace_only_buffer_skipped():
    """chunk 中 flush_buffer 遇到仅含空白的 buffer 时跳过（不产出空 chunk）。"""
    from hermes_kb.parser import DocumentParser

    parser = DocumentParser()
    # 构造段落间有大量空白，使 buffer 累积为纯空白
    text = "段落一\n\n   \n\n段落二"
    chunks = parser.chunk(text, chunk_size=100)
    # 至少有有效 chunk
    assert len(chunks) >= 1
    all_text = "".join(c[2] for c in chunks)
    assert "段落一" in all_text
    assert "段落二" in all_text


def test_chunk_paragraph_not_found_from_cursor():
    """chunk 中 text.find(para, cursor) 返回 -1 时回退到 cursor。"""
    from hermes_kb.parser import DocumentParser

    parser = DocumentParser()
    # 构造一个段落无法在 cursor 之后找到的场景：
    # 段落被 strip 后与原文不完全一致（前后空白差异）
    text = "  前导空白段落  \n\n  第二段  "
    chunks = parser.chunk(text, chunk_size=100)
    # 应正常产出 chunk，不抛异常
    assert len(chunks) >= 1


def test_chunk_buffer_flush_when_exceeding_size():
    """chunk 中 buffer + 新段落超限时先 flush_buffer 再开新 buffer。"""
    from hermes_kb.parser import DocumentParser

    parser = DocumentParser()
    # 构造多个段落，使 buffer 累积超过 chunk_size + overlap 触发 flush
    para1 = "A" * 30
    para2 = "B" * 30
    para3 = "C" * 30
    text = f"{para1}\n\n{para2}\n\n{para3}"
    chunks = parser.chunk(text, chunk_size=50, overlap=10)
    # 应产出多个 chunk
    assert len(chunks) >= 2


def test_parse_file_not_found_raises():
    """parse_file 文件不存在 → FileNotFoundError。"""
    from hermes_kb.parser import DocumentParser

    parser = DocumentParser()
    with pytest.raises(FileNotFoundError, match="文件不存在"):
        parser.parse_file("/nonexistent/path/to/file.txt")


# ============================================================
# query_rewriter.py 覆盖率补强
# ============================================================


def test_rewriter_empty_query_returns_empty():
    """rewrite 对空/空白 query 直接返回（不走启发式也不走 LLM）。"""
    from hermes_kb.query_rewriter import QueryRewriter

    rw = QueryRewriter()
    assert rw.rewrite("") == ""
    assert rw.rewrite("   ") == "   "


def test_rewriter_disabled_uses_heuristic(monkeypatch):
    """rewriter 未启用（LLM 不可用）时走启发式改写。"""
    from hermes_kb import query_rewriter as qr_mod

    monkeypatch.setattr(qr_mod.QueryRewriter, "__init__", lambda self, llm_client=None: None)
    rw = qr_mod.QueryRewriter()
    rw.enabled = False
    # 启发式应补充同义词
    result = rw.rewrite("金酒什么味道")
    assert "金酒" in result
    assert "杜松子" in result


def test_rewriter_llm_returns_too_long_falls_back_to_original(monkeypatch):
    """LLM 改写结果长度异常（超过 max(50, len(query)*5)）→ 回退原 query。"""
    from hermes_kb import query_rewriter as qr_mod

    monkeypatch.setattr(qr_mod.QueryRewriter, "__init__", lambda self, llm_client=None: None)
    rw = qr_mod.QueryRewriter()
    rw.enabled = True

    # mock _llm_rewrite 返回超长结果
    rw._llm_rewrite = lambda q: "x" * 1000  # 远超 len(query)*5

    result = rw.rewrite("短query")
    # 长度异常，回退原 query
    assert result == "短query"


def test_rewriter_llm_returns_valid_result(monkeypatch):
    """LLM 改写结果长度合法 → 使用改写结果。"""
    from hermes_kb import query_rewriter as qr_mod

    monkeypatch.setattr(qr_mod.QueryRewriter, "__init__", lambda self, llm_client=None: None)
    rw = qr_mod.QueryRewriter()
    rw.enabled = True

    rw._llm_rewrite = lambda q: "金酒 杜松子 风味"

    result = rw.rewrite("金酒啥味")
    assert result == "金酒 杜松子 风味"


def test_rewriter_llm_timeout_falls_back_to_heuristic(monkeypatch):
    """LLM 改写超时 → 回退启发式。"""
    from hermes_kb import query_rewriter as qr_mod

    monkeypatch.setattr(qr_mod.QueryRewriter, "__init__", lambda self, llm_client=None: None)
    rw = qr_mod.QueryRewriter()
    rw.enabled = True

    def slow_llm(query):
        import time
        time.sleep(10)  # 模拟超时
        return "should not reach"

    rw._llm_rewrite = slow_llm

    # 超时应回退启发式（包含同义词）
    result = rw.rewrite("威士忌")
    assert "威士忌" in result
    assert "谷物" in result or "橡木桶" in result


def test_rewriter_llm_exception_falls_back_to_heuristic(monkeypatch):
    """LLM 改写抛异常 → 回退启发式。"""
    from hermes_kb import query_rewriter as qr_mod

    monkeypatch.setattr(qr_mod.QueryRewriter, "__init__", lambda self, llm_client=None: None)
    rw = qr_mod.QueryRewriter()
    rw.enabled = True

    def boom(query):
        raise RuntimeError("LLM service down")

    rw._llm_rewrite = boom

    result = rw.rewrite("茅台")
    assert "茅台" in result
    assert "酱香" in result


def test_llm_rewrite_calls_llm_chat():
    """_llm_rewrite 调用 llm.chat 并返回 content。"""
    from hermes_kb import query_rewriter as qr_mod

    class _FakeLLM:
        def __init__(self):
            self.called = False

        def chat(self, messages):
            self.called = True
            # 返回带 content 的对象
            class _Resp:
                content = "  改写结果  "
            return _Resp()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(qr_mod.QueryRewriter, "__init__", lambda self, llm_client=None: None)
    rw = qr_mod.QueryRewriter()
    rw.llm = _FakeLLM()

    result = rw._llm_rewrite("test query")
    assert rw.llm.called is True
    assert result == "改写结果"  # .strip() 已应用
    monkeypatch.undo()


def test_heuristic_rewrite_no_synonym_match():
    """_heuristic_rewrite 对无同义词匹配的 query 仅去语气词。"""
    from hermes_kb.query_rewriter import _heuristic_rewrite

    result = _heuristic_rewrite("随便的问题呢")
    assert "随便" in result
    assert "呢" not in result


def test_heuristic_rewrite_empty_query():
    """_heuristic_rewrite 对空 query 原样返回。"""
    from hermes_kb.query_rewriter import _heuristic_rewrite

    assert _heuristic_rewrite("") == ""
    assert _heuristic_rewrite(None) is None
