import { RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { getAudioDownloadUrl } from '@/services/audioTaskService';
import type { AudioTask, Script } from '@/types';
import { formatDuration } from './RenderPlanPreview';

interface TaskItemProps {
  task: AudioTask;
  script?: Script;
  onRetry: (id: number) => void;
}

const STATUS_KEYS = {
  pending: 'statusPending',
  processing: 'statusProcessing',
  completed: 'statusCompleted',
  failed: 'statusFailed',
} as const;

function formatTime(iso?: string | null) {
  if (!iso) return '';
  const date = new Date(iso);
  return date.toLocaleString();
}

export function TaskItem({ task, script, onRetry }: TaskItemProps) {
  const { t, i18n } = useTranslation();

  const scriptTitle = script?.title ?? t('audio.unknownScript');
  const voicePrompt = task.voice_prompt;
  const stage = task.stage ? t(`audio.stages.${task.stage}`) : t(`audio.${STATUS_KEYS[task.status]}`);
  const progress = task.stage === 'synthesizing' && task.total_segments
    ? t('audio.segmentProgress', { completed: task.completed_segments, total: task.total_segments })
    : null;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border bg-card p-4">
      <div className="flex flex-col gap-3">
        <div className="min-w-0">
          <div className="font-semibold">
            {t('audio.task')} #{task.id} · {scriptTitle}
          </div>
          <div className="text-sm text-muted-foreground">
            {stage}{progress ? ` · ${progress}` : ''}
            {task.created_at ? ` · ${t('audio.createdAt')} ${formatTime(task.created_at)}` : null}
            {task.status === 'completed' && task.completed_at
              ? ` · ${t('audio.completedAt')} ${formatTime(task.completed_at)}`
              : null}
          </div>
          {task.error_msg ? <div className="text-sm text-destructive">{task.error_msg}</div> : null}
          {(task.provider || task.model || task.voice_id || task.pause_profile_id) && (
            <div className="mt-2 text-xs text-muted-foreground">
              {[task.provider, task.model, task.voice_id, task.pause_profile_id ? t(`audio.pauseProfiles.${task.pause_profile_id}.name`, { defaultValue: task.pause_profile_id }) : null].filter(Boolean).join(' · ')}
            </div>
          )}
          {task.estimated_total_seconds != null && <div className="mt-1 text-xs text-muted-foreground">{t('audio.taskEstimated', { duration: formatDuration(task.estimated_total_seconds, i18n.language) })}</div>}
          {task.status === 'completed' && task.actual_duration_seconds != null && <div className="text-xs text-muted-foreground">{t('audio.taskActual', { duration: formatDuration(task.actual_duration_seconds, i18n.language), percent: Math.abs(task.duration_deviation_percent ?? 0).toFixed(1) })}</div>}
          {task.status === 'failed' && task.render_plan_version && <div className="mt-2 text-xs text-muted-foreground">{t(task.stage === 'assembling' || task.stage === 'encoding' || task.stage === 'verifying' ? 'audio.retryLocalHint' : 'audio.retryPlanHint')}</div>}
        </div>
        <div className="flex min-w-0 w-full items-center justify-end gap-2">
          {task.status === 'completed' ? (
            /* biome-ignore lint/a11y/useMediaCaption: generated audio has no captions */
            <audio
              controls
              preload="none"
              src={getAudioDownloadUrl(task.id)}
              className="h-8 w-full"
            />
          ) : null}
          {task.status === 'failed' ? (
            <Button size="sm" variant="outline" onClick={() => onRetry(task.id)}>
              <RotateCcw className="h-4 w-4" />
              <span className="ml-1">{t('audio.retry')}</span>
            </Button>
          ) : null}
        </div>
      </div>

      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <p className="truncate text-xs text-muted-foreground">
              {t('audio.voicePrompt')}：{voicePrompt}
            </p>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-sm">
            <p>{voicePrompt}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
