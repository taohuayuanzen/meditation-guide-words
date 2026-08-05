import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { RefreshCw } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { TaskItem } from '@/components/workspace/TaskItem';
import { useToast } from '@/hooks/useToast';
import { createAudioTask, fetchAudioTasks, retryAudioTask } from '@/services/audioTaskService';
import { parseVoicePrompt } from '@/services/difyService';
import { fetchScripts } from '@/services/scriptService';
import type { AudioTask, Script } from '@/types';

interface AudioWorkspaceProps {
  active: boolean;
}

export function AudioWorkspace({ active }: AudioWorkspaceProps) {
  const { t } = useTranslation();
  const { error: showError, success } = useToast();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScriptId, setSelectedScriptId] = useState('');
  const [voicePrompt, setVoicePrompt] = useState('');
  const [tasks, setTasks] = useState<AudioTask[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshTasks = useCallback(async () => {
    try {
      const updated = await fetchAudioTasks();
      setTasks(updated);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('refresh audio tasks failed', err);
    }
  }, []);

  const refreshScripts = useCallback(async () => {
    try {
      const items = await fetchScripts();
      setScripts(items);
    } catch (err) {
      console.error('fetch scripts failed', err);
    }
  }, []);

  useEffect(() => {
    if (!active) return;
    void refreshScripts();
    void refreshTasks();
  }, [active, refreshScripts, refreshTasks]);

  useEffect(() => {
    if (!active) return;
    const hasActiveTask = tasks.some(
      (task) => task.status === 'pending' || task.status === 'processing',
    );
    if (!hasActiveTask) return;
    const id = window.setInterval(() => {
      void refreshTasks();
    }, 3000);
    return () => window.clearInterval(id);
  }, [active, tasks, refreshTasks]);

  const selectedScript = scripts.find((s) => String(s.id) === selectedScriptId);
  const scriptsById = new Map(scripts.map((s) => [s.id, s]));

  const handleGenerate = async () => {
    if (!selectedScript || voicePrompt.trim() === '' || isGenerating) return;
    setIsGenerating(true);
    setError('');
    try {
      let ttsParams: Record<string, unknown> | undefined;
      try {
        ttsParams = await parseVoicePrompt(selectedScript, voicePrompt);
      } catch (err) {
        const detail = err instanceof Error ? err.message : '';
        setError(`${t('audio.parseError')}${detail ? `（${detail}）` : ''}`);
        return;
      }
      await createAudioTask(selectedScript.id, voicePrompt, ttsParams);
      await refreshTasks();
      success(t('audio.taskCreated'));
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setError(`${t('audio.createError')}：${detail}`);
      showError(`${t('audio.createError')}：${detail}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRetry = async (taskId: number) => {
    try {
      await retryAudioTask(taskId);
      await refreshTasks();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      showError(message);
    }
  };

  const secondsSinceUpdate = lastUpdated
    ? Math.max(0, Math.floor((Date.now() - lastUpdated.getTime()) / 1000))
    : null;

  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden p-4">
      <div>
        <label htmlFor="script-select" className="mb-1 block text-sm font-medium">
          {t('audio.selectScript')}
        </label>
        <Select value={selectedScriptId} onValueChange={setSelectedScriptId}>
          <SelectTrigger id="script-select" className="w-full">
            <SelectValue placeholder={t('audio.selectPlaceholder')} />
          </SelectTrigger>
          <SelectContent>
            {scripts.map((script) => (
              <SelectItem key={script.id} value={String(script.id)}>
                {script.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {scripts.length === 0 ? (
          <p className="mt-1 text-sm text-muted-foreground">{t('audio.noScripts')}</p>
        ) : null}
      </div>

      {selectedScript ? (
        <div className="shrink-0 space-y-2">
          <label htmlFor="script-preview" className="block text-sm font-medium">
            {t('audio.scriptPreview')}
          </label>
          <Textarea
            id="script-preview"
            value={selectedScript.content}
            readOnly
            rows={6}
            className="bg-muted"
          />
        </div>
      ) : null}

      <div className="flex shrink-0 gap-2">
        <Textarea
          value={voicePrompt}
          onChange={(e) => setVoicePrompt(e.target.value)}
          placeholder={t('audio.voicePromptPlaceholder')}
          className="flex-1"
          rows={2}
        />
        <Button
          onClick={() => void handleGenerate()}
          disabled={isGenerating || !selectedScript || voicePrompt.trim() === ''}
          className="self-stretch"
        >
          {isGenerating ? t('audio.parsing') : t('audio.generate')}
        </Button>
      </div>

      {error ? <p className="shrink-0 text-sm text-destructive">{error}</p> : null}

      <ScrollArea className="flex-1 rounded-lg border p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-medium">{t('audio.taskList')}</h3>
          <div className="flex items-center gap-2">
            {secondsSinceUpdate !== null ? (
              <span className="text-xs text-muted-foreground">
                {t('audio.lastUpdated', { seconds: secondsSinceUpdate })}
              </span>
            ) : null}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => void refreshTasks()}
              aria-label={t('audio.refresh')}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="space-y-2">
          {tasks.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('audio.emptyTasks')}</p>
          ) : (
            tasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                script={scriptsById.get(task.script_id)}
                onRetry={handleRetry}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
