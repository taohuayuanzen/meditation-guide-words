import { Download, RotateCcw, Sparkles, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { getMusicDownloadUrl } from '@/services/musicTaskService';
import type { MusicTask } from '@/types';

interface MusicTaskItemProps {
  task: MusicTask;
  onRetry: (task: MusicTask) => void;
  onDownload: (task: MusicTask) => void;
  onDelete: (task: MusicTask) => void;
}

const STATUS_KEYS = {
  pending: 'statusPending',
  processing: 'statusProcessing',
  completed: 'statusCompleted',
  failed: 'statusFailed',
} as const;

const STAGE_KEYS = {
  generating: 'stageGenerating',
  downloading: 'stageDownloading',
  source_ready: 'stageSourceReady',
  processing: 'stageProcessing',
} as const;

export function MusicTaskItem({ task, onRetry, onDownload, onDelete }: MusicTaskItemProps) {
  const { t } = useTranslation();
  const tags = Object.entries(task.preset_params)
    .filter(([key]) => key !== 'scene')
    .flatMap(([, value]) => (Array.isArray(value) ? value : [value]))
    .filter((value): value is string => typeof value === 'string');

  return (
    <article className="space-y-3 rounded-2xl border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 font-semibold">
            <span>{t('music.taskNumber', { id: task.id })}</span>
            {task.is_ai_generated ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                <Sparkles className="h-3 w-3" /> {t('music.aiGenerated')}
              </span>
            ) : null}
          </div>
          <p className="text-sm text-muted-foreground">
            {task.provider === 'minimax' ? 'MiniMax' : t('settings.aliyunBailian')} · {task.model} ·{' '}
            {t(`music.${STATUS_KEYS[task.status]}`)} · {t(`music.${STAGE_KEYS[task.stage]}`)} ·{' '}
            {t('music.targetMinutes', { minutes: task.target_duration_seconds / 60 })}
          </p>
        </div>
        <time className="text-xs text-muted-foreground">
          {new Date(task.created_at).toLocaleString()}
        </time>
      </div>

      {tags.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => (
            <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-xs">
              {t(`music.option.${tag}`, { defaultValue: tag })}
            </span>
          ))}
        </div>
      ) : null}

      {task.source_duration_seconds && task.provider === 'aliyun' ? (
        <p className="text-sm text-muted-foreground">
          {t('music.costSummary', {
            seconds: task.source_duration_seconds,
            cost: task.estimated_cost?.toFixed(2) ?? '--',
          })}
        </p>
      ) : null}
      {task.source_duration_seconds && task.provider === 'minimax' ? (
        <p className="text-sm text-muted-foreground">
          {t('music.minimaxCostSummary', { seconds: task.source_duration_seconds })}
        </p>
      ) : null}
      {task.error_msg ? <p className="text-sm text-destructive">{task.error_msg}</p> : null}

      {task.status === 'completed' ? (
        /* biome-ignore lint/a11y/useMediaCaption: generated music has no captions */
        <audio
          controls
          preload="none"
          src={getMusicDownloadUrl(task.id, 'final')}
          className="h-9 w-full"
        />
      ) : null}

      <div className="flex flex-wrap justify-end gap-2">
        {task.status === 'failed' ? (
          <Button size="sm" variant="outline" onClick={() => onRetry(task)}>
            <RotateCcw className="mr-1 h-4 w-4" /> {t('music.retry')}
          </Button>
        ) : null}
        <Button size="sm" variant="outline" onClick={() => onDownload(task)}>
          <Download className="mr-1 h-4 w-4" /> {t('music.download')}
        </Button>
        <Button size="sm" variant="destructive" onClick={() => onDelete(task)}>
          <Trash2 className="mr-1 h-4 w-4" /> {t('music.delete')}
        </Button>
      </div>
    </article>
  );
}
