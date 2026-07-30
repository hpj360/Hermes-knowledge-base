"""配置：所有项可通过环境变量覆盖。"""

from __future__ import annotations

import functools
import os
import threading
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path

# 默认 JWT 密钥：仅 dev 模式使用，prod 模式缺失则启动失败
_DEFAULT_JWT_SECRET = "hermes-kb-default-secret-please-change"

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
    raw = v.strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off", ""):
        return False
    # P1-7: 非识别值（如 "disable" / "enable" / "y"）显式报错，
    # 避免用户误以为 "disable" 是关闭（实际静默为 False）。
    raise ValueError(
        f"Invalid boolean value for {key}: {v!r}. "
        f"Expected one of: 1/true/yes/on (True), 0/false/no/off/'' (False)."
    )


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


def _env_float(key: str, default: float) -> float:
    """P3-4: 浮点配置项，非法值显式报错（避免启动崩溃且错误不清）。"""
    v = os.environ.get(key)
    if v is None or v.strip() == "":
        return default
    try:
        return float(v)
    except ValueError as e:
        raise ValueError(
            f"Invalid float value for {key}: {v!r}. Expected a number."
        ) from e


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
    min_score_threshold: float = field(default_factory=lambda: _env_float("KB_MIN_SCORE", 0.015))

    # 向量检索扫描上限（A3-1：替代硬编码 LIMIT 10000）
    vector_scan_limit: int = field(default_factory=lambda: _env_int("KB_VECTOR_SCAN_LIMIT", 50000))

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

    # V3-Task9/10：多用户协作（feature flag，默认关闭，保持单用户模式向后兼容）
    multiuser: bool = field(default_factory=lambda: _env_bool("KB_MULTIUSER", False))

    # 未成年保护（M1-08）
    age_gate_enabled: bool = field(default_factory=lambda: _env_bool("KB_AGE_GATE", True))
    # 年龄门 cookie 安全（P2-5）：生产 HTTPS 应置 True，开发 HTTP 置 False
    cookie_secure: bool = field(default_factory=lambda: _env_bool("KB_COOKIE_SECURE", False))

    # 调试模式（A1-02）：True 时 500 响应保留 str(exc) 便于排查；False 时隐藏内部信息
    debug: bool = field(default_factory=lambda: _env_bool("KB_DEBUG", False))

    # 查询改写（M2-02）
    query_rewrite_enabled: bool = field(default_factory=lambda: _env_bool("KB_QUERY_REWRITE", True))
    # HyDE（M2-02 可选，默认关闭，W1 末评估后决定）
    hyde_enabled: bool = field(default_factory=lambda: _env_bool("KB_HYDE", False))

    # IMA 知识库 OpenAPI（B6: 外部知识库同步）
    # 文档：https://ima.qq.com/agent-interface
    # 鉴权头非标准 Authorization，而是两个自定义头 ima-openapi-clientid / ima-openapi-apikey
    ima_client_id: str = field(default_factory=lambda: _env_str("KB_IMA_CLIENT_ID", ""))
    ima_api_key: str = field(default_factory=lambda: _env_str("KB_IMA_API_KEY", ""))
    # 默认知识库 ID（可留空，运行时通过 list_knowledge_bases 选择）
    ima_kb_id: str = field(default_factory=lambda: _env_str("KB_IMA_KB_ID", ""))
    # 同步时每页拉取条数（IMA OpenAPI 默认上限 50）
    ima_page_size: int = field(default_factory=lambda: _env_int("KB_IMA_PAGE_SIZE", 50))

    # V4-Phase1：Obsidian vault 集成（文件系统直连方案）
    # vault_path 为 Obsidian vault 根目录绝对路径；留空表示未启用
    vault_path: str = field(default_factory=lambda: _env_str("KB_VAULT_PATH", ""))
    # 是否启用 watchdog 实时监听（False 时仅手动触发扫描）
    vault_watch: bool = field(default_factory=lambda: _env_bool("KB_VAULT_WATCH", True))
    # 排除的子目录/文件模式（glob，逗号分隔），默认排除 .obsidian 配置目录与附件
    vault_exclude: str = field(default_factory=lambda: _env_str("KB_VAULT_EXCLUDE", ".obsidian,.trash,*.png,*.jpg,*.jpeg,*.gif,*.pdf,*.svg"))

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
    def ima_enabled(self) -> bool:
        """是否启用 IMA 知识库同步（client_id + api_key 都配置）。"""
        return bool(self.ima_client_id and self.ima_api_key)

    @property
    def vault_enabled(self) -> bool:
        """V4-Phase1：是否启用 Obsidian vault 集成（vault_path 非空且存在）。"""
        if not self.vault_path.strip():
            return False
        from pathlib import Path

        return Path(self.vault_path).expanduser().is_dir()

    @property
    def vault_exclude_patterns(self) -> list[str]:
        """V4-Phase1：解析 vault_exclude 为 glob 模式列表。"""
        if not self.vault_exclude.strip():
            return []
        return [p.strip() for p in self.vault_exclude.split(",") if p.strip()]

    @property
    def cors_credentials_allowed(self) -> bool:
        """CORS 是否允许携带凭证：仅当 origins 不含通配符 * 时允许。"""
        if not self.cors_origins:
            return False
        return "*" not in self.cors_origins

    def __post_init__(self) -> None:
        """启动期安全校验（A1-1）。

        - 启用认证时必须显式配置非默认 jwt_secret，否则禁止启动。
        - 生产环境（KB_ENV=prod）必须显式开启认证（KB_AUTH_ENABLED=true），
          否则所有管理员端点（审计/导出/仪表盘）将完全暴露（C-1 安全修复）。
        """
        if self.auth_enabled:
            if not self.jwt_secret or not self.jwt_secret.strip():
                raise RuntimeError(
                    "jwt_secret must be set to a non-empty value when "
                    "KB_AUTH_ENABLED=true (set KB_JWT_SECRET env var)"
                )
            if self.jwt_secret == _DEFAULT_JWT_SECRET:
                raise RuntimeError(
                    "jwt_secret is still the default value. Set a unique "
                    "secret via the KB_JWT_SECRET environment variable before "
                    "enabling auth (KB_AUTH_ENABLED=true)."
                )
        # 生产环境强制开启认证，避免 admin 端点（dashboard/audit/export）裸奔
        if self.is_prod and not self.auth_enabled:
            raise RuntimeError(
                "KB_AUTH_ENABLED must be true in production (KB_ENV=prod). "
                "Admin endpoints (dashboard/audit/export) require authentication. "
                "Set KB_AUTH_ENABLED=true and KB_JWT_SECRET=<unique-secret>."
            )
        # 生产环境禁止使用通配符 CORS（防任意网站跨域读）
        if self.is_prod and ("*" in self.cors_origins):
            raise RuntimeError(
                "KB_CORS must not contain '*' in production (KB_ENV=prod). "
                "Specify explicit origins to prevent cross-site data exfiltration."
            )
        # 生产环境禁止 debug 模式（避免异常详情泄露）
        if self.is_prod and self.debug:
            raise RuntimeError(
                "KB_DEBUG must be false in production (KB_ENV=prod). "
                "Debug mode exposes internal exception details to clients."
            )


_SETTINGS: Settings | None = None
_SETTINGS_LOCK = threading.Lock()


@functools.lru_cache(maxsize=1)
def _create_settings() -> Settings:
    """线程安全的单例创建（lru_cache 内部加锁，避免多 worker 竞态）。"""
    return Settings()


def get_settings() -> Settings:
    """获取全局配置单例（线程安全）。

    P1-3: 用 lru_cache 保护单例创建，消除多 worker 下的竞态。
    测试期 override 优先于缓存实例。
    """
    override = _SETTINGS
    if override is not None:
        return override
    return _create_settings()


def reset_settings() -> None:
    """测试用：重置单例（清除 override + 清空 lru_cache）。"""
    global _SETTINGS
    with _SETTINGS_LOCK:
        _SETTINGS = None
    _create_settings.cache_clear()


def override_settings(**kwargs) -> Settings:
    """测试用：覆盖部分配置（线程安全）。"""
    global _SETTINGS
    base = get_settings()
    new = replace(base, **kwargs)
    with _SETTINGS_LOCK:
        _SETTINGS = new
    return new
