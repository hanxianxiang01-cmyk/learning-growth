# ADR-0002｜Frontend Does Not Own Mastery

**Status:** Accepted

## Context
儿童端需要展示能力状态，但教育判断必须保持一致、可审计。

## Decision
前端不计算：
- Mastery
- Diagnosis
- Ability Level

前端只展示 Learning Engine / authoritative result 返回的数据。

## Consequence
任何试图通过前端 attempt/hint 数量直接推导能力等级的实现都应被拒绝。
