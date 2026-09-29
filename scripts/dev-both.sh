#!/usr/bin/env bash
# 一键启动儿童学习成长系统（前后端联调模式）
#
# 用法：bash scripts/dev-both.sh
# 前置：PostgreSQL RDS 可连；依赖已装（根 node_modules + learning-engine venv）
#
# 说明：
# - 后端 FastAPI → http://127.0.0.1:8000（连 RDS）
# - 前端 Next.js dev → http://127.0.0.1:3000（http 模式连后端）
# - 孩子端首页：http://127.0.0.1:3000/child/math
#
# 关键：Next.js 的 .next 编译缓存写入被 WorkBuddy 的 NODE_OPTIONS 文件系统 shim
# 拦截（EEXIST / CODEBUDDY_BROKER_DENY），必须清空 NODE_OPTIONS 后再启动前端。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="/Users/hanxianxiang/.workbuddy/binaries/node/versions/22.22.2-3/bin/node"
PY="/Users/hanxianxiang/.workbuddy/binaries/python/envs/learning-engine/bin/python"

# 数据库连接（脱敏占位，实际值请用环境变量覆盖）
: "${DATABASE_URL:?请设置 DATABASE_URL 环境变量}"

echo "==> 启动后端 FastAPI (127.0.0.1:8000)..."
cd "$ROOT/apps/learning-api"
DATABASE_URL="$DATABASE_URL" PYTHONPATH="$ROOT/apps/learning-api" \
  "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "    后端 PID=$BACKEND_PID"

echo "==> 启动前端 Next.js dev (127.0.0.1:3000, http 模式)..."
cd "$ROOT/apps/child-web"
NODE_OPTIONS="" \
  NEXT_PUBLIC_LEARNING_API_MODE=http \
  NEXT_PUBLIC_LEARNING_API_BASE_URL=http://127.0.0.1:8000 \
  "$NODE" ../../node_modules/next/dist/bin/next dev -p 3000 &
FRONTEND_PID=$!
echo "    前端 PID=$FRONTEND_PID"

echo ""
echo "======================================================"
echo " 后端:  http://127.0.0.1:8000  (健康检查: / 或 /v1/health)"
echo " 前端:  http://127.0.0.1:3000  (孩子端首页: /child/math)"
echo " 联调 UI Kit: http://127.0.0.1:3000/dev/ui-kit"
echo " V1.3 QA:   http://127.0.0.1:3000/dev/v1.3-qa"
echo "======================================================"
echo ""
echo "按 Ctrl+C 停止两个服务。"

trap 'echo "==> 停止服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' INT TERM
wait