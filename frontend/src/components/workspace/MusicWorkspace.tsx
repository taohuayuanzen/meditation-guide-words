import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import {
  buildMusicPrompt,
  DEFAULT_MUSIC_PRESETS,
  MUSIC_PRESETS,
  type MusicPresetValues,
  type PresetOption,
} from '@/config/musicPresets';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { MusicTaskItem } from '@/components/workspace/MusicTaskItem';
import { useToast } from '@/hooks/useToast';
import {
  createMusicTask,
  deleteMusicTask,
  fetchMusicCapabilities,
  fetchMusicDownloads,
  fetchMusicTasks,
  retryMusicTask,
} from '@/services/musicTaskService';
import { useSettingsStore } from '@/stores/settingsStore';
import type { MusicCapabilities, MusicDownloadItem, MusicTask } from '@/types';

interface MusicWorkspaceProps {
  active: boolean;
}

const DURATIONS = [5, 10, 15, 20, 30];

export function MusicWorkspace({ active }: MusicWorkspaceProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { error: showError, success } = useToast();
  const settings = useSettingsStore((state) => state.settings);
  const loadSettings = useSettingsStore((state) => state.loadSettings);
  const [presets, setPresets] = useState<MusicPresetValues>(DEFAULT_MUSIC_PRESETS);
  const [freeDescription, setFreeDescription] = useState('');
  const generatedPrompt = useMemo(
    () => buildMusicPrompt(presets, freeDescription, i18n.language),
    [presets, freeDescription, i18n.language],
  );
  const [effectivePrompt, setEffectivePrompt] = useState(generatedPrompt);
  const [promptEdited, setPromptEdited] = useState(false);
  const [presetChanged, setPresetChanged] = useState(false);
  const [durationMode, setDurationMode] = useState('5');
  const [customMinutes, setCustomMinutes] = useState(5);
  const [tasks, setTasks] = useState<MusicTask[]>([]);
  const [capabilities, setCapabilities] = useState<MusicCapabilities | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const initialized = useRef(false);
  const [downloadTask, setDownloadTask] = useState<MusicTask | null>(null);
  const [downloads, setDownloads] = useState<MusicDownloadItem[]>([]);

  useEffect(() => {
    if (!promptEdited) setEffectivePrompt(generatedPrompt);
    else setPresetChanged(true);
  }, [generatedPrompt, promptEdited]);

  const refresh = useCallback(async () => {
    const [nextTasks, nextCapabilities] = await Promise.all([
      fetchMusicTasks(),
      fetchMusicCapabilities(),
    ]);
    setTasks(nextTasks);
    setCapabilities(nextCapabilities);
    if (!initialized.current) {
      setExpanded(nextTasks.length > 0);
      initialized.current = true;
    }
  }, []);

  useEffect(() => {
    if (!active) return;
    void loadSettings();
    void refresh().catch((error) => showError(error instanceof Error ? error.message : String(error)));
  }, [active, loadSettings, refresh, showError]);

  useEffect(() => {
    if (!active || !tasks.some((task) => ['pending', 'processing'].includes(task.status))) return;
    const timer = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(timer);
  }, [active, tasks, refresh]);

  const musicConfig = settings?.music_config;
  const activeProviderConfig = musicConfig?.[musicConfig.provider];
  const missing = [
    !activeProviderConfig?.api_key ? t('music.missingApiKey') : '',
    musicConfig?.provider === 'aliyun' && !musicConfig.aliyun?.workspace_id
      ? t('music.missingWorkspace')
      : '',
    capabilities && !capabilities.ffmpeg_available ? t('music.missingFfmpeg') : '',
    capabilities && !capabilities.ffprobe_available ? t('music.missingFfprobe') : '',
  ].filter(Boolean);
  const minutes = durationMode === 'custom' ? customMinutes : Number(durationMode);
  const presetsValid =
    presets.moods.length > 0 && presets.instruments.length > 0 && presets.environments.length > 0;
  const canSubmit =
    missing.length === 0 && presetsValid && minutes >= 1 && minutes <= 60 && effectivePrompt.trim();

  const toggleMulti = (
    key: 'moods' | 'instruments' | 'environments',
    value: string,
    exclusive?: string,
  ) => {
    setPresets((current) => {
      const selected = current[key];
      let next: string[];
      if (value === exclusive) next = [value];
      else if (selected.includes(value)) next = selected.filter((item) => item !== value);
      else next = [...selected.filter((item) => item !== exclusive), value];
      return { ...current, [key]: next };
    });
  };

  const applyGeneratedPrompt = () => {
    setEffectivePrompt(generatedPrompt);
    setPromptEdited(false);
    setPresetChanged(false);
  };

  const submit = async () => {
    if (!canSubmit || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await createMusicTask({
        prompt: freeDescription,
        effective_prompt: effectivePrompt,
        preset_params: { ...presets },
        target_duration_seconds: minutes * 60,
      });
      await refresh();
      setExpanded(true);
      success(t('music.taskCreated'));
    } catch (error) {
      showError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const openDownloads = async (task: MusicTask) => {
    try {
      setDownloads(await fetchMusicDownloads(task.id));
      setDownloadTask(task);
    } catch (error) {
      showError(error instanceof Error ? error.message : String(error));
    }
  };

  const handleDelete = async (task: MusicTask) => {
    if (task.status === 'processing') {
      showError(t('music.processingCannotDelete'));
      return;
    }
    if (!window.confirm(t('music.confirmDelete'))) return;
    try {
      await deleteMusicTask(task.id);
      await refresh();
      success(t('music.deleted'));
    } catch (error) {
      showError(error instanceof Error ? error.message : String(error));
    }
  };

  const handleRetry = async (task: MusicTask) => {
    const regenerates = task.provider === 'minimax' && task.stage === 'generating';
    if (regenerates && !window.confirm(t('music.confirmMinimaxRegenerate'))) return;
    try {
      await retryMusicTask(task.id, regenerates);
      await refresh();
    } catch (error) {
      showError(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <div className="mx-auto flex h-full w-full max-w-7xl gap-6 overflow-hidden p-6">
      <div className="min-w-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {missing.length > 0 ? (
          <Alert variant="destructive">
            <AlertTitle>{t('music.unavailable')}</AlertTitle>
            <AlertDescription>
              <p>{missing.join('、')}</p>
              <Button className="mt-3" size="sm" onClick={() => navigate('/settings/music')}>
                {t('music.goToSettings')}
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}

        <PresetGroup title={t('music.moods')} options={MUSIC_PRESETS.moods} selected={presets.moods} onToggle={(value) => toggleMulti('moods', value)} />
        <PresetGroup title={t('music.instruments')} options={MUSIC_PRESETS.instruments} selected={presets.instruments} onToggle={(value) => toggleMulti('instruments', value, 'no_distinct_instrument')} />
        <PresetGroup title={t('music.environments')} options={MUSIC_PRESETS.environments} selected={presets.environments} onToggle={(value) => toggleMulti('environments', value, 'no_nature')} />

        <div className="grid gap-4 sm:grid-cols-2">
          <SinglePreset label={t('music.rhythm')} value={presets.rhythm} options={MUSIC_PRESETS.rhythms} onChange={(rhythm) => setPresets((current) => ({ ...current, rhythm }))} />
          <SinglePreset label={t('music.dynamics')} value={presets.dynamics} options={MUSIC_PRESETS.dynamics} onChange={(dynamics) => setPresets((current) => ({ ...current, dynamics }))} />
        </div>

        <div className="space-y-2">
          <label htmlFor="music-free-description" className="font-medium">{t('music.freeDescription')}</label>
          <Textarea id="music-free-description" value={freeDescription} onChange={(event) => setFreeDescription(event.target.value)} rows={2} />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="music-prompt" className="font-medium">{t('music.promptPreview')}</label>
            {presetChanged ? <Button size="sm" variant="outline" onClick={applyGeneratedPrompt}>{t('music.applyNewPreset')}</Button> : null}
          </div>
          <Textarea id="music-prompt" value={effectivePrompt} onChange={(event) => { setEffectivePrompt(event.target.value); setPromptEdited(true); }} rows={8} />
          <p className="text-xs text-muted-foreground">{t('music.copyrightHint')}</p>
        </div>

        <div className="space-y-2">
          <p className="font-medium">{t('music.duration')}</p>
          <div className="flex flex-wrap gap-2">
            {DURATIONS.map((item) => <Button key={item} type="button" size="sm" variant={durationMode === String(item) ? 'default' : 'outline'} onClick={() => setDurationMode(String(item))}>{t('music.minutes', { count: item })}</Button>)}
            <Button type="button" size="sm" variant={durationMode === 'custom' ? 'default' : 'outline'} onClick={() => setDurationMode('custom')}>{t('music.custom')}</Button>
            {durationMode === 'custom' ? <Input type="number" min={1} max={60} step={1} value={customMinutes} onChange={(event) => setCustomMinutes(Number(event.target.value))} className="w-24" /> : null}
          </div>
        </div>
        <Alert>
          <AlertDescription>
            {musicConfig?.provider === 'aliyun'
              ? t('music.costHintAliyun')
              : t('music.costHintMinimax')}
          </AlertDescription>
        </Alert>
        <Button onClick={() => void submit()} disabled={!canSubmit || isSubmitting} className="w-full">
          {isSubmitting ? t('music.submitting') : t('music.generate')}
        </Button>
      </div>

      <aside className={`flex shrink-0 flex-col transition-[width] ${expanded ? 'w-[30rem]' : 'w-9'}`}>
        {expanded ? (
          <ScrollArea className="flex-1 rounded-2xl border bg-card p-4">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">{t('music.taskList')}</h3>
              <div><Button variant="ghost" size="icon" onClick={() => void refresh()}><RefreshCw className="h-4 w-4" /></Button><Button variant="ghost" size="icon" onClick={() => setExpanded(false)}><ChevronRight className="h-4 w-4" /></Button></div>
            </div>
            <div className="space-y-3">
              {tasks.length === 0 ? <p className="text-sm text-muted-foreground">{t('music.emptyTasks')}</p> : tasks.map((task) => <MusicTaskItem key={task.id} task={task} onRetry={(item) => void handleRetry(item)} onDownload={(item) => void openDownloads(item)} onDelete={(item) => void handleDelete(item)} />)}
            </div>
          </ScrollArea>
        ) : <Button variant="ghost" size="icon" onClick={() => setExpanded(true)}><ChevronLeft className="h-4 w-4" /></Button>}
      </aside>

      <Dialog open={Boolean(downloadTask)} onOpenChange={(open) => !open && setDownloadTask(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('music.downloadTitle')}</DialogTitle><DialogDescription>{t('music.downloadHint')}</DialogDescription></DialogHeader>
          <div className="space-y-3">
            {downloads.length === 0 ? <p>{t('music.noDownloads')}</p> : downloads.map((item) => <div key={item.kind} className="flex items-center justify-between rounded-xl border p-3"><div><p className="font-medium">{item.label}</p><p className="text-xs text-muted-foreground">{item.format.toUpperCase()} · {item.duration_seconds ? `${Math.round(item.duration_seconds)}s · ` : ''}{formatBytes(item.size)}</p></div><Button asChild size="sm"><a href={item.download_url} download>{t('music.download')}</a></Button></div>)}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function PresetGroup({ title, options, selected, onToggle }: { title: string; options: PresetOption[]; selected: string[]; onToggle: (value: string) => void }) {
  const { i18n } = useTranslation();
  return <fieldset className="space-y-2"><legend className="font-medium">{title}</legend><div className="flex flex-wrap gap-2">{options.map((option) => <Button key={option.value} type="button" size="sm" variant={selected.includes(option.value) ? 'default' : 'outline'} onClick={() => onToggle(option.value)}>{i18n.language.startsWith('zh') ? option.zh : option.en}</Button>)}</div></fieldset>;
}

function SinglePreset({ label, value, options, onChange }: { label: string; value: string; options: PresetOption[]; onChange: (value: string) => void }) {
  const { i18n } = useTranslation();
  return <div className="space-y-2"><p className="font-medium">{label}</p><Select value={value} onValueChange={onChange}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{options.map((option) => <SelectItem key={option.value} value={option.value}>{i18n.language.startsWith('zh') ? option.zh : option.en}</SelectItem>)}</SelectContent></Select></div>;
}

function formatBytes(size: number): string {
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}
