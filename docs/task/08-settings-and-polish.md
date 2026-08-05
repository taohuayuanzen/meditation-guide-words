# T8：设置页、测试、启动脚本与项目收尾

## 任务目标

实现设置页（LLM、TTS、Dify、通用配置），完善多语言切换，补充后端单元测试，完善一键启动脚本，更新 README 和相关文档，完成项目 MVP 收尾。

**预计耗时**：2 ~ 2.5 天

---

## 前置依赖

- T4 完成（设置 API 已就绪）
- T5 完成（TTS 适配与 Worker 已就绪）
- T6、T7 完成（前后端界面与核心功能已实现）

---

## 详细步骤

### 8.1 设置页组件

`frontend/src/components/settings/SettingsDialog.tsx`：

```tsx
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LLMSettings } from "./LLMSettings"
import { TTSSettings } from "./TTSSettings"
import { DifySettings } from "./DifySettings"
import { GeneralSettings } from "./GeneralSettings"

export function SettingsDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          ⚙️
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>设置</DialogTitle>
        </DialogHeader>
        <Tabs defaultValue="llm">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="llm">大模型</TabsTrigger>
            <TabsTrigger value="tts">语音合成</TabsTrigger>
            <TabsTrigger value="dify">Dify</TabsTrigger>
            <TabsTrigger value="general">通用</TabsTrigger>
          </TabsList>
          <TabsContent value="llm"><LLMSettings /></TabsContent>
          <TabsContent value="tts"><TTSSettings /></TabsContent>
          <TabsContent value="dify"><DifySettings /></TabsContent>
          <TabsContent value="general"><GeneralSettings /></TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
```

### 8.2 LLM 设置

`frontend/src/components/settings/LLMSettings.tsx`：

```tsx
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const PROVIDERS = [
  { value: "deepseek", label: "DeepSeek" },
  { value: "kimi", label: "Kimi" },
  { value: "custom", label: "自定义 OpenAI-Compatible" },
]

export function LLMSettings() {
  const [config, setConfig] = useState({
    provider: "deepseek",
    base_url: "",
    api_key: "",
    model: "",
    temperature: 0.7,
    max_tokens: undefined,
  })

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((data) => setConfig(data.llm_config))
  }, [])

  const handleSave = async () => {
    const settings = await fetch("/api/settings").then((r) => r.json())
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...settings, llm_config: config }),
    })
  }

  const handleTest = async () => {
    const res = await fetch("/api/settings/test-llm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    })
    const data = await res.json()
    alert(data.status === "ok" ? "连接成功" : `连接失败：${data.detail}`)
  }

  return (
    <div className="space-y-4 py-4">
      <div>
        <Label>供应商</Label>
        <Select
          value={config.provider}
          onValueChange={(v) => setConfig({ ...config, provider: v })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PROVIDERS.map((p) => (
              <SelectItem key={p.value} value={p.value}>
                {p.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label>API Base URL</Label>
        <Input
          value={config.base_url}
          onChange={(e) => setConfig({ ...config, base_url: e.target.value })}
          placeholder="https://api.deepseek.com/v1"
        />
      </div>
      <div>
        <Label>API Key</Label>
        <Input
          type="password"
          value={config.api_key}
          onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
        />
      </div>
      <div>
        <Label>模型名称</Label>
        <Input
          value={config.model}
          onChange={(e) => setConfig({ ...config, model: e.target.value })}
          placeholder="deepseek-chat"
        />
      </div>
      <div>
        <Label>温度（{config.temperature}）</Label>
        <Input
          type="range"
          min={0}
          max={2}
          step={0.1}
          value={config.temperature}
          onChange={(e) =>
            setConfig({ ...config, temperature: parseFloat(e.target.value) })
          }
        />
      </div>
      <div className="flex gap-2 pt-4">
        <Button onClick={handleTest} variant="outline">
          测试连接
        </Button>
        <Button onClick={handleSave}>保存</Button>
      </div>
    </div>
  )
}
```

### 8.3 TTS 设置

`frontend/src/components/settings/TTSSettings.tsx`：

类似 LLMSettings，字段包括：
- provider：volcano / aliyun / custom
- api_key
- secret_key（火山/阿里云部分接口需要）
- voice_id
- speed
- volume
- output_format

### 8.4 Dify 设置

`frontend/src/components/settings/DifySettings.tsx`：

字段包括：
- base_url
- script_app_key
- audio_app_key

> Dify 本身也使用 LLM，但 Dify 的模型配置在 Dify 后台完成，这里只保存连接本项目的两个应用的 API Key。

### 8.5 通用设置

`frontend/src/components/settings/GeneralSettings.tsx`：

字段包括：
- language：zh / en
- theme：light / dark
- audio_output_dir

语言切换：

```tsx
import { useTranslation } from "react-i18next"

const { i18n } = useTranslation()

const handleLanguageChange = (lang: string) => {
  i18n.changeLanguage(lang)
  setConfig({ ...config, language: lang })
}
```

### 8.6 后端设置保存逻辑完善

