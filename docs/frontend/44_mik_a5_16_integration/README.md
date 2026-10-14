# MIK-A5 16 Renderer 一体化复审入口

见 [`INTEGRATION_REVIEW.md`](./INTEGRATION_REVIEW.md)。

输入基线：`FE1445_V6_Full_Source_504a93d.zip`；SAFE-01 Router：`MIK_SAFE01_Spike_Candidate_Source_2026-10-13.zip`。

一套交付：本目录审批边界 + 所有 16 个 Renderer 的新增 React 交互接线 + 新增 CI 领域测试门。默认 legacy；不影响 main / PR #87。

原有 `docs/frontend/43_safe01_router_spike/` 原样保留，未用旧版覆盖纠偏版。
