import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';

export type TestState = 'idle' | 'testing' | 'ok' | 'failed';

interface TestButtonProps {
  state: TestState;
  message: string;
  onTest: () => void;
  label: string;
}

export function TestButton({ state, message, onTest, label }: TestButtonProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2 pt-2">
      <Button variant="outline" onClick={onTest} disabled={state === 'testing'}>
        {state === 'testing' ? t('settings.testing') : label}
      </Button>
      {state === 'ok' ? (
        <span className="text-sm text-green-600 dark:text-green-400">{t('settings.testOk')}</span>
      ) : null}
      {state === 'failed' ? (
        <span className="text-sm text-destructive">
          {t('settings.testFailed')}：{message}
        </span>
      ) : null}
    </div>
  );
}
