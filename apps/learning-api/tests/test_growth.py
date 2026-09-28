"""GrowthService 单元测试 —— 样本不足观察中、证据引用、下一阶段重点。"""
import uuid
from datetime import date

from app.services.growth import report_to_dict, build_snapshot

# 纯逻辑部分用假对象测试（不连库），DB 集成在端到端验收里覆盖