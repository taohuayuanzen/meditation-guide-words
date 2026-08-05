#!/usr/bin/env bash
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
echo "Project root: $ROOT"

# 1. 检查 Dify 是否运行（后续 T3 完善）
echo "[TODO] 检查 Dify 运行状态"

# 2. 启动后端（后台）
echo "[TODO] 启动 FastAPI 后端"

# 3. 启动音频 Worker（后台）
echo "[TODO] 启动音频 Worker"

# 4. 启动前端
echo "[TODO] 启动前端"

wait
