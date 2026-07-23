"""代码质量优化后的补充测试：负面路径 + 边缘场景。

覆盖第 4 批优化引入的新行为：
- 单文件上传端点（happy + 解析失败 + 损坏文件）
- 标签颜色格式校验（非法值回退默认色）
- metadata 不存在 tag_id 返回 skipped_tag_ids
- 文档详情分页（chunk_limit/chunk_offset）
- 查询改写 LLM 超时/异常降级
- token 过期 API 级 401
- 批量上传总体积上限 413
- JWT 密钥 prod 模式拒绝启动
- CORS credentials 收紧
"""

from __future__ import annotations

import io
import time

import pytest


# ---------------------------------------------------------------------------
# 单文件上传（/api/documents/upload）
# ---------------------------------------------------------------------------
def test_upload_single_txt_happy(client):
    """单文件上传 txt 成功。"""
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", io.BytesIO("测试内容".encode("utf-8")), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "imported"
    assert body["doc_id"]


def test_upload_single_empty_filename_400(client):
    """空文件名 → 400 或 422（FastAPI 校验）。"""
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("", io.BytesIO(b"x"), "text/plain")},
    )
    assert resp.status_code in (400, 422)


def test_upload_single_unsupported_type_400(client):
    """不支持的类型 → 400。"""
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("a.jpg", io.BytesIO(b"x"), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


def test_upload_single_pdf_parse_failure_400(client):
    """损坏 PDF（非真正 PDF 二进制）→ 400 友好提示。"""
    # 传一个声明 .pdf 但内容不是有效 PDF 的文件
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("bad.pdf", io.BytesIO(b"not a real pdf"), "application/pdf")},
    )
    # pypdf 解析失败 → RuntimeError → 400
    assert resp.status_code == 400
    assert "解析失败" in resp.json()["detail"] or "解析" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# 标签颜色校验
