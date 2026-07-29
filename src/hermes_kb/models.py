"""SQLModel 数据模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

# P2 修复：PRESET_CATEGORIES 已移至 config.py，此处仅做向后兼容重导出
from hermes_kb.config import PRESET_CATEGORIES  # noqa: F401


def _now_utc() -> datetime:
    """当前 UTC 时间（无时区信息的 datetime，兼容 SQLite）。

    P2 修复：datetime.utcnow() 在 Python 3.12+ 已废弃。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gen_doc_id() -> str:
    return f"doc_{uuid4().hex[:12]}"


class Document(SQLModel, table=True):
    """文档。"""

    doc_id: str = Field(default_factory=_gen_doc_id, primary_key=True, max_length=64)
    title: str = Field(index=True, max_length=200)
    content: str = Field(default="", sa_column=Column("content", Text))
    source_type: str = Field(default="local", max_length=32)  # local / upload / seed
    file_type: str = Field(default="txt", max_length=16)  # txt / md / pdf
    source_path: str | None = Field(default=None, max_length=512)
    chunk_count: int = Field(default=0)
    category: str = Field(default="", max_length=32, index=True)  # M2-06：分类（单选）
    # B1: 数据源治理字段（向后兼容，均有默认值）
    source: str = Field(default="local", max_length=32, index=True)  # local/iba/thecocktaildb/user/ugc
    source_id: str | None = Field(default=None, max_length=64)
    verified: bool = Field(default=True)
    season: str | None = Field(default=None, max_length=16)  # spring/summer/autumn/winter
    hidden: bool = Field(default=False)
    status: str = Field(default="published", max_length=16)  # draft/pending/published/rejected
    image_url: str | None = Field(default=None, max_length=512)  # B 新增：外部图片 URL
    meta: str = Field(default="{}", sa_column=Column("metadata", Text))  # B 新增：JSON 字符串（属性名避开 SQLAlchemy 保留字 metadata）
    # M3：配方结构化元数据（向后兼容，默认空字符串）
    glassware: str = Field(default="", max_length=64, index=True)  # 载杯类型（马天尼杯/古典杯/高球杯...）
    technique: str = Field(default="", max_length=32, index=True)  # 调酒技法（build/stir/shake/blend/layer/muddle）
    iba_category: str = Field(default="", max_length=32, index=True)  # IBA 分类（unforgettables/contemporary_classics/new_era_drinks）
    flavor_profile: str = Field(default="", max_length=256)  # 风味标签（分号分隔，如 "苦甜;药草;干爽"）
    # M3+：难度与强度档位（向后兼容，默认空字符串）
    difficulty: str = Field(default="", max_length=16, index=True)  # 制作难度（easy/medium/hard）
    abv_bucket: str = Field(default="", max_length=16, index=True)  # 强度档位（low/medium/high/strong）
    created_at: datetime = Field(default_factory=_now_utc)

    def __init__(self, **data: object) -> None:
        # 允许 `metadata=` 构造参数，映射到实际字段 `meta`
        if "metadata" in data:
            data["meta"] = data.pop("metadata")
        super().__init__(**data)


# 类创建完成后挂载 `metadata` 只读 property（避开 SQLAlchemy 在类声明期对
# `metadata` 保留名的检查，同时不破坏 `cls.metadata` 在建表阶段返回 MetaData）。
def _get_metadata(self: Document) -> str:
    return self.meta


Document.metadata = property(_get_metadata)  # type: ignore[assignment]


class Chunk(SQLModel, table=True):
    """文档分片。"""

    id: int | None = Field(default=None, primary_key=True)
    doc_id: str = Field(
        max_length=64,
        sa_column=Column("doc_id", Text, ForeignKey("document.doc_id", ondelete="CASCADE"), index=True),
    )
    idx: int = Field(default=0)
    text: str = Field(default="", sa_column=Column("text", Text))
    char_start: int = Field(default=0)
    char_end: int = Field(default=0)
    created_at: datetime = Field(default_factory=_now_utc)


