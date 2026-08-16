import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import type { PauseProfileId, RenderPlanPreview as Preview } from '@/types';

interface Props {
  preview: Preview;
  profileId: PauseProfileId;
  model?: string;
  voice?: string;
  disabled: boolean;
  onConfirm: () => void;
}

export function formatDuration(seconds: number, language: string): string {
  const rounded = Math.max(0, Math.round(seconds));
  if (rounded < 60) return language.startsWith('zh') ? `${rounded}秒` : `${rounded}s`;
  const minutes = Math.floor(rounded / 60);
  const rest = rounded % 60;
  return language.startsWith('zh') ? `${minutes}分${rest}秒` : `${minutes}m ${rest}s`;
}

export function RenderPlanPreview({ preview, profileId, model, voice, disabled, onConfirm }: Props) {
  const { t, i18n } = useTranslation();
  const { estimate, render_plan: plan } = preview;
  const target = Math.max(1, estimate.target_duration_seconds);
  const deltaPercent = (estimate.duration_delta_seconds / target) * 100;
  const outsideTarget = Math.abs(deltaPercent) > 10;
  const deterministicCount = plan.segments.filter((segment) => segment.pause_strategy === 'silence' && segment.pause_after_ms > 0).length;
  const longestPause = Math.max(0, ...plan.segments.map((segment) => segment.pause_after_ms / 1000));
  const duration = (value: number) => formatDuration(value, i18n.language);

  return (
    <section className="space-y-4 rounded-xl border bg-card p-4" aria-live="polite">
      <div>
        <p className="text-sm font-medium">{t('audio.estimatedDuration')}</p>
        <p className="mt-1 text-3xl font-semibold">{duration(estimate.estimated_total_seconds)}</p>
        <p className="mt-1 text-xs text-muted-foreground">{t('audio.estimatedDurationHint')}</p>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
        <div><dt className="text-muted-foreground">{t('audio.targetDuration')}</dt><dd>{duration(estimate.target_duration_seconds)}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.estimatedSpeech')}</dt><dd>{duration(estimate.estimated_speech_seconds)}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.naturalPauses')}</dt><dd>{duration(estimate.estimated_natural_pause_seconds)}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.meditationSilence')}</dt><dd>{duration(estimate.deterministic_pause_seconds)}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.deterministicPauseCount')}</dt><dd>{t('audio.pauseCountValue', { count: deterministicCount })}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.longestPause')}</dt><dd>{duration(longestPause)}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.model')}</dt><dd className="break-all">{model ?? '—'}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.voice')}</dt><dd>{voice ?? plan.voice.voice_id}</dd></div>
        <div><dt className="text-muted-foreground">{t('audio.pauseProfile')}</dt><dd>{t(`audio.pauseProfiles.${profileId}.name`)}</dd></div>
      </dl>
      <p className={outsideTarget ? 'text-sm font-medium text-amber-700 dark:text-amber-400' : 'text-sm text-muted-foreground'}>
        {t(outsideTarget ? 'audio.durationWarning' : 'audio.durationWithinTarget', { percent: Math.abs(deltaPercent).toFixed(1) })}
      </p>
      <Button disabled={disabled} onClick={onConfirm}>{t('audio.confirmGenerate')}</Button>
    </section>
  );
}
