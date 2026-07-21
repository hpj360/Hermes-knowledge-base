"""配置：所有项可通过环境变量覆盖。"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path

# 默认 JWT 密钥：仅 dev 模式使用，prod 模式缺失则启动失败
_DEFAULT_JWT_SECRET = "hermes-kb-dev-only-secret-DO-NOT-USE-IN-PROD"

# M2-06 预设分类（业务配置，归属 config 而非 models）
PRESET_CATEGORIES = [
    "烈酒",
    "葡萄酒",
    "啤酒",
    "中国白酒",
    "利口酒",
    "资料",
    "其他",
]


def _env_int(key: str, default: int) -> int:
    v = os.environ.get(key)
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_list(key: str, default: list[str]) -> list[str]:
    v = os.environ.get(key)
    if not v:
        return list(default)
    return [x.strip() for x in v.split(",") if x.strip()]


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _resolve_jwt_secret() -> str:
    """解析 JWT 密钥：prod 模式缺失则报错；dev 模式使用默认值并告警。"""
    secret = os.environ.get("KB_JWT_SECRET", "")
    if secret:
        return secret
    env = os.environ.get("KB_ENV", "dev")
    if env == "prod":
        raise RuntimeError(
            "KB_JWT_SECRET 未设置。生产环境（KB_ENV=prod）必须显式配置 JWT 密钥。"
        )
    warnings.warn(
        "KB_JWT_SECRET 未设置，使用 dev 默认密钥。切勿用于生产环境！",
        RuntimeWarning,
        stacklevel=2,
    )
    return _DEFAULT_JWT_SECRET


@dataclass
class Settings:
    """全局配置。"""

    db_path: str = field(default_factory=lambda: _env_str("KB_DB_PATH", ".hermes_kb/hermes_kb.db"))
    host: str = field(default_factory=lambda: _env_str("KB_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("KB_PORT", 8765))
    cors_origins: list[str] = field(default_factory=lambda: _env_list("KB_CORS", []))
    # 环境标识：prod 模式下强制要求 JWT 密钥等敏感配置
    env: str = field(default_factory=lambda: _env_str("KB_ENV", "dev"))

    # 分片
    chunk_size: int = field(default_factory=lambda: _env_int("KB_CHUNK_SIZE", 500))
    chunk_overlap: int = field(default_factory=lambda: _env_int("KB_CHUNK_OVERLAP", 80))

    # 检索
    top_k: int = field(default_factory=lambda: _env_int("KB_TOP_K", 5))
    rrf_k: int = field(default_factory=lambda: _env_int("KB_RRF_K", 60))
    # 低置信度阈值：RRF score < 此值时返回"未找到"反馈（M1-06）
    min_score_threshold: float = field(default_factory=lambda: float(_env_str("KB_MIN_SCORE", "0.005")))

    # Embedding Provider（M1-02）
    embedding_dim: int = field(default_factory=lambda: _env_int("KB_EMBEDDING_DIM", 256))
    embedding_provider: str = field(default_factory=lambda: _env_str("KB_EMBEDDING_PROVIDER", "hash"))
    embedding_api_key: str = field(default_factory=lambda: _env_str("KB_EMBEDDING_API_KEY", ""))
    embedding_base_url: str = field(default_factory=lambda: _env_str("KB_EMBEDDING_BASE_URL", "https://api.openai.com/v1"))
    embedding_model: str = field(default_factory=lambda: _env_str("KB_EMBEDDING_MODEL", "text-embedding-3-small"))
    embedding_st_model: str = field(default_factory=lambda: _env_str("KB_EMBEDDING_ST_MODEL", "BAAI/bge-small-zh-v1.5"))

    # LLM Provider（M1-01）
    llm_api_key: str = field(default_factory=lambda: _env_str("KB_LLM_API_KEY", ""))
    llm_base_url: str = field(default_factory=lambda: _env_str("KB_LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = field(default_factory=lambda: _env_str("KB_LLM_MODEL", "gpt-4o-mini"))
    llm_provider: str = field(default_factory=lambda: _env_str("KB_LLM_PROVIDER", "openai"))

    # 安全
    query_max_length: int = field(default_factory=lambda: _env_int("KB_QUERY_MAX_LENGTH", 500))

    # 认证（M1-07）
    auth_enabled: bool = field(default_factory=lambda: _env_bool("KB_AUTH_ENABLED", False))
    auth_password: str = field(default_factory=lambda: _env_str("KB_AUTH_PASSWORD", ""))
    auth_username: str = field(default_factory=lambda: _env_str("KB_USERNAME", "admin"))
    jwt_secret: str = field(default_factory=lambda: _resolve_jwt_secret())
    jwt_ttl_hours: int = field(default_factory=lambda: _env_int("KB_JWT_TTL_HOURS", 24))

    # 未成年保护（M1-08）
    age_gate_enabled: bool = field(default_factory=lambda: _env_bool("KB_AGE_GATE", True))

    # 查询改写（M2-02）
    query_rewrite_enabled: bool = field(default_factory=lambda: _env_bool("KB_QUERY_REWRITE", True))
    # HyDE（M2-02 可选，默认关闭，W1 末评估后决定）
    hyde_enabled: bool = field(default_factory=lambda: _env_bool("KB_HYDE", False))

    @property
    def llm_available(self) -> bool:
        """是否启用真实 LLM。"""
        if self.llm_provider == "mock":
            return False
        return bool(self.llm_api_key and self.llm_api_key.strip())

    @property
    def embedding_available(self) -> bool:
        """是否启用真实 Embedding。"""
        if self.embedding_provider == "hash":
            return False
        if self.embedding_provider == "sentence_transformers":
            return True
        return bool(self.embedding_api_key and self.embedding_api_key.strip())

    @property
    def db_url(self) -> str:
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{p.absolute()}"

    @property
    def is_prod(self) -> bool:
        """是否生产环境。"""
        return self.env == "prod"

    @property
    def cors_credentials_allowed(self) -> bool:
        """CORS 是否允许携带凭证：仅当 origins 不含通配符 * 时允许。"""
        if not self.cors_origins:
            return False
        return "*" not in self.cors_origins


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS


def reset_settings() -> None:
    """测试用：重置单例。"""
    global _SETTINGS
    _SETTINGS = None


def override_settings(**kwargs) -> Settings:
    """测试用：覆盖部分配置。"""
    s = get_settings()
    new = replace(s, **kwargs)
    global _SETTINGS
    _SETTINGS = new
    return new
