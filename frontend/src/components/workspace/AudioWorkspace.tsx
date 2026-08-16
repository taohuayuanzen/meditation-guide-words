import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { PauseProfileSelector } from './PauseProfileSelector';
import { RenderPlanPreview } from './RenderPlanPreview';
import { TaskItem } from './TaskItem';
import { useToast } from '@/hooks/useToast';
import { fetchPauseProfiles, previewAudioRenderPlan } from '@/services/audioRenderPlanService';
import { createAudioTask, fetchAudioCapabilities, fetchAudioTasks, retryAudioTask } from '@/services/audioTaskService';
import { fetchScripts } from '@/services/scriptService';
import { useSettingsStore } from '@/stores/settingsStore';
import type { AudioCapabilities, AudioTask, PauseProfile, PauseProfileId, RenderPlanPreview as Preview, Script } from '@/types';

interface Props { active: boolean }

export function AudioWorkspace({ active }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const settings = useSettingsStore((state) => state.settings);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [selectedScriptId, setSelectedScriptId] = useState('');
  const [voicePrompt, setVoicePrompt] = useState('');
  const [profileId, setProfileId] = useState<PauseProfileId>('standard_v1');
  const [profiles, setProfiles] = useState<PauseProfile[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [tasks, setTasks] = useState<AudioTask[]>([]);
  const [capabilities, setCapabilities] = useState<AudioCapabilities | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [expanded, setExpanded] = useState(false);
  const initialized = useRef(false);
  const previewInput = useRef('');

  const refreshTasks = useCallback(async () => {
    try {
      const result = await fetchAudioTasks(); setTasks(result); setLastUpdated(new Date());
      if (!initialized.current) { setExpanded(result.length > 0); initialized.current = true; }
    } catch (reason) { console.error('refresh audio tasks failed', reason); }
  }, []);
  const refreshScripts = useCallback(async () => {
    try {
      const result = await fetchScripts();
      setScripts(result);
      const selected = result.find((script) => String(script.id) === selectedScriptId);
      if (previewInput.current && selected && !previewInput.current.startsWith(`${selected.id}:${selected.updated_at}:`)) {
        setPreview(null); previewInput.current = '';
      }
    } catch (reason) { console.error('fetch scripts failed', reason); }
  }, [selectedScriptId]);

  useEffect(() => {
    if (!active) return;
    void Promise.all([refreshScripts(), refreshTasks(), fetchPauseProfiles().then(setProfiles), fetchAudioCapabilities().then(setCapabilities)])
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, [active, refreshScripts, refreshTasks]);
  useEffect(() => {
    if (!active || !tasks.some((task) => task.status === 'pending' || task.status === 'processing')) return;
    const id = window.setInterval(() => void refreshTasks(), 3000);
    return () => window.clearInterval(id);
  }, [active, tasks, refreshTasks]);
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => void refreshScripts(), 10_000);
    return () => window.clearInterval(id);
  }, [active, refreshScripts]);

  const selectedScript = scripts.find((script) => String(script.id) === selectedScriptId);
  const configKey = `${settings?.tts_config.provider ?? ''}:${settings?.tts_config.model ?? ''}:${settings?.tts_config.voice_id ?? ''}`;
  const inputKey = `${selectedScript?.id ?? ''}:${selectedScript?.updated_at ?? ''}:${profileId}:${voicePrompt}:${configKey}`;
  const invalidate = () => { setPreview(null); previewInput.current = ''; };

  const handlePreview = async () => {
    if (!selectedScript?.pause_capable || !voicePrompt.trim() || previewing) return;
    setPreviewing(true); setError(''); invalidate();
    try {
      const result = await previewAudioRenderPlan(selectedScript.id, profileId, voicePrompt.trim());
      previewInput.current = inputKey; setPreview(result); toast.success(t('audio.previewReady'));
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : String(reason);
      setError(`${t('audio.createError')}：${detail}`); toast.error(t('audio.createError'));
    } finally { setPreviewing(false); }
  };
  const handleConfirm = async () => {
    if (!preview || !selectedScript || previewInput.current !== inputKey || confirming) return;
    setConfirming(true); setError('');
    try {
      await createAudioTask(selectedScript.id, voicePrompt.trim(), undefined, preview.render_plan, preview.render_plan_digest, preview.preview_digest);
      invalidate(); toast.success(t('audio.taskCreated')); await refreshTasks(); setExpanded(true);
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : String(reason);
      setError(detail); toast.error(detail.includes('预览') || detail.toLowerCase().includes('preview') ? t('audio.previewExpired') : detail);
    } finally { setConfirming(false); }
  };
  const handleRetry = async (id: number) => {
    try { await retryAudioTask(id); await refreshTasks(); }
    catch (reason) { const detail = reason instanceof Error ? reason.message : String(reason); setError(detail); toast.error(detail); }
  };

  const legacyOnly = scripts.length > 0 && scripts.every((script) => !script.pause_capable);
  const stale = Boolean(preview && previewInput.current !== inputKey);
  const mediaUnavailable = capabilities !== null && !capabilities.audio_rendering_available;
  const scriptsById = new Map(scripts.map((script) => [script.id, script]));
  const age = lastUpdated ? Math.max(0, Math.floor((Date.now() - lastUpdated.getTime()) / 1000)) : null;

  return <div className="mx-auto flex h-full w-full max-w-7xl gap-6 overflow-hidden p-6">
    <div className="flex min-w-0 flex-1 flex-col gap-6 overflow-y-auto">
      <section><label htmlFor="script-select" className="mb-1 block text-sm font-medium">{t('audio.selectScript')}</label>
        <Select value={selectedScriptId} onValueChange={(value) => { setSelectedScriptId(value); invalidate(); }}><SelectTrigger id="script-select"><SelectValue placeholder={t('audio.selectPlaceholder')} /></SelectTrigger><SelectContent>{scripts.map((script) => <SelectItem key={script.id} value={String(script.id)}>{script.title} · {script.pause_capable ? `${t('audio.newScriptBadge')} · ${Math.round((script.target_duration_seconds ?? 0) / 60)} min` : t('audio.legacyBadge')}</SelectItem>)}</SelectContent></Select>
        {scripts.length === 0 && <p className="mt-2 text-sm text-muted-foreground">{t('audio.noScripts')}</p>}
        {legacyOnly && <p className="mt-2 text-sm text-amber-700 dark:text-amber-400">{t('audio.onlyLegacyScripts')}</p>}
        {selectedScript && !selectedScript.pause_capable && <p className="mt-2 text-sm font-medium text-destructive">{t('audio.legacyScriptHint')}</p>}
      </section>
      {selectedScript && <section className="space-y-2"><label htmlFor="script-preview" className="text-sm font-medium">{t('audio.scriptPreview')}</label><Textarea id="script-preview" value={selectedScript.content} readOnly rows={6} className="bg-muted" /></section>}
      <PauseProfileSelector profiles={profiles} value={profileId} onChange={(value) => { setProfileId(value); invalidate(); }} disabled={!selectedScript?.pause_capable} />
      <section className="space-y-2"><label htmlFor="voice-prompt" className="text-sm font-medium">{t('audio.voicePrompt')}</label><Textarea id="voice-prompt" value={voicePrompt} onChange={(event) => { setVoicePrompt(event.target.value); invalidate(); }} placeholder={t('audio.voicePromptPlaceholder')} rows={3} /><Button onClick={() => void handlePreview()} disabled={previewing || !selectedScript?.pause_capable || !voicePrompt.trim() || profiles.length === 0}>{previewing ? t('audio.previewing') : t('audio.previewPlan')}</Button></section>
      {stale && <p className="text-sm font-medium text-amber-700 dark:text-amber-400">{t('audio.previewExpired')}</p>}
      {mediaUnavailable && <p className="text-sm font-medium text-destructive">{t('audio.mediaUnavailable')}</p>}
      {error && <p className="text-sm font-medium text-destructive">{error}</p>}
      {preview && !stale && <RenderPlanPreview preview={preview} profileId={profileId} model={settings?.tts_config.model} voice={settings?.tts_config.voice_id} disabled={confirming || mediaUnavailable} onConfirm={() => void handleConfirm()} />}
    </div>
    <aside className={`flex shrink-0 flex-col transition-[width] ${expanded ? 'w-[30rem]' : 'w-9'}`}>
      {expanded ? <ScrollArea className="flex-1 rounded-2xl border bg-card p-4"><div className="mb-4 flex items-center justify-between"><h3 className="text-lg font-semibold">{t('audio.taskList')}</h3><div className="flex items-center gap-2">{age !== null && <span className="text-xs text-muted-foreground">{t('audio.lastUpdated', { seconds: age })}</span>}<Button variant="ghost" size="icon" onClick={() => void refreshTasks()} aria-label={t('audio.refresh')}><RefreshCw className="h-4 w-4" /></Button><Button variant="ghost" size="icon" onClick={() => setExpanded(false)} aria-label={t('audio.collapseTaskList')}><ChevronRight className="h-4 w-4" /></Button></div></div><div className="space-y-3">{tasks.length === 0 ? <p className="text-sm text-muted-foreground">{t('audio.emptyTasks')}</p> : tasks.map((task) => <TaskItem key={task.id} task={task} script={scriptsById.get(task.script_id)} onRetry={handleRetry} />)}</div></ScrollArea> : <Button variant="ghost" size="icon" onClick={() => setExpanded(true)} aria-label={t('audio.expandTaskList')}><ChevronLeft className="h-4 w-4" /></Button>}
    </aside>
  </div>;
}
