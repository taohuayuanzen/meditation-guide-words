@echo off
setlocal

set "ROOT=%~dp0.."

:: Dify 目录：环境变量 DIFY_DIR 优先，否则探测常见路径
if "%DIFY_DIR%"=="" (
  if exist "C:\projects\github\dify\dify-1.16.1\docker\docker-compose.yml" set "DIFY_DIR=C:\projects\github\dify\dify-1.16.1"
  if not defined DIFY_DIR if exist "C:\projects\github\dify\docker\docker-compose.yml" set "DIFY_DIR=C:\projects\github\dify"
  if not defined DIFY_DIR if exist "D:\project\github\dify\docker\docker-compose.yml" set "DIFY_DIR=D:\project\github\dify"
  if not defined DIFY_DIR if exist "%USERPROFILE%\github\dify\docker\docker-compose.yml" set "DIFY_DIR=%USERPROFILE%\github\dify"
)

echo Project root: %ROOT%
if defined DIFY_DIR (
  echo Dify dir: %DIFY_DIR%
) else (
  echo Dify dir: 未找到，请设置 DIFY_DIR 环境变量
)

:: 检查 Dify 是否运行
curl -s -o NUL --max-time 5 http://localhost/
if errorlevel 1 (
  if defined DIFY_DIR (
    echo Dify 未运行，尝试启动...
    pushd "%DIFY_DIR%\docker"
    docker compose up -d
    popd
    echo 等待 Dify 启动...
    timeout /t 15 /nobreak >nul
  ) else (
    echo 警告：未找到 Dify 目录，请手动启动 Dify 后重新运行本脚本。
  )
) else (
  echo Dify 已在运行。
)

:: 启动后端 / Worker / 前端（默认开启 DEBUG 日志，便于排查 TTS 等问题）
set LOG_LEVEL=DEBUG
start "Backend" cmd /c "cd /d %ROOT%\backend && set LOG_LEVEL=DEBUG && uv run uvicorn app.main:app --reload --port 8000"
start "Worker" cmd /c "cd /d %ROOT%\backend && set LOG_LEVEL=DEBUG && uv run python -m app.services.audio_worker"
start "Frontend" cmd /c "cd /d %ROOT%\frontend && npm run dev"

echo.
echo 服务已启动：
echo   前端:  http://localhost:5173
echo   后端:  http://localhost:8000
echo   Dify:  http://localhost
echo 关闭本窗口不会停止子进程，请用任务管理器或关闭各自窗口停止。
pause
