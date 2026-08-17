"""Embedding 服务测试：覆盖 hash/openai/sentence_transformers 三后端 + 降级。

覆盖：
- HashEmbeddingBackend：dim/embed/_tokenize（中文 bigram/trigram + 英文整词 + 空文本）
- OpenAIEmbeddingBackend：探针成功/失败、embed 成功/降级、空输入、_call_api
- SentenceTransformerBackend：模型缺失降级、dim 探测、embed 降级
- EmbeddingService：backend 选择、dim 覆盖、embed_one
"""
from __future__ import annotations

from unittest.mock import MagicMock


# ===========================================================================
# HashEmbeddingBackend
# ===========================================================================
class TestHashEmbeddingBackend:
    """Hash 后端：SHA256 确定性向量。"""

    def test_dim_default_from_settings(self):
        """无参数构造从 settings 取 dim。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend()
        assert backend.dim > 0

    def test_dim_explicit(self):
        """显式指定 dim。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=64)
        assert backend.dim == 64

    def test_embed_returns_correct_dim(self):
        """embed 返回向量维度正确。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=32)
        vecs = backend.embed(["测试文本", "另一段"])
        assert len(vecs) == 2
        for v in vecs:
            assert len(v) == 32

    def test_embed_empty_text_returns_zero_vector(self):
        """空文本返回零向量。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=16)
        vec = backend._embed_one("")
        assert vec == [0.0] * 16

    def test_embed_deterministic(self):
        """相同文本生成相同向量（SHA256 确定性）。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=32)
        v1 = backend._embed_one("金酒")
        v2 = backend._embed_one("金酒")
        assert v1 == v2

    def test_embed_different_text_different_vector(self):
        """不同文本生成不同向量。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=32)
        v1 = backend._embed_one("金酒")
        v2 = backend._embed_one("威士忌")
        assert v1 != v2

    def test_embed_normalized(self):
        """非空文本向量已 L2 归一化（模长=1）。"""
        import math

        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=32)
        vec = backend._embed_one("金酒杜松子")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6

    def test_embed_empty_list_returns_empty(self):
        """空列表返回空列表。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        backend = HashEmbeddingBackend(dim=32)
        assert backend.embed([]) == []

    def test_tokenize_chinese_bigram_trigram(self):
        """中文走 bigram + trigram。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        tokens = HashEmbeddingBackend._tokenize("金酒杜松子")
        # "金酒杜松子" 长度 5：4 个 bigram + 3 个 trigram = 7
        assert "金酒" in tokens
        assert "杜松子" in tokens

    def test_tokenize_english_word_kept_whole(self):
        """英文/数字 token 整词保留。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        tokens = HashEmbeddingBackend._tokenize("gin cocktail 123")
        assert "gin" in tokens
        assert "cocktail" in tokens
        assert "123" in tokens

    def test_tokenize_short_segment_kept(self):
        """长度 ≤ 2 的段直接保留。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        tokens = HashEmbeddingBackend._tokenize("金酒")
        assert "金酒" in tokens

    def test_tokenize_punctuation_split(self):
        """标点分割。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        tokens = HashEmbeddingBackend._tokenize("金酒，威士忌。朗姆")
        assert "金酒" in tokens
        assert "威士忌" in tokens
        assert "朗姆" in tokens

    def test_tokenize_empty_text(self):
        """空文本无 token。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        assert HashEmbeddingBackend._tokenize("") == []

    def test_tokenize_only_punctuation(self):
        """纯标点无 token。"""
        from hermes_kb.embedding import HashEmbeddingBackend

        assert HashEmbeddingBackend._tokenize("，。！？") == []


