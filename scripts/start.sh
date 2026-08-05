#!/usr/bin/env bash
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)

# Dify 目录：环境变量 DIFY_DIR 优先，否则自动探测常见路径
DIFY_DIR="${DIFY_DIR:-}"
if [ -z "$DIFY_DIR" ]; then
  for cand in \
    "D:/project/github/dify" \
    "C:/projects/github/dify" \
    "$HOME/github/dify" \
    "$HOME/projects/github/dify" \
    C:/projects/github/dify/dify-*; do
    if [ -f "$cand/docker/docker-compose.yml" ]; then
      DIFY_DIR="$cand"
      break
    fi
  done
fi

echo "Project root: $ROOT"
echo "Dify dir: ${DIFY_DIR:-（未找到，请设置 DIFY_DIR 环境变量）}"

# 检查 Dify 是否运行
if curl -s -o /dev/null --max-time 5 http://localhost/; then
  echo "Dify 已在运行。"
else
  if [ -n "$DIFY_DIR" ]; then
    echo "Dify 未运行，尝试启动..."
    cd "$DIFY_DIR/docker"
    docker compose up -d
    echo "等待 Dify 启动..."
    sleep 15
    cd "$ROOT"
  else
    echo "警告：未找到 Dify 目录，请手动启动 Dify 后重新运行本脚本。"
  fi
fi

# 启动后端
cd "$ROOT/backend"
uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# 启动 Worker
uv run python -m app.services.audio_worker &
WORKER_PID=$!

# 启动前端
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "服务已启动："
echo "  前端:  http://localhost:5173"
echo "  后端:  http://localhost:8000"
echo "  Dify:  http://localhost"
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $WORKER_PID $FRONTEND_PID" EXIT
wait
