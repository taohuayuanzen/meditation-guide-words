export interface PresetOption {
  value: string;
  zh: string;
  en: string;
}

export const MUSIC_PRESETS = {
  moods: [
    { value: 'calm', zh: '平静', en: 'calm' },
    { value: 'warm', zh: '温暖', en: 'warm' },
    { value: 'ethereal', zh: '空灵', en: 'ethereal' },
    { value: 'deep', zh: '沉静', en: 'deep and quiet' },
    { value: 'safe', zh: '安全', en: 'safe' },
    { value: 'clear', zh: '清澈', en: 'clear' },
  ],
  instruments: [
    { value: 'piano', zh: '钢琴', en: 'piano' },
    { value: 'singing_bowl', zh: '颂钵', en: 'singing bowls' },
    { value: 'soft_strings', zh: '柔和弦乐', en: 'soft strings' },
    { value: 'flute', zh: '长笛', en: 'flute' },
    { value: 'drone', zh: 'Drone持续音', en: 'a sustained drone' },
    { value: 'wood_percussion', zh: '木质打击乐', en: 'wooden percussion' },
    { value: 'no_distinct_instrument', zh: '无明显乐器', en: 'no distinct instrument' },
  ],
  environments: [
    { value: 'rain', zh: '雨声', en: 'rain' },
    { value: 'waves', zh: '海浪', en: 'ocean waves' },
    { value: 'stream', zh: '溪流', en: 'a stream' },
    { value: 'forest', zh: '森林', en: 'a forest' },
    { value: 'night', zh: '夜晚', en: 'night ambience' },
    { value: 'campfire', zh: '篝火', en: 'a campfire' },
    { value: 'wind', zh: '风声', en: 'wind' },
    { value: 'no_nature', zh: '无自然声', en: 'no nature sounds' },
  ],
  rhythms: [
    { value: 'no_beat', zh: '无节拍', en: 'without a beat' },
    { value: 'free_flow', zh: '自由流动', en: 'free-flowing' },
    { value: 'very_slow', zh: '极慢', en: 'very slow' },
    { value: 'slow_steady', zh: '缓慢稳定', en: 'slow and steady' },
  ],
  dynamics: [
    { value: 'very_low', zh: '极低动态', en: 'very low dynamics' },
    { value: 'steady', zh: '平稳', en: 'steady' },
    { value: 'gentle_variation', zh: '轻微起伏', en: 'gently varied' },
  ],
} satisfies Record<string, PresetOption[]>;

export interface MusicPresetValues {
  moods: string[];
  instruments: string[];
  environments: string[];
  rhythm: string;
  dynamics: string;
}

export const DEFAULT_MUSIC_PRESETS: MusicPresetValues = {
  moods: ['calm'],
  instruments: ['soft_strings'],
  environments: ['no_nature'],
  rhythm: 'no_beat',
  dynamics: 'steady',
};

function labels(group: PresetOption[], values: string[], language: string): string {
  return values
    .map((value) => group.find((item) => item.value === value))
    .filter((item): item is PresetOption => Boolean(item))
    .map((item) => (language.startsWith('zh') ? item.zh : item.en))
    .join(language.startsWith('zh') ? '、' : ', ');
}

export function buildMusicPrompt(
  values: MusicPresetValues,
  freeDescription: string,
  language: string,
): string {
  const isZh = language.startsWith('zh');
  const moods = labels(MUSIC_PRESETS.moods, values.moods, language);
  const instruments = labels(MUSIC_PRESETS.instruments, values.instruments, language);
  const environments = labels(MUSIC_PRESETS.environments, values.environments, language);
  const rhythm = labels(MUSIC_PRESETS.rhythms, [values.rhythm], language);
  const dynamics = labels(MUSIC_PRESETS.dynamics, [values.dynamics], language);
  if (isZh) {
    return [
      '创作一首纯音乐。',
      `整体情绪${moods}。`,
      `使用${instruments}，并加入${environments}。`,
      `节奏${rhythm}，动态${dynamics}，无突然变化，无强烈高潮。`,
      '旋律克制、重复性自然，适合长时间循环播放。',
      '不要人声、吟唱、念白、歌词或任何语言片段。',
      freeDescription.trim(),
    ]
      .filter(Boolean)
      .join('\n');
  }
  return [
    'Create suitable instrumental music.',
    `The overall mood is ${moods}.`,
    `Use ${instruments}, with ${environments}.`,
    `The rhythm is ${rhythm}, with ${dynamics} dynamics, no sudden changes or strong climax.`,
    'Keep the melody restrained and naturally repetitive for long listening and looping.',
    'Do not include vocals, chanting, speech, lyrics, or language fragments.',
    freeDescription.trim(),
  ]
    .filter(Boolean)
    .join('\n');
}
