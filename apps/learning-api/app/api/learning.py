"""Learning 编排路由 —— 严格对齐冻结 OpenAPI /v1/learning/*。

签名以 02_openapi_v1.3.1.yaml 为准。

**游客模式改造（V1.4）**：身份只来自会话（deps.require_guest），不再信任
body / query 里的 child_id。方案 3.2「前端传入的 guest_id 不能直接作为授权依据」
的落点就是这里——请求体里若仍带 child_id，只被当作「要求操作的资源标识」，
必须与会话身份相等，否则 404。

冻结契约的**请求体字段一个没删**（body 里的 child_id 仍可传，只是不再有授权效力），
故前端不改也不会 422；但真正安全的调用方应当不再传它。
"""
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import GuestContext, assert_owns_child, require_guest
from app.core.config import get_settings
from app.core.database import get_db
from app.core.qa import is_qa_child
from app.services import guest_quota
from app.services.guest import touch_activity
from app.services.learning import (
    assign_next_task,
    request_hint,
    start_session,
    submit_attempt,
    trace_next_selection,
)
from app.services.session_result import get_session_result
from app.services.turn_service import SubmissionConflict

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/selection-trace")
async def selection_trace(
    child_id: str = "",
    session_id: str = "",
    ability_id: str | None = None,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """QA-ITEM-01 只读选题追踪（QA-ITEM-01 §4.2『新增 QA-only 只读追踪，不改变排序行为』）。

    安全门禁（R2 §二收口，双层）：
    1. **部署面**：`SELECTION_TRACE_ENABLED` 默认 false——生产不启用调试入口；
       未启用一律 404（不暴露端点存在性）。
    2. **目标面**：`is_qa_child` 403（与 pin 同红线）。如实声明：这校验的是
       *目标 child 属于 QA 池*，**不是调用者身份鉴权**（本服务当前无调用者
       认证体系）——故本端点只允许在 QA/内网环境开启；输出不含答案字段
       （候选池元数据=题目 rvid/难度/标题+该 child 画像），答案泄露风险=0。
    纯读，不落 TaskInstance、零写入。QA 侧与真实 tasks/next 对账。
    """
    if not get_settings().selection_trace_enabled:
        raise HTTPException(status_code=404)
    if not is_qa_child(child_id):
        raise HTTPException(status_code=403, detail="selection-trace 仅限 QA 测试池 child 使用")
    # 游客模式下再加一道：QA child 不是「你的」，也不许看（游客身份 ≠ QA 调试身份）
    await assert_owns_child(
        db, guest_child_id=guest.child_id, target_child_id=uuid.UUID(str(child_id))
    )
    try:
        return await trace_next_selection(
            db,
            child_id=uuid.UUID(str(child_id)),
            session_id=uuid.UUID(str(session_id)),
            ability_id=ability_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/sessions/{session_id}/result")
async def session_result(
    session_id: uuid.UUID,
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """读取一次 session 的真实学习结果（服务端聚合，非前端快照）。

    这是冻结 OpenAPI 之外新增的只读聚合接口；不修改任何已有冻结端点。

    归属：session 必须属于当前游客。原实现只按 session_id 查，改 id 就能看
    别人的会话结果——方案 3.2 点名的正是这一类。
    """
    try:
        result = await get_session_result(db, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    await assert_owns_child(
        db,
        guest_child_id=guest.child_id,
        target_child_id=uuid.UUID(str(result["child_id"])),
    )
    return result


@router.post("/sessions", status_code=201)
async def create_session(
    payload: dict[str, Any] = Body(...),
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """开始学习 session（对齐 OpenAPI，body 传参）。

    游客模式：child_id 一律用会话身份。请求体若带了不同的 child_id，
    说明调用方在试图以别人身份开课 → 404（方案 3.2 归属校验）。
    """
    subject = payload.get("subject")
    if not subject:
        raise HTTPException(status_code=422, detail="subject 为必填字段")

    claimed = payload.get("child_id")
    if claimed:
        try:
            await assert_owns_child(
                db, guest_child_id=guest.child_id, target_child_id=uuid.UUID(str(claimed))
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="资源不存在")

    return await start_session(
        db,
        child_id=guest.child_id,
        subject=subject,
        requested_minutes=payload.get("requested_minutes"),
        plan_id=payload.get("plan_id"),
    )


@router.post("/tasks/next")
async def next_task(
    payload: dict[str, Any] = Body(...),
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """取下一题（对齐 OpenAPI；可选 ability_id：由前端挑战卡片显式指定能力，否则后端自选）。

    pin_resource_version_id（FE-1422a QA 确定性钉题）：**仅限 QA child**。
    真实 child 携带该参数 → 403（生产选题路径不允许测试机制侵入）。

    游客模式：child_id 用会话身份；session 必须属于当前游客，否则 404——
    否则改一个 session_id 就能往别人的会话里塞题。
    """
    claimed = payload.get("child_id")
    if claimed:
        try:
            await assert_owns_child(
                db, guest_child_id=guest.child_id, target_child_id=uuid.UUID(str(claimed))
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="资源不存在")

    pin_raw = payload.get("pin_resource_version_id")
    pin = uuid.UUID(str(pin_raw)) if pin_raw else None
    if pin is not None and not is_qa_child(str(guest.child_id)):
        raise HTTPException(status_code=403, detail="pin_resource_version_id 仅限 QA 测试池 child 使用")

    # 归属：session 必须属于当前游客（docstring 承诺过，10-29 验收 3.4 抓到没实现）。
    # 不校验的后果：改一个 session_id 就能往别人的会话里塞题——task_instance 会
    # 落成 (session_id=别人的, child_id=自己的)，污染对方会话的 completed_count，
    # 且绕开对方配额不计数。404 而非 403：不泄露「该 session 存在但不是你的」。
    try:
        session_uuid = uuid.UUID(str(payload["session_id"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail="资源不存在")
    session_owner = await _session_owner(db, session_uuid)
    if session_owner is None:
        raise HTTPException(status_code=404, detail="资源不存在")
    await assert_owns_child(
        db, guest_child_id=guest.child_id, target_child_id=session_owner
    )

    try:
        return await assign_next_task(
            db,
            child_id=str(guest.child_id),
            session_id=payload["session_id"],
            subject=payload["subject"],
            requested_minutes=payload.get("requested_minutes"),
            ability_id=payload.get("ability_id"),
            pin_resource_version_id=pin,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/attempts")
async def submit(
    payload: dict[str, Any] = Body(...),
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """提交作答（对齐 OpenAPI，无 child_id，后端反查）。

    游客模式三件事（方案 3.2 + 第五章）：
    1. **归属**：先确认 task 属于当前游客，否则 404（改 task_instance_id 不能
       往别人会话里写答案，也不能借此判分别人的题）。
    2. **配额**：超过当日上限 → 429（LE-4291）。判定顺序是「先看是不是老题」，
       避免第 30 题的重试被误拒（详见 services/guest_quota.is_over_limit）。
    3. **活动刷新**：成功提交后刷新保留期（方案 4.1 的 last_activity_at）。
    """
    task_instance_id = payload["task_instance_id"]
    claimed = payload.get("child_id")
    if claimed:
        try:
            await assert_owns_child(
                db, guest_child_id=guest.child_id, target_child_id=uuid.UUID(str(claimed))
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="资源不存在")

    # 归属：task → child_id 必须等于会话身份
    try:
        task_uuid = uuid.UUID(str(task_instance_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="task_instance 不存在")
    owner = await _task_owner(db, task_uuid)
    if owner is None:
        raise HTTPException(status_code=404, detail="task_instance 不存在")
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=owner)

    # 配额：超限 429（方案第五章「达到上限时，显示清晰提示」）
    if await guest_quota.is_over_limit(
        db, child_id=guest.child_id, task_instance_id=task_uuid
    ):
        usage = await guest_quota.usage_summary(db, child_id=guest.child_id)
        # 提示语里的题数必须与 usage["limit"] 同源（配置 guest_daily_task_limit）。
        # 曾经硬编码「30」：配置改成 15 时文案会说谎（形态 40：文案与数据不同源）。
        raise HTTPException(
            status_code=429,
            detail={
                "code": "LE-4291",
                "message": f"今天已经完成 {usage['limit']} 道题啦，明天再来吧",
                "quota": usage,
            },
        )

    try:
        sub_raw = payload.get("submission_id")
        submission_id = uuid.UUID(str(sub_raw)) if sub_raw else None
        result = await submit_attempt(
            db,
            task_instance_id=task_instance_id,
            attempt_no=int(payload.get("attempt_no", 1)),
            response=payload.get("response", {}),
            client_elapsed_ms=payload.get("client_elapsed_ms"),
            used_hint_levels=payload.get("used_hint_levels", []),
            submission_id=submission_id,
        )
    except SubmissionConflict as e:
        # docs/frontend/29 §3：同 submission_id 不同内容 → 409（不得当新提交/不得 404）
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, AttributeError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 只有真的判分了才算「一次有效学习活动」：重复提交/幂等重放不刷新保留期，
    # 也不重复计题（台账主键保证）。
    await guest_quota.record_task_consumed(
        db, child_id=guest.child_id, task_instance_id=task_uuid
    )
    await touch_activity(db, child_id=guest.child_id)
    await db.commit()
    return result


async def _task_owner(db: AsyncSession, task_instance_id: uuid.UUID) -> uuid.UUID | None:
    """task_instance → child_id。为空说明任务不存在。"""
    from app.models import TaskInstance

    return (
        await db.execute(
            select(TaskInstance.child_id).where(
                TaskInstance.task_instance_id == task_instance_id
            )
        )
    ).scalar_one_or_none()


async def _session_owner(db: AsyncSession, session_id: uuid.UUID) -> uuid.UUID | None:
    """learning_session → child_id。为空说明会话不存在。

    10-29 验收 3.4 发现 next_task 缺这道校验（docstring 承诺了但没实现）：
    不校验则任何登录游客可往他人会话塞题，落成
    task_instance(session_id=别人的, child_id=自己的)，污染对方会话统计
    且绕开对方配额。与 _task_owner 同源同语义。
    """
    from app.models import LearningSession

    return (
        await db.execute(
            select(LearningSession.child_id).where(
                LearningSession.session_id == session_id
            )
        )
    ).scalar_one_or_none()


@router.post("/hints")
async def hint(
    payload: dict[str, Any] = Body(...),
    guest: GuestContext = Depends(require_guest),
    db: AsyncSession = Depends(get_db),
):
    """受控 Hint（对齐 OpenAPI，attempt_id → 反查资源 hint 阶梯）。

    游客模式：attempt → task → child 必须属于当前游客。提示阶梯含解题思路，
    改一个 attempt_id 就能读到别人题目的提示——归属校验不是可选项。
    """
    try:
        attempt_uuid = uuid.UUID(str(payload["attempt_id"]))
    except (KeyError, ValueError):
        raise HTTPException(status_code=404, detail="attempt 不存在")

    owner = await _attempt_owner(db, attempt_uuid)
    if owner is None:
        raise HTTPException(status_code=404, detail="attempt 不存在")
    await assert_owns_child(db, guest_child_id=guest.child_id, target_child_id=owner)

    try:
        return await request_hint(
            db,
            attempt_id=payload["attempt_id"],
            requested_level=payload.get("requested_level"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def _attempt_owner(db: AsyncSession, attempt_id: uuid.UUID) -> uuid.UUID | None:
    """attempt → task_instance → child_id。"""
    from app.models import Attempt, TaskInstance

    return (
        await db.execute(
            select(TaskInstance.child_id)
            .join(Attempt, Attempt.task_instance_id == TaskInstance.task_instance_id)
            .where(Attempt.attempt_id == attempt_id)
        )
    ).scalar_one_or_none()