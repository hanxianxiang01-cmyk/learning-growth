"""诊断路由。"""
from fastapi import APIRouter, Body

from app.services.diagnosis import diagnose

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


@router.post("/")
async def run_diagnosis(
    payload: dict = Body(...),
):
    """对一次作答产出诊断（E01~E07）。"""
    correct = payload.get("correct")
    error_model = payload.get("error_model")
    used_hint_levels = payload.get("used_hint_levels", [])
    repeated_pattern = payload.get("repeated_pattern", False)

    d = diagnose(
        correct,
        error_model=error_model,
        used_hint_levels=used_hint_levels,
        repeated_pattern=repeated_pattern,
    )
    if d is None:
        return {"diagnosis": None}
    return {"diagnosis": d.to_dict()}