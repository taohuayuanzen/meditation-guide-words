import { ArrowLeft } from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useBlocker, useNavigate } from 'react-router-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { SettingsNav } from '@/pages/settings/SettingsNav';
import { SettingsPageProvider, useSettingsPage } from '@/pages/settings/SettingsPageContext';

function SettingsLayoutInner() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { loading, loadError, isDirty } = useSettingsPage();

  const blocker = useBlocker(({ currentLocation: _currentLocation, nextLocation }) => {
    return isDirty && !nextLocation.pathname.startsWith('/settings');
  });

  useEffect(() => {
    if (blocker.state === 'blocked') {
      const confirmed = window.confirm(t('settings.unsavedLeave'));
      if (confirmed) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker, t]);

  const handleBack = () => {
    if (isDirty) {
      const confirmed = window.confirm(t('settings.unsavedLeave'));
      if (!confirmed) return;
    }
    navigate('/');
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      <header className="flex h-14 shrink-0 items-center gap-4 border-b px-4">
        <Button variant="ghost" size="icon" onClick={handleBack} aria-label={t('settings.back')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold">{t('settings.title')}</h1>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <SettingsNav />
        <ScrollArea className="flex-1">
          <main className="min-h-full p-6">
            {loading ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-1/3" />
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : loadError ? (
              <Alert variant="destructive">
                <AlertTitle>{t('settings.loadFailed')}</AlertTitle>
                <AlertDescription>{loadError}</AlertDescription>
              </Alert>
            ) : (
              <Outlet />
            )}
          </main>
        </ScrollArea>
      </div>
    </div>
  );
}

export function SettingsLayout() {
  return (
    <SettingsPageProvider>
      <SettingsLayoutInner />
    </SettingsPageProvider>
  );
}
