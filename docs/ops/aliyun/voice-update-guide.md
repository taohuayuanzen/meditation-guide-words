# 阿里云 TTS 音色更新说明

本文档说明如何在 `frontend/src/components/settings/TTSSettings.tsx` 中维护阿里云 TTS 音色列表。

## 背景

阿里云百炼非实时语音合成包含多个模型系列，每个模型支持的系统音色不同：

- **Qwen-Audio-TTS**：`qwen-audio-3.0-tts-plus`、`qwen-audio-3.0-tts-flash`
- **CosyVoice**：`cosyvoice-v3-flash`（以及 `cosyvoice-v3-plus`、`cosyvoice-v3.5-*` 等）

当前项目只预设了常用系统音色。当阿里云新增/调整音色时，需要同步更新前端下拉列表。

## 音色配置位置

前端音色数据定义在：

```
frontend/src/components/settings/TTSSettings.tsx
```

常量 `ALIYUN_VOICES` 按 model 维护可选音色：

```typescript
const ALIYUN_VOICES: Record<string, { value: string; labelKey: string }[]> = {
  'qwen-audio-3.0-tts-plus': [
    { value: 'longanlingxin', labelKey: 'settings.voiceLonganlingxin' },
    { value: 'longanlufeng', labelKey: 'settings.voiceLonganlufeng' },
  ],
  // ...
};
```

## 如何新增或修改音色

### 1. 查找官方音色列表

参考阿里云官方文档：

- [Qwen-Audio-TTS 音色列表](https://help.aliyun.com/zh/model-studio/qwen-audio-tts-voice-list)
- [CosyVoice 音色列表](https://help.aliyun.com/zh/model-studio/cosyvoice-tts-voice-list)

确认目标音色的 `voice` 参数值（即请求体中 `input.voice` 的值）。

### 2. 在 `ALIYUN_VOICES` 中增加/修改条目

例如为 `qwen-audio-3.0-tts-flash` 新增系统音色 `longxiaoming`：

```typescript
'qwen-audio-3.0-tts-flash': [
  // ... 现有音色
  { value: 'longxiaoming', labelKey: 'settings.voiceLongxiaoming' },
],
```

### 3. 添加 i18n 文案

在以下两个文件中添加对应文案：

- `frontend/src/i18n/locales/zh.json`
- `frontend/src/i18n/locales/en.json`

示例：

```json
{
  "settings": {
    "voiceLongxiaoming": "龙小明（示例音色）"
  }
}
```

### 4. 验证

```bash
cd frontend
npm run lint
npm run build
```

确保没有 TypeScript 或 i18n 键缺失报错。

## 注意事项

1. **音色与模型不能混用**：每个 model 只支持自己的音色列表。若用户在下拉中选择了 A 模型的音色，又切换到了 B 模型，前端会自动重置为 B 模型的第一个音色。
2. **自定义音色**：下拉最后一项为"自定义音色"，用户可输入任意阿里云支持的音色 ID（包括基础音色、声音复刻音色等）。开发者不需要为所有音色都维护下拉选项。
3. **CosyVoice 系统音色不支持自由 instruction**：当前实现已约定对 `cosyvoice-*` 模型不传 `instruction`，避免自由文本指令与系统音色固定格式冲突。
4. **地域限制**：Qwen-Audio-TTS 与 CosyVoice 仅在北京地域可用，请确保使用华北 2（北京）的 API Key。

## 相关代码

- 适配器实现：`backend/app/services/tts_aliyun.py`
- 设置页组件：`frontend/src/components/settings/TTSSettings.tsx`
- 官方接口文档：[非实时语音合成用户指南](https://help.aliyun.com/zh/model-studio/non-realtime-tts-user-guide)
