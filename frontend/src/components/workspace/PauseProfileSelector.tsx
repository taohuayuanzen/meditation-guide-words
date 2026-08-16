import { useTranslation } from 'react-i18next';

import type { PauseProfile, PauseProfileId } from '@/types';
import { cn } from '@/lib/utils';

interface Props {
  profiles: PauseProfile[];
  value: PauseProfileId;
  onChange: (value: PauseProfileId) => void;
  disabled?: boolean;
}

const IDS: PauseProfileId[] = ['gentle_v1', 'standard_v1', 'deep_v1'];

export function PauseProfileSelector({ profiles, value, onChange, disabled }: Props) {
  const { t } = useTranslation();
  const available = new Set(profiles.map((profile) => profile.id));
  return (
    <fieldset disabled={disabled} className="space-y-2">
      <legend className="text-sm font-medium">{t('audio.pauseProfile')}</legend>
      <div className="grid gap-2 sm:grid-cols-3">
        {IDS.map((id) => (
          <button
            key={id}
            type="button"
            disabled={disabled || !available.has(id)}
            aria-pressed={value === id}
            onClick={() => onChange(id)}
            className={cn(
              'rounded-xl border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50',
              value === id ? 'border-primary bg-primary/5' : 'hover:bg-muted',
            )}
          >
            <span className="block font-medium">{t(`audio.pauseProfiles.${id}.name`)}</span>
            <span className="mt-1 block text-xs text-muted-foreground">
              {t(`audio.pauseProfiles.${id}.description`)}
            </span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
