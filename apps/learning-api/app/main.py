"""FastAPI 应用入口。

游客模式（V1.4）：新增 lifespan 内的清理定时任务。方案 4.3 要求
「定时任务实际运行，而不是只通过单元测试」，故这里真的起一个后台循环，
每轮写 `guest_cleanup_run` 运行记录——验收时可直接 SQL 核对。
"""
import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)


async def _cleanup_loop(stop: asyncio.Event) -> None:
    """按固定间隔跑清理。单轮失败不退出——否则一次数据库抖动就永久停摆。"""
    from app.services.guest_cleanup import run_cleanup

    interval = settings.guest_cleanup_interval_seconds
    logger.info("guest cleanup loop started, interval=%ss", interval)
    while not stop.is_set():
        try:
            async with AsyncSessionLocal() as db:
                summary = await run_cleanup(db)
            logger.info(
                "guest cleanup done: scanned=%s purged=%s failed=%s status=%s",
                summary["scanned"],
                summary["purged"],
                summary["failed"],
                summary.get("status"),
            )
        except Exception:  # noqa: BLE001
            logger.exception("guest cleanup round failed")
        # 用 wait 而不是 sleep：应用关闭时能立即退出，不必等满一个周期
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)
    logger.info("guest cleanup loop stopped")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task: asyncio.Task | None = None
    if settings.guest_cleanup_enabled:
        task = asyncio.create_task(_cleanup_loop(stop))
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(api_router)


@app.get("/", tags=["root"])
def root() -> dict:
    return {"service": settings.app_name, "status": "ok"}