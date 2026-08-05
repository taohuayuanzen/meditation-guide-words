import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { WorkspaceNav } from '@/components/layout/WorkspaceNav';
import { useAppStore } from '@/stores/appStore';

export function Sidebar() {
  const { t } = useTranslation();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

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
      <div className="mt-auto">
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
