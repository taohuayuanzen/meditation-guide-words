import { Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';

interface ScriptEmptyStateProps {
  onSelect: (text: string) => void;
}

export function ScriptEmptyState({ onSelect }: ScriptEmptyStateProps) {
  const { t } = useTranslation();

  const examples = [t('chat.emptyExample1'), t('chat.emptyExample2'), t('chat.emptyExample3')];

  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 p-6 text-center">
      <div className="rounded-full bg-primary p-4 text-primary-foreground">
        <Sparkles className="h-7 w-7" />
      </div>
      <div>
        <p className="text-xl font-semibold">{t('chat.emptyTitle')}</p>
        <p className="text-sm text-muted-foreground">{t('chat.emptyHint')}</p>
      </div>
      <div className="flex max-w-md flex-wrap justify-center gap-2">
        {examples.map((text) => (
          <Button key={text} variant="outline" size="sm" onClick={() => onSelect(text)}>
            {text}
          </Button>
        ))}
      </div>
    </div>
  );
}
