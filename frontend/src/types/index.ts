export type PauseKind =
  | 'short' | 'paragraph' | 'breath' | 'observe' | 'practice'
  | 'transition' | 'ending' | 'none';

export interface SemanticPause {
  kind: PauseKind;
  count?: number;
  suggested_seconds?: number;
}

export interface ScriptBlock {
  id?: string | null;
  text: string;
  pause_after: SemanticPause;
}

export interface ScriptPlan {
  version: 1;
  target_duration_seconds: number;
  blocks: ScriptBlock[];
}

export interface GeneratedScript extends ScriptPlan {
  title: string;
}

export interface Script {
  id: number;
  title: string;
  content: string;
  script_plan?: ScriptPlan | null;
  pause_capable: boolean;
  target_duration_seconds?: number | null;
  session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AudioRenderPlan {
  version: 1;
  pause_profile_id: 'gentle_v1' | 'standard_v1' | 'deep_v1';
  voice: { voice_id: string; rate: number; volume: number; pitch: number; instruction: string };
  segments: Array<{
    id: string;
    text: string;
    pause_after_ms: number;
    pause_kind: PauseKind;
    pause_strategy: 'natural' | 'silence';
  }>;
}

export type PauseProfileId = AudioRenderPlan['pause_profile_id'];

export interface PauseProfile {
  id: PauseProfileId;
  version: 1;
  durations: Record<string, number>;
  suggested_seconds_factor: number;
}

export interface RenderPlanPreview {
  render_plan: AudioRenderPlan;
  render_plan_digest: string;
  preview_digest: string;
  estimate: {
    estimated_speech_seconds: number;
    estimated_natural_pause_seconds: number;
    deterministic_pause_seconds: number;
    estimated_total_seconds: number;
    target_duration_seconds: number;
    duration_delta_seconds: number;
    estimation_version: 'zh_v1';
  };
}

export interface ScriptListResponse {
  items: Script[];
  total: number;
}

export type AudioTaskStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface AudioTask {
  id: number;
  script_id: number;
  voice_prompt: string;
  tts_params?: Record<string, unknown> | null;
  status: AudioTaskStatus;
  retry_count: number;
  file_path?: string | null;
  error_msg?: string | null;
  created_at: string;
  completed_at?: string | null;
  render_plan_version?: number | null;
  render_plan_digest?: string | null;
  pause_profile_id?: string | null;
  stage?: 'plan_validated' | 'synthesizing' | 'assembling' | 'encoding' | 'verifying' | 'completed' | null;
  completed_segments: number;
  total_segments?: number | null;
  estimated_speech_seconds?: number | null;
  estimated_pause_seconds?: number | null;
  estimated_total_seconds?: number | null;
  actual_duration_seconds?: number | null;
  duration_deviation_percent?: number | null;
  provider?: string | null;
  model?: string | null;
  voice_id?: string | null;
}

export interface LLMConfig {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  temperature: number;
  max_tokens?: number | null;
}

export interface TTSConfig {
  provider: string;
  api_key: string;
  secret_key: string;
  appid: string;
  cluster: string;
  voice_id: string;
  speed: number;
  volume: number;
  output_format: string;
  model: string;
  base_url: string;
}

export interface DifyConfig {
  base_url: string;
  script_app_key: string;
  audio_app_key: string;
}

export interface AliyunMusicConfig {
  api_key: string;
  workspace_id: string;
  base_url: string;
  model: 'fun-music-v1';
  source_format: 'wav';
}

export interface MiniMaxMusicConfig {
  api_key: string;
  base_url: string;
  model: 'music-3.0';
  source_format: 'mp3' | 'wav';
}

export interface MusicConfig {
  provider: 'minimax' | 'aliyun';
  output_format: 'mp3';
  enable_aigc_watermark: false;
  worker_concurrency: number;
  aliyun: AliyunMusicConfig;
  minimax: MiniMaxMusicConfig;
}

export type MusicTaskStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type MusicTaskStage = 'generating' | 'downloading' | 'source_ready' | 'processing';

export interface MusicTask {
  id: number;
  prompt: string;
  effective_prompt: string;
  preset_params: Record<string, unknown>;
  provider: 'minimax' | 'aliyun';
  model: string;
  source_format: 'wav' | 'mp3';
  status: MusicTaskStatus;
  stage: MusicTaskStage;
  retry_count: number;
  download_retry_count: number;
  source_duration_seconds?: number | null;
  target_duration_seconds: number;
  final_duration_seconds?: number | null;
  sample_rate?: number | null;
  channels?: number | null;
  output_format: string;
  is_ai_generated: boolean;
  watermark_enabled: boolean;
  estimated_cost?: number | null;
  error_code?: string | null;
  error_msg?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface MusicCapabilities {
  ffmpeg_available: boolean;
  ffprobe_available: boolean;
  music_processing_available: boolean;
}

export interface AudioCapabilities {
  ffmpeg_available: boolean;
  ffprobe_available: boolean;
  audio_rendering_available: boolean;
}

export interface MusicDownloadItem {
  kind: 'source' | 'final';
  format: 'wav' | 'mp3';
  label: string;
  size: number;
  duration_seconds?: number | null;
  download_url: string;
}

export interface GeneralConfig {
  language: string;
  theme: string;
  audio_output_dir: string;
}

export interface Settings {
  llm_config: LLMConfig;
  tts_config: TTSConfig;
  dify_config: DifyConfig;
  general_config: GeneralConfig;
  music_config: MusicConfig;
}