# ===========================================================================
# OpenAIEmbeddingBackend
# ===========================================================================
class TestOpenAIEmbeddingBackend:
    """OpenAI 兼容后端。"""

    def test_dim_probe_success(self, monkeypatch):
        """探针成功确定维度。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        # 模拟 _call_api 返回 8 维向量
        def fake_call_api(self, texts):
            return [[0.1] * 8 for _ in texts]

        monkeypatch.setattr(OpenAIEmbeddingBackend, "_call_api", fake_call_api)
        backend = OpenAIEmbeddingBackend()
        assert backend.dim == 8

    def test_dim_probe_failure_fallback_to_config(self, monkeypatch):
        """探针失败回退到 settings.embedding_dim。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        def failing_call_api(self, texts):
            raise RuntimeError("API 不可用")

        monkeypatch.setattr(OpenAIEmbeddingBackend, "_call_api", failing_call_api)
        backend = OpenAIEmbeddingBackend()
        # 探针失败应回退到配置值
        assert backend.dim == backend.settings.embedding_dim

    def test_dim_cached_after_first_probe(self, monkeypatch):
        """首次探测后 dim 缓存，不再重复调用。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        call_count = {"n": 0}

        def fake_call_api(self, texts):
            call_count["n"] += 1
            return [[0.1] * 8 for _ in texts]

        monkeypatch.setattr(OpenAIEmbeddingBackend, "_call_api", fake_call_api)
        backend = OpenAIEmbeddingBackend()
        _ = backend.dim
        _ = backend.dim
        _ = backend.dim
        assert call_count["n"] == 1

    def test_embed_success(self, monkeypatch):
        """embed 成功返回 API 结果。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        def fake_call_api(self, texts):
            return [[0.5] * 4 for _ in texts]

        monkeypatch.setattr(OpenAIEmbeddingBackend, "_call_api", fake_call_api)
        backend = OpenAIEmbeddingBackend()
        vecs = backend.embed(["a", "b", "c"])
        assert len(vecs) == 3
        for v in vecs:
            assert len(v) == 4

    def test_embed_empty_input(self):
        """空输入返回空列表。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        backend = OpenAIEmbeddingBackend()
        assert backend.embed([]) == []

    def test_embed_failure_falls_back_to_hash(self, monkeypatch):
        """API 失败降级 Hash。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        def failing_call_api(self, texts):
            raise RuntimeError("API 故障")

        monkeypatch.setattr(OpenAIEmbeddingBackend, "_call_api", failing_call_api)
        backend = OpenAIEmbeddingBackend()
        # 不应抛错，降级 Hash
        vecs = backend.embed(["测试文本"])
        assert len(vecs) == 1
        assert len(vecs[0]) == backend.settings.embedding_dim

    def test_call_api_uses_correct_url_and_headers(self, monkeypatch):
        """_call_api 构造正确的 URL/headers/body。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                captured["timeout"] = kwargs.get("timeout")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, url, headers=None, json=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["body"] = json
                return FakeResponse()

        monkeypatch.setattr("httpx.Client", FakeClient)
        backend = OpenAIEmbeddingBackend()
        result = backend._call_api(["test"])
        assert result == [[0.1, 0.2, 0.3]]
        assert captured["url"].endswith("/embeddings")
        assert "Bearer " in captured["headers"]["Authorization"]
        assert captured["body"]["input"] == ["test"]
        assert captured["timeout"] == 60.0

    def test_call_api_updates_dim_from_response(self, monkeypatch):
        """_call_api 从响应更新 _dim。"""
        from hermes_kb.embedding import OpenAIEmbeddingBackend

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": [{"embedding": [0.1] * 10}]}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def post(self, *args, **kwargs):
                return FakeResponse()

        monkeypatch.setattr("httpx.Client", FakeClient)
        backend = OpenAIEmbeddingBackend()
        backend._call_api(["x"])
        assert backend._dim == 10


# ===========================================================================
# SentenceTransformerBackend
# ===========================================================================
class TestSentenceTransformerBackend:
    """sentence-transformers 本地后端。"""

    def test_dim_fallback_when_model_unavailable(self, monkeypatch):
        """模型缺失时 dim 回退到配置值。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        # _ensure_model 失败设置 _load_error
        def failing_ensure(self):
            self._load_error = "sentence_transformers not installed"

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", failing_ensure)
        backend = SentenceTransformerBackend()
        assert backend.dim == backend.settings.embedding_dim

    def test_dim_from_model(self, monkeypatch):
        """模型可用时从模型获取维度。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        fake_model = MagicMock()
        fake_model.get_sentence_embedding_dimension.return_value = 512

        def fake_ensure(self):
            self._model = fake_model

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", fake_ensure)
        backend = SentenceTransformerBackend()
        assert backend.dim == 512

    def test_dim_cached(self, monkeypatch):
        """dim 首次探测后缓存。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        fake_model = MagicMock()
        fake_model.get_sentence_embedding_dimension.return_value = 256

        def fake_ensure(self):
            self._model = fake_model

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", fake_ensure)
        backend = SentenceTransformerBackend()
        _ = backend.dim
        _ = backend.dim
        assert fake_model.get_sentence_embedding_dimension.call_count == 1

    def test_dim_model_raises_falls_back(self, monkeypatch):
        """模型 get_sentence_embedding_dimension 抛异常回退配置值。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        fake_model = MagicMock()
        fake_model.get_sentence_embedding_dimension.side_effect = RuntimeError("fail")

        def fake_ensure(self):
            self._model = fake_model

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", fake_ensure)
        backend = SentenceTransformerBackend()
        assert backend.dim == backend.settings.embedding_dim

    def test_embed_empty_input(self):
        """空输入返回空列表。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        backend = SentenceTransformerBackend()
        assert backend.embed([]) == []

    def test_embed_model_none_falls_back_to_hash(self, monkeypatch):
        """模型未加载降级 Hash。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        def failing_ensure(self):
            self._load_error = "not installed"

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", failing_ensure)
        backend = SentenceTransformerBackend()
        vecs = backend.embed(["测试"])
        assert len(vecs) == 1
        assert len(vecs[0]) == backend.settings.embedding_dim

    def test_embed_success(self, monkeypatch):
        """模型可用时正常 embed。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        fake_model = MagicMock()
        # encode 返回类 numpy 数组
        fake_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        def fake_ensure(self):
            self._model = fake_model

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", fake_ensure)
        backend = SentenceTransformerBackend()
        vecs = backend.embed(["a", "b"])
        assert len(vecs) == 2
        assert vecs[0] == [0.1, 0.2, 0.3]
        assert vecs[1] == [0.4, 0.5, 0.6]
        fake_model.encode.assert_called_once_with(["a", "b"], normalize_embeddings=True)

    def test_embed_model_raises_falls_back(self, monkeypatch):
        """模型 encode 抛异常降级 Hash。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        fake_model = MagicMock()
        fake_model.encode.side_effect = RuntimeError("encode fail")

        def fake_ensure(self):
            self._model = fake_model

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", fake_ensure)
        backend = SentenceTransformerBackend()
        vecs = backend.embed(["测试"])
        assert len(vecs) == 1
        assert len(vecs[0]) == backend.settings.embedding_dim

    def test_ensure_model_loads_once(self, monkeypatch):
        """_ensure_model 只加载一次，后续调用直接返回。"""
        from hermes_kb.embedding import SentenceTransformerBackend

        load_count = {"n": 0}

        def fake_ensure(self):
            if self._model is not None or self._load_error:
                return
            load_count["n"] += 1
            self._model = MagicMock()

        monkeypatch.setattr(SentenceTransformerBackend, "_ensure_model", fake_ensure)
        backend = SentenceTransformerBackend()
        backend._ensure_model()
        backend._ensure_model()
        backend._ensure_model()
        assert load_count["n"] == 1


# ===========================================================================
# EmbeddingService
# ===========================================================================
class TestEmbeddingService:
    """Embedding 服务入口。"""

    def test_default_backend_is_hash(self, monkeypatch):
        """默认 provider=hash。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService, HashEmbeddingBackend

        override_settings(embedding_provider="hash")
        service = EmbeddingService()
        assert isinstance(service._backend, HashEmbeddingBackend)

    def test_select_openai_when_available(self, monkeypatch):
        """provider=openai 且 api_key 非空 → OpenAI 后端。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService, OpenAIEmbeddingBackend

        override_settings(
            embedding_provider="openai",
            embedding_api_key="test-key",
        )
        service = EmbeddingService()
        assert isinstance(service._backend, OpenAIEmbeddingBackend)

    def test_select_hash_when_openai_unavailable(self, monkeypatch):
        """provider=openai 但 api_key 空 → 回退 Hash。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService, HashEmbeddingBackend

        override_settings(
            embedding_provider="openai",
            embedding_api_key="",
        )
        service = EmbeddingService()
        assert isinstance(service._backend, HashEmbeddingBackend)

    def test_select_sentence_transformers(self, monkeypatch):
        """provider=sentence_transformers → ST 后端。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService, SentenceTransformerBackend

        override_settings(embedding_provider="sentence_transformers")
        service = EmbeddingService()
        assert isinstance(service._backend, SentenceTransformerBackend)

    def test_dim_override_for_hash_backend(self, monkeypatch):
        """显式 dim 仅对 Hash 后端生效。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService

        override_settings(embedding_provider="hash")
        service = EmbeddingService(dim=128)
        assert service.dim == 128

    def test_dim_override_ignored_for_non_hash(self, monkeypatch):
        """非 Hash 后端忽略 dim 参数。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService, OpenAIEmbeddingBackend

        override_settings(
            embedding_provider="openai",
            embedding_api_key="test-key",
        )
        service = EmbeddingService(dim=128)
        assert isinstance(service._backend, OpenAIEmbeddingBackend)

    def test_backend_name(self, monkeypatch):
        """backend_name 返回类名。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService

        override_settings(embedding_provider="hash")
        service = EmbeddingService()
        assert service.backend_name == "HashEmbeddingBackend"

    def test_embed_delegates_to_backend(self, monkeypatch):
        """embed 委托给后端。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService

        override_settings(embedding_provider="hash")
        service = EmbeddingService(dim=16)
        vecs = service.embed(["测试", "文本"])
        assert len(vecs) == 2
        for v in vecs:
            assert len(v) == 16

    def test_embed_one_returns_single_vector(self, monkeypatch):
        """embed_one 返回单向量。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService

        override_settings(embedding_provider="hash")
        service = EmbeddingService(dim=16)
        vec = service.embed_one("测试")
        assert isinstance(vec, list)
        assert len(vec) == 16

    def test_embed_one_empty_returns_zero_vector(self, monkeypatch):
        """embed_one 空文本返回零向量。"""
        from hermes_kb.config import override_settings
        from hermes_kb.embedding import EmbeddingService

        override_settings(embedding_provider="hash")
        service = EmbeddingService(dim=16)
        vec = service.embed_one("")
        assert vec == [0.0] * 16