class Tag(SQLModel, table=True):
    """M2-06：标签。"""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=32, unique=True)
    color: str = Field(default="#6b7280", max_length=16)  # hex 颜色
    created_at: datetime = Field(default_factory=_now_utc)


class DocumentTag(SQLModel, table=True):
    """M2-06：文档-标签关联（多对多）。"""

    id: int | None = Field(default=None, primary_key=True)
    doc_id: str = Field(
        max_length=64,
        sa_column=Column("doc_id", Text, ForeignKey("document.doc_id", ondelete="CASCADE"), index=True),
    )
    tag_id: int = Field(
        sa_column=Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), index=True),
    )
    created_at: datetime = Field(default_factory=_now_utc)


class QueryLog(SQLModel, table=True):
    """问答日志。"""

    id: int | None = Field(default=None, primary_key=True)
    query: str = Field(max_length=2000)
    answer: str = Field(default="", sa_column=Column("answer", Text))
    citations: str = Field(
        default="[]", sa_column=Column("citations", Text)
    )  # JSON
    model_used: str = Field(default="mock", max_length=64)
    latency_ms: int = Field(default=0)
    feedback: int = Field(default=0)  # 1=up / -1=down / 0=none
    # M2-10：token 用量统计（默认 0，向后兼容旧记录）
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    cost_cny: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=_now_utc, index=True)


class RecipeStats(SQLModel, table=True):
    """M3：配方使用统计。"""

    doc_id: str = Field(
        max_length=64,
        sa_column=Column("doc_id", Text, ForeignKey("document.doc_id", ondelete="CASCADE"), primary_key=True),
    )
    match_count: int = Field(default=0)  # 被匹配命中次数（累计）
    view_count: int = Field(default=0)  # 被点击查看次数
    weekly_match_count: int = Field(default=0)  # A4-1: 本周新增匹配数
    last_matched_at: datetime | None = Field(default=None)
    last_viewed_at: datetime | None = Field(default=None)


class IngredientSubstitute(SQLModel, table=True):
    """M3：材料替代关系（L2 用户自定义 + L1 预置镜像）。"""

    __table_args__ = (
        UniqueConstraint("canonical", "substitute", name="uq_ingredient_substitute"),
    )

    id: int | None = Field(default=None, primary_key=True)
    canonical: str = Field(index=True, max_length=64)  # 原材料标准名
    substitute: str = Field(max_length=64)  # 替代材料名
    source: str = Field(default="preset", max_length=16)  # preset | user
    created_at: datetime = Field(default_factory=_now_utc)


class MissingIngredientStats(SQLModel, table=True):
    """M4.1：缺失材料统计（材料维度，反向优化替代表）。"""

    canonical: str = Field(primary_key=True, max_length=64)
    missing_count: int = Field(default=0)
    last_missing_at: datetime | None = Field(default=None)


class RecipeVariant(SQLModel, table=True):
    """M4.3：配方变体关联。"""

    id: int | None = Field(default=None, primary_key=True)
    base_doc_id: str = Field(
        max_length=64,
        sa_column=Column("base_doc_id", Text, ForeignKey("document.doc_id", ondelete="CASCADE"), index=True),
    )  # 原配方
    variant_doc_id: str = Field(
        max_length=64,
        sa_column=Column("variant_doc_id", Text, ForeignKey("document.doc_id", ondelete="CASCADE"), index=True),
    )  # 变体配方
    variant_note: str = Field(default="", max_length=200)  # 变体说明
    created_at: datetime = Field(default_factory=_now_utc)


