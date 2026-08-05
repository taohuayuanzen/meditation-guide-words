export interface Script {
  id: number;
  title: string;
  content: string;
  session_id?: string | null;
  created_at: string;
  updated_at: string;
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
}

export interface DifyConfig {
  base_url: string;
  script_app_key: string;
  audio_app_key: string;
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
}
