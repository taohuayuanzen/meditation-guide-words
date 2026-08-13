import { Archive, FileText, Headphones, Menu, Music2, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { WorkspaceNav } from '@/components/layout/WorkspaceNav';
import { useAppStore } from '@/stores/appStore';

const ICONS = {
  script: FileText,
  audio: Headphones,
  music: Music2,
  artifact: Archive,
};

const WORKSPACE_TITLE_KEY: Record<keyof typeof ICONS, string> = {
  script: 'workspace.script',
  audio: 'workspace.audio',
  music: 'workspace.music',
  artifact: 'workspace.artifact',
};

export function Header() {
  const navigate = useNavigate();
  const { currentWorkspace, mobileMenuOpen, setMobileMenuOpen } = useAppStore();
  const { t } = useTranslation();
  const title = t(WORKSPACE_TITLE_KEY[currentWorkspace]);
  const Icon = ICONS[currentWorkspace];

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
      <div className="flex items-center gap-2">
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label={t('sidebar.menu')}
            >
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64">
            <SheetHeader>
              <SheetTitle>{t('app.name')}</SheetTitle>
            </SheetHeader>
            <div className="mt-6">
              <WorkspaceNav onNavigate={() => setMobileMenuOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>
        <Icon className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label={t('settings.title')}
        onClick={() => navigate('/settings')}
      >
        <Settings className="h-5 w-5" />
      </Button>
    </header>
  );
}
