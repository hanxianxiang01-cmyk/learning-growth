from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Learning Engine 配置，从环境变量 / .env 读取。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Learning Engine"
    debug: bool = False

    # QA-ITEM-01 R2 §二：selection-trace 调试入口**生产默认不启用**。
    # 仅 QA 环境显式设 SELECTION_TRACE_ENABLED=true 开放（403 QA-child 守卫
    # 之外再加一道部署面开关——trace 暴露孩子能力画像，属调试面而非业务面）。
    selection_trace_enabled: bool = False

    # 数据库连接（postgresql+psycopg://），由环境变量 DATABASE_URL 注入
    database_url: str = "postgresql+psycopg://user:CHANGE_ME@localhost:5432/db"

    # CORS 白名单：同时允许 localhost 与 127.0.0.1（前端 dev server 两套地址都可能用）
    # 3100/3101 = B5 E2E harness 专用实例（exploration-lab / healing 双皮肤）
    # 3102 = V6 UI worktree 联调实例（feat/FE-1445 分支，10-29 起）
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3101",
        "http://127.0.0.1:3101",
        "http://localhost:3102",
        "http://127.0.0.1:3102",
    ]

    # ---- 游客模式（V1.4 纯游客模式设计方案）----

    # 学习数据保留期（方案 4.1「最长保留 7 天」）。从最后一次有效学习活动起算。
    guest_retention_days: int = 7

    # 会话有效期。与数据保留期同名同长，避免「会话还在、数据没了」的错位体验。
    guest_session_days: int = 7

    # Cookie 的 Secure 属性。本地 http 调试必须 False——否则浏览器不保存 cookie，
    # 表现为「每次刷新都变新游客」。生产 HTTPS 部署时置 true。
    guest_cookie_secure: bool = False

    # 每日题数**不再设上限**（2026-11-01 产品决策：取消每日 30 题硬限制）。
    # 学习量改由「本轮任务」决定，孩子想多练一会儿不再被 429 挡住。
    # 注意：这里不要重新引入 daily limit —— 防滥用靠下面的频率限流 +
    # submission_id 幂等 + 台账主键去重，而不是靠限制孩子一天能学多少。

    # 接口限流（滑动窗口，按 child_id 计）。阈值是「防脚本刷接口」的量级，
    # 不是学习量限制：正常作答 1 分钟到不了 20 次提交，孩子不会撞到。
    submit_rate_limit_per_minute: int = 20
    next_task_rate_limit_per_minute: int = 40

    # 活动统计与保留期换算的**固定时区**（原「每日计数」口径，现只用于
    # 「今天做了几道题」这类真实作答数展示，不再参与准入判断）。
    # 用 IANA 名称而非 offset，夏令时地区也不会漂。
    guest_quota_timezone: str = "Asia/Shanghai"

    # 清理任务开关。方案 4.3 要求「定时任务实际运行」，故默认开启；
    # 设 false 仅用于「故意停机」的故障演练，不用于绕过验收。
    guest_cleanup_enabled: bool = True

    # 清理任务的触发间隔（秒）。默认 1 小时：7 天保留期下，1 小时误差可接受，
    # 又能在验收时不必等一整天。
    guest_cleanup_interval_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()