class AuditLog(SQLModel, table=True):
    """M2-08：审计日志。

    记录关键写操作（login / import / delete / seed / ask 采样 10%），
    供管理员查询。设计要点：
    - meta_json 用 Text 存 JSON 字符串，避免 schema 演进时迁移成本
    - user 从 JWT payload.sub 解析，未启用认证时为 "anonymous"
    - 写入失败不影响主业务（吞异常 + log warning）
    """

    id: int | None = Field(default=None, primary_key=True)
    action: str = Field(index=True, max_length=32)  # login/import/delete/seed/ask/...
    target_type: str = Field(default="", max_length=32, index=True)  # document/user/recipe/query
    target_id: str = Field(default="", max_length=128)  # doc_id / user_id / log_id
    user: str = Field(default="anonymous", max_length=64, index=True)
    meta_json: str = Field(default="{}", sa_column=Column("meta_json", Text))
    created_at: datetime = Field(default_factory=_now_utc, index=True)


class RecipeRating(SQLModel, table=True):
    """V2-Task6：配方评分与调酒笔记。

    用户对配方的评分（1-5 星）+ 文字笔记（替代材料、口感调整、心得）。
    - 同一用户对同一配方仅保留一条记录（UNIQUE 约束），再次评分 UPSERT 更新
    - user 未启用认证时为 "anonymous"，启用后为 JWT payload.sub
    - comment 允许空串（仅评分无笔记）
    """

    __table_args__ = (
        UniqueConstraint("doc_id", "user", name="uq_recipe_rating_doc_user"),
    )

    id: int | None = Field(default=None, primary_key=True)
    doc_id: str = Field(
        max_length=64,
        sa_column=Column("doc_id", Text, ForeignKey("document.doc_id", ondelete="CASCADE"), index=True),
    )
    user: str = Field(default="anonymous", max_length=64, index=True)
    score: int = Field(default=0, ge=0, le=5)  # 0-5 星（0 表示仅笔记无评分）
    comment: str = Field(default="", sa_column=Column("comment", Text))
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


# ---------------------------------------------------------------------------
# V3-Task9：多用户数据模型
# ---------------------------------------------------------------------------
# 角色层级：owner > member > viewer
# - owner: 团队所有者，可生成邀请码、管理成员、审核 UGC（原 admin 升级）
# - member: 团队成员，可创建/编辑自己的 UGC、评分、提问
# - viewer: 只读成员，仅可浏览/搜索/提问，不能创建 UGC
USER_ROLES = ("owner", "member", "viewer")


class User(SQLModel, table=True):
    """V3-Task9：用户表（多用户协作）。

    - 启用 KB_MULTIUSER 后，登录改为用户名+密码（校验 password_hash）
    - 未启用时，仍走旧的单用户密码模式（KB_AUTH_PASSWORD），本表不生效
    - username 唯一约束，password_hash 使用 pbkdf2_hmac(sha256) + 随机 salt
    - role 为 owner/member/viewer 之一
    """

    __table_args__ = (
        UniqueConstraint("username", name="uq_user_username"),
    )

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=64, index=True)
    password_hash: str = Field(default="", sa_column=Column("password_hash", Text))
    role: str = Field(default="member", max_length=16, index=True)  # owner/member/viewer
    # 邀请人（owner 用户名），用于追溯团队关系；自注册为空
    invited_by: str = Field(default="", max_length=64)
    is_active: bool = Field(default=True)  # 软禁用：False 时拒绝登录
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)


class InviteCode(SQLModel, table=True):
    """V3-Task10：邀请码表（owner 生成，一次性使用）。

    - code: 随机生成的邀请码（URL 安全）
    - role: 注册后分配的角色（member/viewer，不允许邀请 owner）
    - created_by: 生成邀请码的 owner 用户名
    - used_by: 使用者用户名（NULL 表示未使用）
    - expires_at: 过期时间（NULL 表示永久有效）
    """

    __table_args__ = (
        UniqueConstraint("code", name="uq_invite_code"),
    )

    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(max_length=64, index=True)
    role: str = Field(default="member", max_length=16)  # member/viewer
    created_by: str = Field(default="", max_length=64, index=True)
    used_by: str | None = Field(default=None, max_length=64)
    expires_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now_utc)
    used_at: datetime | None = Field(default=None)