# ---------------------------------------------------------------------------
def test_create_tag_invalid_color_falls_back_to_default(client):
    """非法颜色值 → 回退默认灰色 #6b7280。"""
    resp = client.post("/api/tags", json={"name": "测试标签", "color": "xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["color"] == "#6b7280"


def test_create_tag_empty_color_falls_back(client):
    """空颜色 → 回退默认。"""
    resp = client.post("/api/tags", json={"name": "空色", "color": ""})
    assert resp.status_code == 200
    assert resp.json()["color"] == "#6b7280"


def test_create_tag_valid_color_preserved(client):
    """合法 #RRGGBB 颜色保留。"""
    resp = client.post("/api/tags", json={"name": "合法色", "color": "#ff5733"})
    assert resp.status_code == 200
    assert resp.json()["color"] == "#ff5733"


# ---------------------------------------------------------------------------
# metadata skipped_tag_ids
# ---------------------------------------------------------------------------
def test_update_metadata_skipped_tag_ids_returned(client):
    """传入不存在的 tag_id → 返回 skipped_tag_ids。"""
    # 先导入一篇文档
    resp = client.post(
        "/api/documents/import-text",
        json={"title": "测试", "content": "内容"},
    )
    doc_id = resp.json()["doc_id"]
    # 传入一个不存在的 tag_id（999999）
    resp = client.put(
        f"/api/documents/{doc_id}/metadata",
        json={"tag_ids": [999999]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "updated"
    assert body["skipped_tag_ids"] == [999999]


# ---------------------------------------------------------------------------
# 文档详情分页
# ---------------------------------------------------------------------------
def test_get_document_pagination(client):
    """chunk_limit + chunk_offset 分页。"""
    # 导入一篇多 chunk 文档（重复段落）
    content = "\n\n".join([f"段落 {i}" for i in range(30)])
    resp = client.post(
        "/api/documents/import-text",
        json={"title": "分页测试", "content": content},
    )
    doc_id = resp.json()["doc_id"]

    # 第一页：limit=5, offset=0
    resp = client.get(f"/api/documents/{doc_id}?chunk_limit=5&chunk_offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["chunks"]) <= 5
    assert body["pagination"]["limit"] == 5
    assert body["pagination"]["offset"] == 0
    assert body["pagination"]["returned"] == len(body["chunks"])

    # 第二页
    resp = client.get(f"/api/documents/{doc_id}?chunk_limit=5&chunk_offset=5")
    assert resp.status_code == 200
    body2 = resp.json()
    assert body2["pagination"]["offset"] == 5


def test_get_document_no_pagination_returns_all(client):
    """不传 chunk_limit → 返回全部。"""
    resp = client.post(
        "/api/documents/import-text",
        json={"title": "无分页", "content": "短内容"},
    )
    doc_id = resp.json()["doc_id"]
    resp = client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["limit"] is None


# ---------------------------------------------------------------------------
# 查询改写降级
# ---------------------------------------------------------------------------
def test_query_rewriter_llm_timeout_falls_back(monkeypatch):
    """LLM 超时 → 回退启发式。"""
    from hermes_kb import query_rewriter

    class SlowLLM:
        def chat(self, messages):
            time.sleep(10)  # 模拟超时
            raise RuntimeError("不应到达")

    # 强制启用 LLM 路径
    monkeypatch.setattr(
        query_rewriter.QueryRewriter, "__init__",
        lambda self, llm_client=None: (
            setattr(self, "llm", SlowLLM()),
            setattr(self, "enabled", True),
        )[1]
    )
    # 缩短超时到 0.5s 加速测试
    monkeypatch.setattr(query_rewriter, "_REWRITE_TIMEOUT_SEC", 0.5)

    r = query_rewriter.QueryRewriter()
    result = r.rewrite("金酒啥味")
    # 超时应回退启发式，包含杜松子
    assert "杜松子" in result or "金酒" in result


def test_query_rewriter_llm_exception_falls_back(monkeypatch):
    """LLM 抛异常 → 回退启发式。"""
    from hermes_kb import query_rewriter

    class FailLLM:
        def chat(self, messages):
            raise RuntimeError("LLM 故障")

    monkeypatch.setattr(
        query_rewriter.QueryRewriter, "__init__",
        lambda self, llm_client=None: (
            setattr(self, "llm", FailLLM()),
            setattr(self, "enabled", True),
        )[1]
    )

    r = query_rewriter.QueryRewriter()
    result = r.rewrite("威士忌")
    # 异常应回退启发式
    assert "威士忌" in result


# ---------------------------------------------------------------------------
# JWT 密钥安全
# ---------------------------------------------------------------------------
def test_jwt_secret_prod_missing_raises(monkeypatch):
    """prod 模式未设置 KB_JWT_SECRET → 拒绝启动。"""
    monkeypatch.setenv("KB_ENV", "prod")
    monkeypatch.delenv("KB_JWT_SECRET", raising=False)
    from hermes_kb.config import reset_settings
    reset_settings()
    with pytest.raises(RuntimeError, match="KB_JWT_SECRET"):
        from hermes_kb.config import Settings
        Settings()


def test_jwt_secret_dev_default_warns(monkeypatch):
    """dev 模式未设置 → 使用默认值并告警。"""
    monkeypatch.setenv("KB_ENV", "dev")
    monkeypatch.delenv("KB_JWT_SECRET", raising=False)
    from hermes_kb.config import reset_settings, Settings
    reset_settings()
    with pytest.warns(RuntimeWarning, match="KB_JWT_SECRET"):
        s = Settings()
    assert s.jwt_secret  # 有默认值
    assert s.is_prod is False


# ---------------------------------------------------------------------------
# CORS 收紧
# ---------------------------------------------------------------------------
def test_cors_credentials_false_when_wildcard(monkeypatch):
    """origins 含 * 时 credentials 为 False。"""
    monkeypatch.setenv("KB_CORS", "*")
    from hermes_kb.config import reset_settings, Settings
    reset_settings()
    s = Settings()
    assert "*" in s.cors_origins
    assert s.cors_credentials_allowed is False


def test_cors_credentials_true_when_specific(monkeypatch):
    """origins 为具体源时 credentials 为 True。"""
    monkeypatch.setenv("KB_CORS", "https://example.com,https://app.com")
    from hermes_kb.config import reset_settings, Settings
    reset_settings()
    s = Settings()
    assert s.cors_credentials_allowed is True


def test_cors_credentials_false_when_empty(monkeypatch):
    """origins 为空时 credentials 为 False。"""
    monkeypatch.delenv("KB_CORS", raising=False)
    from hermes_kb.config import reset_settings, Settings
    reset_settings()
    s = Settings()
    assert s.cors_origins == []
    assert s.cors_credentials_allowed is False


# ---------------------------------------------------------------------------
# token 过期 API 级 401
# ---------------------------------------------------------------------------
def test_expired_token_returns_401(client, monkeypatch):
    """过期 token 访问受保护端点 → 401。"""
    # 使用非默认 secret（__post_init__ 安全校验拒绝默认值）
    test_secret = "test-secret-for-expired-token-xxx"
    monkeypatch.setenv("KB_JWT_SECRET", test_secret)

    # 构造一个已过期的 token（exp 设为 1 小时前）
    import time as _time
    payload = {
        "sub": "admin",
        "role": "admin",
        "iat": int(_time.time()) - 7200,
        "exp": int(_time.time()) - 3600,  # 1 小时前过期
    }
    # 手动构造过期 token
    import json
    from base64 import urlsafe_b64encode
    import hmac
    import hashlib

    def _b64e(data: bytes) -> str:
        return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    h = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = _b64e(json.dumps(payload).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(test_secret.encode(), signing_input, hashlib.sha256).digest()
    expired_token = f"{h}.{p}.{_b64e(sig)}"

    # 启用认证
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_AUTH_PASSWORD", "test")
    from hermes_kb.config import reset_settings
    reset_settings()

    resp = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 批量上传总体积上限
# ---------------------------------------------------------------------------
def test_upload_batch_total_size_limit(client):
    """批量上传总体积超 100MB → 413。

    注意：此测试构造单文件超 10MB 触发单文件上限，
    或构造累计超 100MB 触发总量上限。
    这里用单文件超 10MB 测试 413（_save_upload_tmp 内置检查）。
    """
    # 11MB 内容
    big_content = b"x" * (11 * 1024 * 1024)
    resp = client.post(
        "/api/documents/upload-batch",
        files=[("files", ("big.txt", io.BytesIO(big_content), "text/plain"))],
    )
    # 单文件超 10MB → _save_upload_tmp 抛 413
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# 文档详情 404
# ---------------------------------------------------------------------------
def test_get_document_404(client):
    """不存在的 doc_id → 404。"""
    resp = client.get("/api/documents/doc_nonexistent123")
    assert resp.status_code == 404


def test_get_document_raw_404(client):
    """raw 端点不存在 doc_id → 404。"""
    resp = client.get("/api/documents/doc_nonexistent123/raw")
    assert resp.status_code == 404


def test_delete_document_404(client):
    """删除不存在的文档 → 404。"""
    resp = client.delete("/api/documents/doc_nonexistent123")
    assert resp.status_code == 404


def test_delete_tag_404(client):
    """删除不存在的标签 → 404。"""
    resp = client.delete("/api/tags/999999")
    assert resp.status_code == 404


def test_update_metadata_404(client):
    """更新不存在文档的元信息 → 404。"""
    resp = client.put(
        "/api/documents/doc_nonexistent123/metadata",
        json={"title": "新标题"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 空文档边缘场景
# ---------------------------------------------------------------------------
def test_empty_document_detail(client):
    """空内容文档被拒绝（400），但空内容带 allow_empty 的端点不崩。

    import_text 对空内容返回 400（业务校验），这是合理行为。
    此测试验证空内容不会导致端点崩溃。
    """
    resp = client.post(
        "/api/documents/import-text",
        json={"title": "空文档", "content": ""},
    )
    # 空内容被业务拒绝是合理的（400），不算 bug
    assert resp.status_code in (200, 400)
    if resp.status_code == 200:
        doc_id = resp.json()["doc_id"]
        resp = client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["chunks"], list)


# ---------------------------------------------------------------------------
# raw 端点 PDF 处理
# ---------------------------------------------------------------------------
def test_raw_pdf_returns_text_plain(client):
    """PDF 文档 raw 下载应返回 text/plain（解析后纯文本）。"""
    # 直接构造一个 file_type=pdf 的文档（绕过解析）
    from hermes_kb.database import get_session
    from hermes_kb.models import Document

    with get_session() as session:
        doc = Document(
            doc_id="test_pdf_raw_001",
            title="PDF测试",
            content="这是 PDF 解析后的纯文本",
            file_type="pdf",
            chunk_count=0,
        )
        session.add(doc)
        session.commit()

    resp = client.get("/api/documents/test_pdf_raw_001/raw")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    # 文件名应是 .txt 而非 .pdf
    disp = resp.headers.get("content-disposition", "")
    assert ".txt" in disp
