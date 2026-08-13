import { Bot, Brain, Music2, SlidersHorizontal, Volume2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';

import { useSettingsPage, type SettingsSection } from '@/pages/settings/SettingsPageContext';
import { cn } from '@/lib/utils';

const NAV_ITEMS: { key: SettingsSection; to: string; labelKey: string; icon: React.ElementType }[] =
  [
    { key: 'llm_config', to: '/settings/llm', labelKey: 'settings.llm', icon: Brain },
    { key: 'tts_config', to: '/settings/tts', labelKey: 'settings.tts', icon: Volume2 },
    { key: 'music_config', to: '/settings/music', labelKey: 'settings.music', icon: Music2 },
    { key: 'dify_config', to: '/settings/dify', labelKey: 'settings.dify', icon: Bot },
    {
      key: 'general_config',
      to: '/settings/general',
      labelKey: 'settings.general',
      icon: SlidersHorizontal,
    },
  ];

export function SettingsNav() {
  const { t } = useTranslation();
  const { dirty } = useSettingsPage();

  return (
    <nav className="w-56 shrink-0 border-r bg-muted/30 p-4">
      <h3 className="mb-4 px-3 text-sm font-semibold text-muted-foreground">
        {t('settings.title')}
      </h3>
      <ul className="space-y-1">
        {NAV_ITEMS.map(({ key, to, labelKey, icon: Icon }) => {
          const isDirty = dirty[key];
          return (
            <li key={key}>
              <NavLink
                to={to}
                end
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-foreground hover:bg-muted',
                  )
                }
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  {t(labelKey)}
                </span>
                {isDirty ? (
                  <span
                    className="h-2 w-2 rounded-full bg-orange-400"
                    aria-label={t('settings.unsavedHint')}
                  />
                ) : null}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
