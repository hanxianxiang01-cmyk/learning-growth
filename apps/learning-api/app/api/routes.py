"""Learning Engine 业务路由聚合。"""
from fastapi import APIRouter

from app.api import diagnosis, growth, learning, mastery, planning, profile

api_router = APIRouter(prefix="/v1")
api_router.include_router(learning.router)
api_router.include_router(mastery.router)
api_router.include_router(diagnosis.router)
api_router.include_router(profile.router)
api_router.include_router(planning.router)
api_router.include_router(growth.router)