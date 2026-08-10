import { Archive, FileText, Headphones } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { useAppStore, type Workspace } from '@/stores/appStore';

interface WorkspaceNavProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

const ITEMS: { value: Workspace; icon: typeof FileText; labelKey: string }[] = [
  { value: 'script', icon: FileText, labelKey: 'workspace.script' },
  { value: 'audio', icon: Headphones, labelKey: 'workspace.audio' },
  { value: 'artifact', icon: Archive, labelKey: 'workspace.artifact' },
];

export function WorkspaceNav({ collapsed, onNavigate }: WorkspaceNavProps) {
  const { currentWorkspace, setWorkspace } = useAppStore();
  const { t } = useTranslation();

  const handleClick = (value: Workspace) => {
    setWorkspace(value);
    onNavigate?.();
  };

  return (
    <nav className="flex flex-col gap-2">
      {ITEMS.map(({ value, icon: Icon, labelKey }) => {
        const active = currentWorkspace === value;
        return (
          <Button
            key={value}
            variant={active ? 'default' : 'ghost'}
            className={`w-full justify-start gap-3 ${active ? 'font-semibold' : ''} ${
              collapsed ? 'px-2' : ''
            }`}
            onClick={() => handleClick(value)}
            aria-label={t(labelKey)}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!collapsed ? <span className="ml-2">{t(labelKey)}</span> : null}
          </Button>
        );
      })}
    </nav>
  );
}
