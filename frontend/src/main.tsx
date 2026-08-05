import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { ErrorBoundary } from '@/components/error/ErrorBoundary';
import { Toaster } from '@/components/ui/sonner';
import './i18n';
import App from './App.tsx';
import './index.css';

const rootElement = document.getElementById('root');
if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <ErrorBoundary>
        <App />
        <Toaster position="top-right" richColors closeButton />
      </ErrorBoundary>
    </StrictMode>,
  );
}