确保 `POST /api/settings` 能保存全部四个配置块，并在启动时正确读取。

### 8.7 测试连接接口完善

#### `/api/settings/test-llm`

```python
@router.post("/test-llm")
async def test_llm(config: LLMConfig):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {config.api_key}"},
            json={
                "model": config.model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    return {"status": "ok"}
```

#### `/api/settings/test-tts`

```python
@router.post("/test-tts")
async def test_tts(config: TTSConfig):
    service = get_tts_service(config.model_dump())
    if not service.is_available():
        raise HTTPException(status_code=400, detail="TTS config invalid")
    await service.synthesize("你好，这是一段测试音频。", config.voice_id)
    return {"status": "ok"}
```

### 8.8 后端单元测试补充

补充以下测试文件：
- `backend/tests/test_settings.py`
- `backend/tests/test_audio_tasks.py`

运行测试：

```bash
cd backend
uv run pytest
```

### 8.9 完善一键启动脚本

#### `scripts/start.sh`

```bash
#!/usr/bin/env bash
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DIFY_DIR="${DIFY_DIR:-D:/project/github/dify}"

echo "Project root: $ROOT"
echo "Dify dir: $DIFY_DIR"

# 检查 Dify 是否运行
if ! curl -s http://localhost/health > /dev/null; then
  echo "Dify 未运行，尝试启动..."
  cd "$DIFY_DIR/docker"
  docker-compose up -d
  echo "等待 Dify 启动..."
  sleep 15
fi

# 启动后端
cd "$ROOT/backend"
uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# 启动 Worker
cd "$ROOT/backend"
uv run python -m app.services.audio_worker &
WORKER_PID=$!

# 启动前端
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo "服务已启动："
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  Dify: http://localhost"
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $WORKER_PID $FRONTEND_PID" EXIT
wait
```

#### `scripts/start.bat`

```bat
@echo off
setlocal

set "ROOT=%~dp0.."
set "DIFY_DIR=%DIFY_DIR%"
if "%DIFY_DIR%"=="" set "DIFY_DIR=D:\project\github\dify"

echo Project root: %ROOT%
echo Dify dir: %DIFY_DIR%

:: 检查 Dify
curl -s http://localhost/health >nul 2>&1
if errorlevel 1 (
  echo Dify 未运行，尝试启动...
  cd /d "%DIFY_DIR%\docker"
  docker-compose up -d
  timeout /t 15 /nobreak >nul
)

:: 启动后端
start "Backend" cmd /c "cd /d %ROOT%\backend && uv run uvicorn app.main:app --reload --port 8000"

:: 启动 Worker
start "Worker" cmd /c "cd /d %ROOT%\backend && uv run python -m app.services.audio_worker"

:: 启动前端
start "Frontend" cmd /c "cd /d %ROOT%\frontend && npm run dev"

echo 服务已启动：
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   Dify: http://localhost
pause
```

### 8.10 README 更新

完善 README：
- 安装前置：Docker、Python 3.11、Node.js 18、uv
- 安装步骤
- 启动方式（一键脚本）
- 首次使用配置 LLM/TTS/Dify
- 常见问题

### 8.11 多语言补充

完善 `zh.json` 和 `en.json`，覆盖所有界面文案。

### 8.12 代码检查

```bash
# 后端
cd backend
ruff check .
ruff format .

# 前端
cd frontend
npm run lint
npm run format
```

---

## 关键设计点

- 设置页使用 Tabs 分组，清晰划分 LLM/TTS/Dify/通用四大块。
- API Key 输入框使用 `type="password"`，本地明文存储但界面隐藏。
- 测试连接按钮即时验证配置可用性，减少用户配置错误。
- 一键启动脚本自动检测 Dify 运行状态，未运行则尝试拉起。
- 项目收尾时确保前后端代码规范检查通过、测试通过。

---

## 验收标准

- [ ] 设置页可配置并保存 LLM、TTS、Dify、通用设置
- [ ] 测试连接按钮可验证 LLM 和 TTS 配置
- [ ] 中英文切换生效，所有界面文案有对应翻译
- [ ] 后端核心接口单元测试全部通过
- [ ] `scripts/start.sh` 和 `scripts/start.bat` 可一键启动 Dify、后端、Worker、前端
- [ ] README 包含完整安装、配置、启动说明
- [ ] Biome + Ruff 检查无错误
- [ ] 端到端验证：工作区 1 生成引导词 → 保存 → 工作区 2 生成音频 → 播放下载

---

## 关联文档

- `docs/tech/tech-spec.md` 第 11、12、13、14 章
- `docs/prd/meditation-guide-words-prd.md` 第 4.4、4.5 章

---

## 风险备注

- Windows bat 脚本的后台进程管理较粗糙，关闭启动窗口不会自动停止子进程，可考虑后续改为 PowerShell 脚本。
- Docker Desktop 在 Windows 下启动 Dify 可能占用较多内存（建议 8GB+）。
- 测试连接接口调用真实外部 API，可能因网络问题偶发失败，需给出清晰错误提示。
