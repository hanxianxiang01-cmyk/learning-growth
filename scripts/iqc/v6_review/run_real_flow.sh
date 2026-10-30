#!/usr/bin/env bash
# FE-1445 复审：真实数据端到端一键复核（跑到生产库，严格零残留）。
#
# 顺序：guard(无遗留) → before 快照 → 浏览器真实流程 → 库里证据链核对
#      → 精确清理本轮游客 → after 快照 → 零残留对账
#
# 关键：清理放在「证据核对之后、终态对账之前」。任何一步失败都仍会清理，
# 否则失败一次就在生产库留一个游客。
#
# 用法：
#   export DATABASE_URL="postgresql://..."
#   MAIN_REPO=<主仓库绝对路径> bash scripts/iqc/v6_review/run_real_flow.sh
#
# 退出码：0 = 全部通过且零残留；1 = 有断言不通过；2 = 环境未就绪。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_DIR="$ROOT/output/v6_review"
PY="${REVIEW_PYTHON:-/Users/hanxianxiang/.workbuddy/binaries/python/envs/learning-engine/bin/python}"
NODE_BIN="${REVIEW_NODE:-/Users/hanxianxiang/.workbuddy/binaries/node/versions/$(cat /Users/hanxianxiang/.workbuddy/binaries/node/versions/current)/bin/node}"
BASE="${REVIEW_BASE:-http://127.0.0.1:3102}"
MAIN_REPO="${MAIN_REPO:?需要设置 MAIN_REPO=<主仓库绝对路径>（guest 后端代码在那里）}"

mkdir -p "$OUT_DIR"
RC=0

say() { printf '\n=== %s ===\n' "$1"; }

say "0. 环境检查"
if ! curl -s -o /dev/null -m 3 "$BASE/child/math"; then
  echo "前端未就绪：$BASE"; exit 2
fi
if ! curl -s -o /dev/null -m 3 "http://127.0.0.1:8000/v1/content/v2-catalog"; then
  echo "后端未就绪：http://127.0.0.1:8000"; exit 2
fi
"$PY" "$ROOT/scripts/iqc/v6_review/db_snapshot.py" guard || exit 2

say "1. 采集基线快照"
"$PY" "$ROOT/scripts/iqc/v6_review/db_snapshot.py" capture --out "$OUT_DIR/db_before.json" || exit 2

say "2. 浏览器真实流程（不拦截任何请求）"
"$NODE_BIN" "$ROOT/scripts/iqc/v6_review/real_flow_e2e.mjs" --base "$BASE" --out "$OUT_DIR/real_flow_run.json" \
  || RC=1

say "3. 库里证据链核对（清理之前）"
if [ -f "$OUT_DIR/real_flow_run.json" ]; then
  "$PY" "$ROOT/scripts/iqc/v6_review/db_verify_flow.py" "$OUT_DIR/real_flow_run.json" || RC=1
else
  echo "缺少 run.json，跳过证据核对"; RC=1
fi

say "4. 精确清理本轮游客"
if [ -f "$OUT_DIR/real_flow_run.json" ]; then
  PYTHONPATH="$MAIN_REPO/apps/learning-api" \
    "$PY" "$ROOT/scripts/iqc/v6_review/db_purge.py" --from-run "$OUT_DIR/real_flow_run.json" || RC=1
else
  echo "缺少 run.json：无法确定要清理哪个游客，请手工检查 guest_identity"; RC=1
fi

say "5. 终态快照与零残留对账"
"$PY" "$ROOT/scripts/iqc/v6_review/db_snapshot.py" capture --out "$OUT_DIR/db_after.json" \
  && "$PY" "$ROOT/scripts/iqc/v6_review/db_snapshot.py" compare "$OUT_DIR/db_before.json" "$OUT_DIR/db_after.json" \
  || RC=1

say "结果"
if [ "$RC" -eq 0 ]; then echo "全部通过，零残留"; else echo "存在失败项，见上方 FAIL"; fi
exit "$RC"
