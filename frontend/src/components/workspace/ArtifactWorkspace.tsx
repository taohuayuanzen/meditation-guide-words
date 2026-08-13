import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Headphones,
  Pencil,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/useToast';
import {
  deleteArtifact,
  fetchArtifacts,
  getArtifactDownloadUrl,
  renameArtifact,
  type Artifact,
  type ArtifactType,
} from '@/services/artifactService';

interface ArtifactWorkspaceProps {
  active: boolean;
}

const PAGE_SIZE = 20;

function formatTime(iso?: string | null) {
  if (!iso) return '';
  return new Date(iso).toLocaleString();
}

function baseNameWithoutExt(name: string) {
  const lastDot = name.lastIndexOf('.');
  return lastDot > 0 ? name.slice(0, lastDot) : name;
}

export function ArtifactWorkspace({ active }: ArtifactWorkspaceProps) {
  const { t } = useTranslation();
  const { success, error: showError } = useToast();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [activeTab, setActiveTab] = useState<ArtifactType>('all');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const [renameArtifactId, setRenameArtifactId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [renameBusy, setRenameBusy] = useState(false);

  const [deleteArtifactId, setDeleteArtifactId] = useState<string | null>(null);
  const [deleteArtifactName, setDeleteArtifactName] = useState('');
  const [deleteBusy, setDeleteBusy] = useState(false);

  const loadArtifacts = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchArtifacts(activeTab, page, PAGE_SIZE);
      setArtifacts(result.items);
      setTotal(result.total);
    } catch (err) {
      console.error('fetch artifacts failed', err);
      showError(err instanceof Error ? err.message : t('artifact.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [activeTab, page, showError, t]);

  useEffect(() => {
    if (!active) return;
    void loadArtifacts();
  }, [active, loadArtifacts]);

  const handleRefresh = () => {
    void loadArtifacts();
  };

  const handleTabChange = (value: string) => {
    setActiveTab(value as ArtifactType);
    setPage(1);
  };

  const openRename = (artifact: Artifact) => {
    setRenameArtifactId(artifact.id);
    setRenameValue(
      artifact.type === 'audio'
        ? baseNameWithoutExt(artifact.name)
        : artifact.title || baseNameWithoutExt(artifact.name),
    );
  };

  const closeRename = () => {
    setRenameArtifactId(null);
    setRenameValue('');
    setRenameBusy(false);
  };

  const handleRename = async () => {
    if (!renameArtifactId || !renameValue.trim()) return;
    setRenameBusy(true);
    try {
      await renameArtifact(renameArtifactId, renameValue.trim());
      success(t('artifact.renamed'));
      closeRename();
      await loadArtifacts();
    } catch (err) {
      const message = err instanceof Error ? err.message : t('artifact.renameFailed');
      showError(message);
    } finally {
      setRenameBusy(false);
    }
  };

  const openDelete = (artifact: Artifact) => {
    setDeleteArtifactId(artifact.id);
    setDeleteArtifactName(artifact.name);
  };

  const closeDelete = () => {
    setDeleteArtifactId(null);
    setDeleteArtifactName('');
    setDeleteBusy(false);
  };

  const handleDelete = async () => {
    if (!deleteArtifactId) return;
    setDeleteBusy(true);
    try {
      await deleteArtifact(deleteArtifactId);
      success(t('artifact.deleted'));
      closeDelete();
      if (artifacts.length === 1 && page > 1) {
        setPage((currentPage) => currentPage - 1);
      } else {
        await loadArtifacts();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('artifact.deleteFailed');
      showError(message);
    } finally {
      setDeleteBusy(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const firstItemIndex = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastItemIndex = Math.min(page * PAGE_SIZE, total);

  const renderList = (items: Artifact[]) => {
    if (items.length === 0) {
      return <p className="text-sm text-muted-foreground">{t('artifact.empty')}</p>;
    }
    return (
      <div className="space-y-3">
        {items.map((artifact) => (
          <div
            key={artifact.id}
            className="flex flex-col gap-3 rounded-2xl border bg-card p-4 sm:flex-row sm:items-start sm:justify-between"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 font-semibold">
                {artifact.type === 'audio' ? (
                  <Headphones className="h-4 w-4 shrink-0 text-muted-foreground" />
                ) : (
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
                <span className="truncate" title={artifact.name}>
                  {artifact.name}
                </span>
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {artifact.type === 'audio' && artifact.script_title
                  ? `${artifact.script_title} · `
                  : null}
                {artifact.created_at ? `${formatTime(artifact.created_at)}` : null}
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {artifact.type === 'audio' ? (
                <>
                  {/* biome-ignore lint/a11y/useMediaCaption: generated audio has no captions */}
                  <audio
                    controls
                    preload="none"
                    src={getArtifactDownloadUrl(artifact.id)}
                    className="h-8 w-44"
                  />
                  <Button asChild size="sm" variant="outline">
                    <a href={getArtifactDownloadUrl(artifact.id)} download>
                      <Download className="h-4 w-4" />
                      <span className="ml-1 hidden sm:inline">{t('artifact.download')}</span>
                    </a>
                  </Button>
                </>
              ) : (
                <Button asChild size="sm" variant="outline">
                  <a href={getArtifactDownloadUrl(artifact.id)} download>
                    <Download className="h-4 w-4" />
                    <span className="ml-1 hidden sm:inline">{t('artifact.download')}</span>
                  </a>
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => openRename(artifact)}>
                <Pencil className="h-4 w-4" />
                <span className="ml-1 hidden sm:inline">{t('artifact.rename')}</span>
              </Button>
              <Button size="sm" variant="destructive" onClick={() => openDelete(artifact)}>
                <Trash2 className="h-4 w-4" />
                <span className="ml-1 hidden sm:inline">{t('artifact.delete')}</span>
              </Button>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col gap-6 overflow-hidden p-6">
      <div className="flex shrink-0 items-center justify-between">
        <h2 className="text-xl font-semibold">{t('artifact.title')}</h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleRefresh}
          disabled={loading}
          aria-label={t('artifact.refresh')}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="flex flex-1 flex-col overflow-hidden"
      >
        <TabsList className="w-fit">
          <TabsTrigger value="all">{t('artifact.all')}</TabsTrigger>
          <TabsTrigger value="audio">{t('artifact.audio')}</TabsTrigger>
          <TabsTrigger value="script">{t('artifact.script')}</TabsTrigger>
        </TabsList>
        <div className="mt-4 flex-1 overflow-hidden">
          <ScrollArea className="h-full rounded-2xl border bg-card p-4">
            {renderList(artifacts)}
          </ScrollArea>
        </div>
        {total > 0 ? (
          <div className="mt-4 flex shrink-0 items-center justify-between gap-3 text-sm text-muted-foreground">
            <span>{t('artifact.paginationSummary', { from: firstItemIndex, to: lastItemIndex, total })}</span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((currentPage) => currentPage - 1)}
                disabled={loading || page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                {t('artifact.previousPage')}
              </Button>
              <span className="whitespace-nowrap">
                {t('artifact.pageIndicator', { page, totalPages })}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((currentPage) => currentPage + 1)}
                disabled={loading || page === totalPages}
              >
                {t('artifact.nextPage')}
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ) : null}
      </Tabs>

      <Dialog open={!!renameArtifactId} onOpenChange={(open) => !open && closeRename()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('artifact.renameTitle')}</DialogTitle>
            <DialogDescription>{t('artifact.renameHint')}</DialogDescription>
          </DialogHeader>
          <Input
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            placeholder={t('artifact.renamePlaceholder')}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void handleRename();
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={closeRename} disabled={renameBusy}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={() => void handleRename()}
              disabled={renameBusy || !renameValue.trim()}
            >
              {renameBusy ? t('common.saving') : t('common.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteArtifactId} onOpenChange={(open) => !open && closeDelete()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('artifact.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('artifact.confirmDelete', { name: deleteArtifactName })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={closeDelete} disabled={deleteBusy}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={() => void handleDelete()} disabled={deleteBusy}>
              {deleteBusy ? t('common.deleting') : t('common.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
