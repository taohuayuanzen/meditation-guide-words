import { ChevronLeft, ChevronRight, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { WorkspaceNav } from '@/components/layout/WorkspaceNav';
import { useAppStore } from '@/stores/appStore';

export function Sidebar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  const settingsButton = (
    <Button
      variant="ghost"
      className={`w-full justify-start gap-2 ${sidebarCollapsed ? 'px-2' : ''}`}
      onClick={() => navigate('/settings')}
      aria-label={t('settings.title')}
    >
      <Settings className="h-5 w-5 shrink-0" />
      {!sidebarCollapsed && <span className="truncate">{t('settings.title')}</span>}
    </Button>
  );

  return (
    <aside
      className={`hidden h-screen shrink-0 flex-col border-r p-4 transition-all duration-200 md:flex ${
        sidebarCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      <h1
        className={`mb-8 text-xl font-bold transition-opacity ${
          sidebarCollapsed ? 'truncate text-center opacity-80' : ''
        }`}
        title={t('app.name')}
      >
        {sidebarCollapsed ? (t('app.shortName') ?? t('app.name')[0]) : t('app.name')}
      </h1>
      <WorkspaceNav collapsed={sidebarCollapsed} />
      <div className="mt-auto space-y-2">
        {sidebarCollapsed ? (
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>{settingsButton}</TooltipTrigger>
              <TooltipContent side="right">{t('settings.title')}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : (
          settingsButton
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="w-full"
          aria-label={sidebarCollapsed ? t('sidebar.expand') : t('sidebar.collapse')}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <ChevronLeft className="h-5 w-5" />
          )}
        </Button>
      </div>
    </aside>
  );
}
