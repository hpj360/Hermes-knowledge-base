"""LLM / parser / substitutes 模块测试补强。

覆盖：
- llm.py: OpenAICompatBackend chat/chat_stream/降级、LLMClient 后端选择/异常降级
- parser.py: parse_file 各种格式/不存在/默认文本、_parse_pdf 异常、chunk 滑窗
- substitutes.py: add_user_substitute 空值/重复/IntegrityError、remove、list_all
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ===========================================================================
# llm.py
# ===========================================================================
class TestLLMOpenAICompatBackend:
    """OpenAI 兼容后端。"""

    def test_chat_success(self, monkeypatch):
        """chat 成功返回带 usage 的响应。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import OpenAICompatBackend, LLMResponse

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
            llm_model="gpt-4",
        )

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "choices": [{"message": {"content": "Hello"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                }

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, *args, **kwargs):
                return FakeResponse()

        import httpx

        monkeypatch.setattr(httpx, "Client", FakeClient)
        backend = OpenAICompatBackend()
        resp = backend.chat([{"role": "user", "content": "hi"}])
        assert isinstance(resp, LLMResponse)
        assert resp.content == "Hello"
        assert resp.model == "gpt-4"
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 5

    def test_chat_no_usage_field(self, monkeypatch):
        """响应无 usage 字段时 token 数为 0。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import OpenAICompatBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
            llm_model="gpt-4",
        )

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "Hi"}}]}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, *args, **kwargs):
                return FakeResponse()

        import httpx

        monkeypatch.setattr(httpx, "Client", FakeClient)
        backend = OpenAICompatBackend()
        resp = backend.chat([{"role": "user", "content": "hi"}])
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0

    @pytest.mark.asyncio
    async def test_chat_stream_success(self, monkeypatch):
        """流式 chat 成功解析 SSE 帧。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import OpenAICompatBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
            llm_model="gpt-4",
        )

        # 模拟 SSE 流：3 个 data 帧 + [DONE]
        sse_lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            'data: {"choices":[]}',  # usage 帧，choices 空
            'data: [DONE]',
        ]

        class FakeStreamResponse:
            def raise_for_status(self):
                pass

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

        class FakeStreamContext:
            async def __aenter__(self):
                return FakeStreamResponse()

            async def __aexit__(self, *args):
                return False

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def stream(self, *args, **kwargs):
                return FakeStreamContext()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
        backend = OpenAICompatBackend()
        chunks = []
        async for chunk in backend.chat_stream([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert "Hello" in "".join(chunks)
        assert "world" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_chat_stream_invalid_json_skipped(self, monkeypatch):
        """SSE 行 JSON 解析失败被跳过。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import OpenAICompatBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
            llm_model="gpt-4",
        )

        sse_lines = [
            "data: not-json",
            'data: {"choices":[{"delta":{"content":"OK"}}]}',
            "data: [DONE]",
        ]

        class FakeStreamResponse:
            def raise_for_status(self):
                pass

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

        class FakeStreamContext:
            async def __aenter__(self):
                return FakeStreamResponse()

            async def __aexit__(self, *args):
                return False

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def stream(self, *args, **kwargs):
                return FakeStreamContext()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
        backend = OpenAICompatBackend()
        chunks = []
        async for chunk in backend.chat_stream([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert "OK" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_chat_stream_empty_line_skipped(self, monkeypatch):
        """空行和非 data: 开头的行被跳过。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import OpenAICompatBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
            llm_model="gpt-4",
        )

        sse_lines = [
            "",
            ": comment",
            'data: {"choices":[{"delta":{"content":"X"}}]}',
            "data: [DONE]",
        ]

        class FakeStreamResponse:
            def raise_for_status(self):
                pass

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

        class FakeStreamContext:
            async def __aenter__(self):
                return FakeStreamResponse()

            async def __aexit__(self, *args):
                return False

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def stream(self, *args, **kwargs):
                return FakeStreamContext()

        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
        backend = OpenAICompatBackend()
        chunks = []
        async for chunk in backend.chat_stream([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert "".join(chunks) == "X"


class TestLLMClient:
    """LLMClient 后端选择与降级。"""

    def test_select_mock_when_provider_mock(self):
        """provider=mock → MockLLMBackend。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import LLMClient, MockLLMBackend

        override_settings(llm_provider="mock")
        client = LLMClient()
        assert isinstance(client._backend, MockLLMBackend)

    def test_select_openai_when_available(self):
        """provider=openai 且 api_key 非空 → OpenAICompatBackend。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import LLMClient, OpenAICompatBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
        )
        client = LLMClient()
        assert isinstance(client._backend, OpenAICompatBackend)

    def test_select_mock_when_openai_no_key(self):
        """provider=openai 但 api_key 空 → MockLLMBackend。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import LLMClient, MockLLMBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="",
        )
        client = LLMClient()
        assert isinstance(client._backend, MockLLMBackend)

    def test_chat_exception_falls_back_to_mock(self, monkeypatch):
        """后端异常时降级 Mock。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import LLMClient, OpenAICompatBackend, MockLLMBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
        )

        def failing_chat(self, messages):
            raise RuntimeError("API 故障")

        monkeypatch.setattr(OpenAICompatBackend, "chat", failing_chat)
        client = LLMClient()
        # 不应抛错，降级 Mock
        resp = client.chat([{"role": "user", "content": "hi"}])
        # Mock 后端返回非空内容
        assert resp.content

    @pytest.mark.asyncio
    async def test_chat_stream_exception_falls_back_to_mock(self, monkeypatch):
        """流式后端异常时降级 Mock 流式。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import LLMClient, OpenAICompatBackend

        override_settings(
            llm_provider="openai",
            llm_api_key="test-key",
        )

        async def failing_stream(self, messages):
            raise RuntimeError("stream 故障")
            yield  # noqa: unreachable - 让函数成为 async generator

        monkeypatch.setattr(OpenAICompatBackend, "chat_stream", failing_stream)
        client = LLMClient()
        chunks = []
        async for chunk in client.chat_stream([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        # 降级 Mock 应有内容
        assert len(chunks) > 0

    def test_backend_name(self):
        """backend_name 返回类名。"""
        from hermes_kb.config import override_settings
        from hermes_kb.llm import LLMClient

        override_settings(llm_provider="mock")
        client = LLMClient()
        assert client.backend_name == "MockLLMBackend"


class TestMockLLMBackend:
    """MockLLMBackend 组合逻辑。"""

    def test_compose_no_retrieval(self):
        """无 untrusted_retrieval 标签 → 默认提示。"""
        from hermes_kb.llm import MockLLMBackend

        backend = MockLLMBackend()
        resp = backend.chat([{"role": "user", "content": "hi"}])
        assert "暂无相关信息" in resp.content

    def test_compose_with_retrieval(self):
        """含 untrusted_retrieval 标签 → 拼装检索片段。"""
        from hermes_kb.llm import MockLLMBackend

        backend = MockLLMBackend()
        sys_msg = (
            '<untrusted_retrieval id="1">[1] 金酒是杜松子风味的烈酒</untrusted_retrieval>\n'
            '<untrusted_retrieval id="2">[2] 伏特加是纯净的烈酒</untrusted_retrieval>'
        )
        resp = backend.chat([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": "什么是金酒"},
        ])
        assert "金酒" in resp.content
        assert "杜松子" in resp.content

    def test_compose_truncates_long_retrieval(self):
        """检索片段过长被截断。"""
        from hermes_kb.llm import MockLLMBackend

        backend = MockLLMBackend()
        long_text = "A" * 500
        sys_msg = f'<untrusted_retrieval id="1">[1] {long_text}</untrusted_retrieval>'
        resp = backend.chat([{"role": "system", "content": sys_msg}])
        # 截断后应含 …
        assert "…" in resp.content

    @pytest.mark.asyncio
    async def test_chat_stream_yields_chunks(self):
        """Mock 流式按字符切片 yield。"""
        from hermes_kb.llm import MockLLMBackend

        backend = MockLLMBackend()
        sys_msg = '<untrusted_retrieval id="1">[1] 测试内容</untrusted_retrieval>'
        chunks = []
        async for chunk in backend.chat_stream([
            {"role": "system", "content": sys_msg},
        ]):
            chunks.append(chunk)
        # 应有多个 chunk
        assert len(chunks) > 1
        assert "测试" in "".join(chunks)


# ===========================================================================
# parser.py
# ===========================================================================
class TestDocumentParser:
    """文档解析器。"""

    def test_parse_file_not_exists(self, tmp_path):
        """文件不存在 → FileNotFoundError。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file(tmp_path / "nonexistent.txt")

    def test_parse_file_txt(self, tmp_path):
        """解析 txt 文件。"""
        from hermes_kb.parser import DocumentParser

        p = tmp_path / "test.txt"
        p.write_text("纯文本内容", encoding="utf-8")

        parser = DocumentParser()
        doc = parser.parse_file(p)
        assert doc.title == "test"
        assert doc.content == "纯文本内容"
        assert doc.file_type == "txt"

    def test_parse_file_md(self, tmp_path):
        """解析 md 文件（剥离标记）。"""
        from hermes_kb.parser import DocumentParser

        p = tmp_path / "test.md"
        p.write_text("# 标题\n\n**粗体** *斜体* `code`", encoding="utf-8")

        parser = DocumentParser()
        doc = parser.parse_file(p)
        assert doc.file_type == "md"
        # 标题标记被剥离
        assert "#" not in doc.content or "#" in "纯文本"
        assert "粗体" in doc.content
        assert "斜体" in doc.content

    def test_parse_file_markdown_suffix(self, tmp_path):
        """`.markdown` 后缀也走 md 解析。"""
        from hermes_kb.parser import DocumentParser

        p = tmp_path / "test.markdown"
        p.write_text("# 标题", encoding="utf-8")

        parser = DocumentParser()
        doc = parser.parse_file(p)
        assert doc.file_type == "md"

    def test_parse_file_unknown_suffix_defaults_txt(self, tmp_path):
        """未知后缀默认按 txt 处理。"""
        from hermes_kb.parser import DocumentParser

        p = tmp_path / "test.log"
        p.write_text("日志内容", encoding="utf-8")

        parser = DocumentParser()
        doc = parser.parse_file(p)
        assert doc.file_type == "txt"
        assert doc.content == "日志内容"

    def test_parse_text_basic(self):
        """parse_text 不传 title 使用 'untitled'。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        doc = parser.parse_text("内容", file_type="txt")
        assert doc.title == "untitled"
        assert doc.content == "内容"

    def test_parse_text_with_title(self):
        """parse_text 传 title 使用传入值。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        doc = parser.parse_text("内容", file_type="txt", title="自定义")
        assert doc.title == "自定义"

    def test_parse_text_md_strips_markdown(self):
        """parse_text md 类型剥离标记。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        doc = parser.parse_text("# 标题\n\n[链接](http://x)", file_type="md")
        assert "#" not in doc.content or "#" in "纯文本"
        assert "链接" in doc.content
        assert "http" not in doc.content

    def test_parse_pdf_import_error(self, monkeypatch, tmp_path):
        """pypdf 未安装 → RuntimeError。"""
        from hermes_kb.parser import DocumentParser

        p = tmp_path / "fake.pdf"
        p.write_bytes(b"fake pdf")

        # 模拟 pypdf 不可用
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("no pypdf")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        parser = DocumentParser()
        with pytest.raises(RuntimeError, match="pypdf"):
            parser.parse_file(p)

    def test_chunk_empty_text(self):
        """空文本不分片。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        assert parser.chunk("") == []
        assert parser.chunk("   ") == []
        assert parser.chunk("\n\n\n") == []

    def test_chunk_short_text_single_chunk(self):
        """短文本单个 chunk。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        chunks = parser.chunk("短文本", chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0][2] == "短文本"

    def test_chunk_long_text_sliding_window(self):
        """长文本走滑窗分片。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        text = "A" * 200
        chunks = parser.chunk(text, chunk_size=50, overlap=10)
        assert len(chunks) > 1
        # 每个 chunk 不超 chunk_size
        for _, _, chunk_text in chunks:
            assert len(chunk_text) <= 50

    def test_chunk_paragraph_split(self):
        """按段落切分。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        text = "段落一\n\n段落二\n\n段落三"
        chunks = parser.chunk(text, chunk_size=100)
        assert len(chunks) >= 1
        # 段落内容都在 chunks 中
        all_text = "".join(c[2] for c in chunks)
        assert "段落一" in all_text
        assert "段落三" in all_text

    def test_chunk_overlap_clamped(self):
        """overlap 超过 chunk_size/2 被钳制。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        text = "A" * 200
        # overlap=1000 应被钳到 chunk_size//2 = 25
        chunks = parser.chunk(text, chunk_size=50, overlap=1000)
        assert len(chunks) > 1

    def test_chunk_size_clamped_to_min(self):
        """chunk_size < 50 被钳到 50。"""
        from hermes_kb.parser import DocumentParser

        parser = DocumentParser()
        text = "A" * 100
        chunks = parser.chunk(text, chunk_size=10, overlap=0)
        # chunk_size=10 → 实际 50
        for _, _, chunk_text in chunks:
            assert len(chunk_text) <= 50

    def test_strip_markdown_comprehensive(self):
        """_strip_markdown 处理各种标记。"""
        from hermes_kb.parser import DocumentParser

        text = """# H1
## H2
- 列表项
1. 有序列表
> 引用
**粗体** *斜体* __下划线__
`行内代码`
```
代码块
```
![图片](url)
[链接](url)
---
"""
        result = DocumentParser._strip_markdown(text)
        assert "H1" in result
        assert "H2" in result
        assert "列表项" in result
        assert "有序列表" in result
        assert "引用" in result
        assert "粗体" in result
        assert "斜体" in result
        assert "下划线" in result
        assert "行内代码" in result
        # 代码块被移除
        assert "代码块" not in result
        # 图片保留 alt 文本
        assert "图片" in result
        # 链接保留文本
        assert "链接" in result
        # url 不应出现
        assert "url" not in result


# ===========================================================================
# substitutes.py
# ===========================================================================
class TestSubstitutesAddRemove:
    """替代关系增删。"""

    def test_add_user_substitute_empty_canonical_noop(self, client):
        """canonical 为空 → 静默返回。"""
        from hermes_kb.substitutes import add_user_substitute, list_all_substitutes

        before = list_all_substitutes()
        add_user_substitute("", "替代")
        after = list_all_substitutes()
        assert before == after

    def test_add_user_substitute_empty_substitute_noop(self, client):
        """substitute 为空 → 静默返回。"""
        from hermes_kb.substitutes import add_user_substitute, list_all_substitutes

        before = list_all_substitutes()
        add_user_substitute("金酒", "")
        after = list_all_substitutes()
        assert before == after

    def test_add_user_substitute_whitespace_only_noop(self, client):
        """仅空白字符 → 静默返回。"""
        from hermes_kb.substitutes import add_user_substitute, list_all_substitutes

        before = list_all_substitutes()
        add_user_substitute("   ", "   ")
        after = list_all_substitutes()
        assert before == after

    def test_add_user_substitute_strips_whitespace(self, client):
        """添加时 strip 空白。"""
        from hermes_kb.substitutes import add_user_substitute, get_substitutes

        add_user_substitute("  金酒  ", "  伏特加  ")
        subs = get_substitutes("金酒")
        assert "伏特加" in subs

    def test_add_user_substitute_duplicate_no_error(self, client):
        """重复添加不报错。"""
        from hermes_kb.substitutes import add_user_substitute

        add_user_substitute("金酒", "测试替代")
        # 第二次重复添加
        add_user_substitute("金酒", "测试替代")
        # 不应抛异常

    def test_add_user_substitute_integrity_error_handled(self, client, monkeypatch):
        """IntegrityError（并发）被捕获并 rollback。"""
        from sqlalchemy.exc import IntegrityError
        from hermes_kb import substitutes
        from hermes_kb.substitutes import add_user_substitute

        class FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def exec(self, *args, **kwargs):
                return MagicMock(first=lambda: None)

            def add(self, *args):
                pass

            def commit(self):
                raise IntegrityError("stmt", "params", Exception("orig"))

            def rollback(self):
                pass

        monkeypatch.setattr(substitutes, "get_session", lambda: FakeSession())
        # 不应抛异常
        add_user_substitute("金酒", "测试")

    def test_remove_user_substitute(self, client):
        """删除用户自定义替代。"""
        from hermes_kb.substitutes import (
            add_user_substitute,
            get_substitutes,
            remove_user_substitute,
        )

        add_user_substitute("金酒", "临时替代")
        assert "临时替代" in get_substitutes("金酒")

        remove_user_substitute("金酒", "临时替代")
        assert "临时替代" not in get_substitutes("金酒")

    def test_remove_user_substitute_preserves_preset(self, client):
        """删除用户自定义不影响预置关系。"""
        from hermes_kb.substitutes import (
            get_substitutes,
            remove_user_substitute,
        )

        # 金酒预置有 "伏特加"
        assert "伏特加" in get_substitutes("金酒")
        # 尝试删除（无用户自定义记录，不报错）
        remove_user_substitute("金酒", "伏特加")
        # 预置关系仍在
        assert "伏特加" in get_substitutes("金酒")

    def test_remove_nonexistent_no_error(self, client):
        """删除不存在的记录不报错。"""
        from hermes_kb.substitutes import remove_user_substitute

        remove_user_substitute("不存在的", "不存在的替代")
        # 不应抛异常


class TestSubstitutesListAll:
    """list_all_substitutes 覆盖率。"""

    def test_list_all_includes_preset(self, client):
        """包含预置关系。"""
        from hermes_kb.substitutes import list_all_substitutes

        result = list_all_substitutes()
        assert "金酒" in result
        assert "伏特加" in result["金酒"]

    def test_list_all_includes_user_custom(self, client):
        """包含用户自定义。"""
        from hermes_kb.substitutes import (
            add_user_substitute,
            list_all_substitutes,
        )

        add_user_substitute("测试材料", "测试替代")
        result = list_all_substitutes()
        assert "测试材料" in result
        assert "测试替代" in result["测试材料"]

    def test_list_all_sorted(self, client):
        """替代列表已排序。"""
        from hermes_kb.substitutes import list_all_substitutes

        result = list_all_substitutes()
        for canon, subs in result.items():
            assert subs == sorted(subs)

    def test_list_all_merges_preset_and_user(self, client):
        """预置和用户自定义合并去重。"""
        from hermes_kb.substitutes import (
            add_user_substitute,
            list_all_substitutes,
        )

        # 金酒预置有 "伏特加"，添加用户自定义 "杜松子酒"（已存在预置）
        add_user_substitute("金酒", "伏特加")  # 重复
        result = list_all_substitutes()
        # 去重：伏特加 只出现一次
        assert result["金酒"].count("伏特加") == 1
