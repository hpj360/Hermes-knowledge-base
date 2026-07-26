"""config.py 覆盖率补强测试（阶段6 批次1）。

覆盖目标：
- _env_int / _env_bool / _env_float 的非法值分支
- embedding_available 的 sentence_transformers 分支
- __post_init__ 生产环境安全校验（CORS 通配符 / debug 模式 / 强制认证）
"""
from __future__ import annotations

import pytest


def _clear_kb_env(monkeypatch):
    """清掉所有 KB_ 环境变量，避免外部污染。"""
    import os

    for k in list(os.environ):
        if k.startswith("KB_"):
            monkeypatch.delenv(k, raising=False)


def test_env_int_invalid_value_returns_default(monkeypatch):
    """_env_int 非整数输入返回默认值（不抛异常）。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_PORT", "not-a-number")
    from hermes_kb.config import reset_settings

    reset_settings()
    # KB_PORT 解析失败应回退到默认 8765
    s = _make_settings()
    assert s.port == 8765


def _make_settings():
    """构造 Settings（绕过单例缓存，确保每次读取最新 env）。"""
    from hermes_kb.config import Settings

    return Settings()


def test_env_bool_invalid_value_raises(monkeypatch):
    """_env_bool 非识别值（如 'disable'）显式报错，不静默为 False。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_AUTH_ENABLED", "disable")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    with pytest.raises(ValueError, match="Invalid boolean value"):
        Settings()


def test_env_bool_recognized_true_values(monkeypatch):
    """_env_bool 识别 1/true/yes/on 为 True。"""
    _clear_kb_env(monkeypatch)
    from hermes_kb.config import Settings, reset_settings

    for val in ("1", "true", "TRUE", "yes", "on"):
        _clear_kb_env(monkeypatch)
        monkeypatch.setenv("KB_AGE_GATE", val)
        reset_settings()
        assert Settings().age_gate_enabled is True


def test_env_bool_recognized_false_values(monkeypatch):
    """_env_bool 识别 0/false/no/off/'' 为 False。"""
    _clear_kb_env(monkeypatch)
    from hermes_kb.config import Settings, reset_settings

    for val in ("0", "false", "no", "off", ""):
        _clear_kb_env(monkeypatch)
        monkeypatch.setenv("KB_AGE_GATE", val)
        reset_settings()
        assert Settings().age_gate_enabled is False


def test_env_float_invalid_value_raises(monkeypatch):
    """_env_float 非浮点输入显式报错。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_MIN_SCORE", "not-a-float")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    with pytest.raises(ValueError, match="Invalid float value"):
        Settings()


def test_env_float_empty_returns_default(monkeypatch):
    """_env_float 空字符串返回默认值。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_MIN_SCORE", "  ")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    assert Settings().min_score_threshold == 0.015


def test_embedding_available_sentence_transformers(monkeypatch):
    """embedding_provider='sentence_transformers' 时 embedding_available=True（无需 API key）。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_EMBEDDING_PROVIDER", "sentence_transformers")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    s = Settings()
    assert s.embedding_provider == "sentence_transformers"
    assert s.embedding_available is True


def test_embedding_available_hash_provider(monkeypatch):
    """embedding_provider='hash' 时 embedding_available=False。"""
    _clear_kb_env(monkeypatch)
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    assert Settings().embedding_available is False


def test_embedding_available_openai_with_key(monkeypatch):
    """embedding_provider='openai' + API key → embedding_available=True。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("KB_EMBEDDING_API_KEY", "sk-real-key")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    assert Settings().embedding_available is True


def test_post_init_prod_without_auth_raises(monkeypatch):
    """生产环境（KB_ENV=prod）未开启认证 → RuntimeError。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_ENV", "prod")
    monkeypatch.setenv("KB_JWT_SECRET", "a-real-prod-secret-xxx")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    with pytest.raises(RuntimeError, match="KB_AUTH_ENABLED must be true in production"):
        Settings()


def test_post_init_prod_with_cors_wildcard_raises(monkeypatch):
    """生产环境 CORS 含 '*' → RuntimeError。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_ENV", "prod")
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_JWT_SECRET", "a-real-prod-secret-xxx")
    monkeypatch.setenv("KB_CORS", "*")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    with pytest.raises(RuntimeError, match="KB_CORS must not contain"):
        Settings()


def test_post_init_prod_with_debug_raises(monkeypatch):
    """生产环境开启 debug → RuntimeError。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_ENV", "prod")
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_JWT_SECRET", "a-real-prod-secret-xxx")
    monkeypatch.setenv("KB_DEBUG", "true")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    with pytest.raises(RuntimeError, match="KB_DEBUG must be false in production"):
        Settings()


def test_post_init_prod_valid_config_ok(monkeypatch):
    """生产环境合法配置（认证开 + 非默认密钥 + 无通配 CORS + debug 关）→ 正常。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_ENV", "prod")
    monkeypatch.setenv("KB_AUTH_ENABLED", "true")
    monkeypatch.setenv("KB_JWT_SECRET", "a-real-prod-secret-xxx-yyy-zzz")
    monkeypatch.setenv("KB_CORS", "https://example.com")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    s = Settings()
    assert s.is_prod is True
    assert s.auth_enabled is True
    assert s.debug is False


def test_resolve_jwt_secret_prod_missing_raises(monkeypatch):
    """prod 模式且 KB_JWT_SECRET 未设置 → _resolve_jwt_secret 报错。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_ENV", "prod")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    with pytest.raises(RuntimeError, match="KB_JWT_SECRET 未设置"):
        Settings()


def test_cors_credentials_allowed(monkeypatch):
    """cors_credentials_allowed：通配符时 False，具体 origin 时 True。"""
    _clear_kb_env(monkeypatch)
    from hermes_kb.config import Settings, reset_settings

    # 无 CORS origins
    reset_settings()
    assert Settings().cors_credentials_allowed is False

    # 含通配符
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_CORS", "*")
    reset_settings()
    assert Settings().cors_credentials_allowed is False

    # 具体 origin
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_CORS", "https://a.com,https://b.com")
    reset_settings()
    assert Settings().cors_credentials_allowed is True


def test_llm_available_mock_provider(monkeypatch):
    """llm_provider='mock' 时 llm_available=False。"""
    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_LLM_PROVIDER", "mock")
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    assert Settings().llm_available is False


def test_ima_enabled_flag(monkeypatch):
    """ima_enabled：client_id + api_key 都配置时为 True。"""
    _clear_kb_env(monkeypatch)
    from hermes_kb.config import Settings, reset_settings

    reset_settings()
    assert Settings().ima_enabled is False

    _clear_kb_env(monkeypatch)
    monkeypatch.setenv("KB_IMA_CLIENT_ID", "cid")
    monkeypatch.setenv("KB_IMA_API_KEY", "key")
    reset_settings()
    assert Settings().ima_enabled is True


def test_override_settings(monkeypatch):
    """override_settings 覆盖部分配置（线程安全）。"""
    _clear_kb_env(monkeypatch)
    from hermes_kb.config import get_settings, override_settings, reset_settings

    reset_settings()
    new = override_settings(top_k=99)
    assert new.top_k == 99
    assert get_settings().top_k == 99
    # reset 后恢复
    reset_settings()
    assert get_settings().top_k == 5
