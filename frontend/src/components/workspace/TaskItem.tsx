import { Download, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { getAudioDownloadUrl } from '@/services/audioTaskService';
import type { AudioTask, Script } from '@/types';

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
  const { t } = useTranslation();

  const scriptTitle = script?.title ?? t('audio.unknownScript');
  const voicePrompt = task.voice_prompt;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border bg-card p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="font-semibold">
            {t('audio.task')} #{task.id} · {scriptTitle}
          </div>
          <div className="text-sm text-muted-foreground">
            {t(`audio.${STATUS_KEYS[task.status]}`)}
            {task.created_at ? ` · ${t('audio.createdAt')} ${formatTime(task.created_at)}` : null}
            {task.status === 'completed' && task.completed_at
              ? ` · ${t('audio.completedAt')} ${formatTime(task.completed_at)}`
              : null}
          </div>
          {task.error_msg ? <div className="text-sm text-destructive">{task.error_msg}</div> : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {task.status === 'completed' ? (
            <>
              {/* biome-ignore lint/a11y/useMediaCaption: generated audio has no captions */}
              <audio
                controls
                preload="none"
                src={getAudioDownloadUrl(task.id)}
                className="h-8 w-44"
              />
              <Button asChild size="sm" variant="outline">
                <a href={getAudioDownloadUrl(task.id)} download>
                  <Download className="h-4 w-4" />
                  <span className="ml-1 hidden sm:inline">{t('audio.download')}</span>
                </a>
              </Button>
            </>
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
