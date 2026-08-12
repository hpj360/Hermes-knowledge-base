"""FastAPI 应用：知识库 API + 静态前端托管。

本模块只负责应用装配：CORS 中间件、结构化请求日志、全局异常处理器、APIRouter
注册与静态文件挂载。端点实现按功能域拆分到 :mod:`hermes_kb.api` 下的各 router
模块，共享依赖（认证、年龄门、JWT 工具、RAG/Import 服务）位于
:mod:`hermes_kb.api.deps`。

- /api/health        liveness 探针
- /api/health/ready  readiness 探针（DB 连通性，失败返回 503）
- /api/documents 文档管理
- /api/ask 问答；/api/ask/stream SSE 流式问答
- /api/history 问答历史；/api/feedback 反馈
- /api/seed 种子数据初始化
- /api/auth/* 认证；/api/age-gate/* 年龄门
- /api/lab/* 鸡尾酒实验室
- / 静态前端（单进程部署）
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from hermes_kb.api.ask import router as ask_router
from hermes_kb.api.audit import router as audit_router
from hermes_kb.api.auth import router as auth_router
from hermes_kb.api.deps import (
    jwt_decode,  # noqa: F401  re-export（tests/test_kb/test_m1.py 仍从本模块导入）
    jwt_encode,  # noqa: F401
)
from hermes_kb.api.documents import router as documents_router
from hermes_kb.api.export import router as export_router
from hermes_kb.api.health import router as health_router
from hermes_kb.api.lab import router as lab_router
from hermes_kb.api.obsidian import router as obsidian_router
from hermes_kb.api.stats import router as stats_router
from hermes_kb.api.tags import router as tags_router
from hermes_kb.config import get_settings
from hermes_kb.rag import ImportService, RAGEngine

# 请求日志器（与 uvicorn access log 解耦，便于独立调整级别 / 格式）
_access_log = logging.getLogger("hermes_kb.access")


def create_app() -> FastAPI:
    """构造 FastAPI 应用。"""
    settings = get_settings()

    app = FastAPI(
        title="Hermes Knowledge Base",
        description="AI 原生酒类知识库（M0+M1）",
        version="0.5.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # P1-4: CORS 规范禁止 "*" + allow_credentials=True 同时出现（浏览器会拒绝）。
        # 通配符时关闭 credentials，具体 origin 列表时才开启。
        allow_credentials="*" not in settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 应用级服务实例：每个 app 独立持有，避免跨测试 settings/engine 复位互相污染。
    app.state.rag = RAGEngine()
    app.state.importer = ImportService()

    # -----------------------------------------------------------------------
    # 结构化请求日志中间件：method/path/status/latency_ms/correlation_id
    # - 仅记录 /api/ 开头的请求，避免静态资源噪声
    # - 5xx 单独 warning 级别，便于告警
    # - correlation_id 同时写入响应头，方便客户端上报问题
    # -----------------------------------------------------------------------
    @app.middleware("http")
    async def access_log_middleware(request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex[:8]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = int((time.perf_counter() - start) * 1000)
            _access_log.warning(
                "access method=%s path=%s status=500 latency_ms=%d cid=%s error=unhandled",
                request.method,
                request.url.path,
                latency_ms,
                correlation_id,
            )
            raise

        latency_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Correlation-ID"] = correlation_id
        level = logging.WARNING if response.status_code >= 500 else logging.INFO
        _access_log.log(
            level,
            "access method=%s path=%s status=%d latency_ms=%d cid=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            correlation_id,
        )
        return response

    # -----------------------------------------------------------------------
    # 全局异常处理（必须注册在 app 级别）
    # -----------------------------------------------------------------------
    @app.exception_handler(ValueError)
    async def _value_error_handler(_request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "bad_request", "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def _generic_error_handler(_request: Request, exc: Exception):
        correlation_id = uuid.uuid4().hex[:8]
        logging.getLogger("hermes_kb").exception("unhandled exception (correlation_id=%s)", correlation_id)
        if settings.debug:
            detail: str = str(exc)
        else:
            detail = f"internal error, correlation_id={correlation_id}"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal",
                "detail": detail,
                "correlation_id": correlation_id,
            },
        )

    # -----------------------------------------------------------------------
    # 路由注册（端点路径与拆分前完全一致，prefix 由各 router 自带）
    # -----------------------------------------------------------------------
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(tags_router)
    app.include_router(ask_router)
    app.include_router(auth_router)
    app.include_router(lab_router)
    app.include_router(audit_router)
    app.include_router(stats_router)
    app.include_router(export_router)
    app.include_router(obsidian_router)

    # -----------------------------------------------------------------------
    # 静态文件挂载（单进程部署，必须最后）
    # -----------------------------------------------------------------------
    web_dist = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
    if web_dist.exists() and web_dist.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=str(web_dist), html=True),
            name="web",
        )

    return app


# 模块级实例（uvicorn 直接引用 hermes_kb.app:app）
app = create_app()


def main() -> None:
    """CLI 启动入口。"""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "hermes_kb.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
