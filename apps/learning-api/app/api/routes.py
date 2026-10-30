"""Learning Engine 业务路由聚合。

注意：`curriculum.router` 的 `/learning/tasks/next` 与 `learning.router` 的
`/learning/tasks/next` 路径完全相同，且它从未被注册过（历史死代码）。
**不要把它加进来**——注册后两个 handler 撞同一路径，先注册者生效，
`/tasks/next` 会静默换成 curriculum 实现，选题逻辑整体改变。
本次游客模式改造只动 `learning.router` 里的那个。
"""
from fastapi import APIRouter

from app.api import content, diagnosis, growth, guest, learning, mastery, planning, profile

api_router = APIRouter(prefix="/v1")
api_router.include_router(learning.router)
api_router.include_router(mastery.router)
api_router.include_router(diagnosis.router)
api_router.include_router(profile.router)
api_router.include_router(planning.router)
api_router.include_router(growth.router)
api_router.include_router(content.router)
api_router.include_router(guest.router)