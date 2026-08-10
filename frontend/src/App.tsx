import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';

import { MainLayout } from '@/components/layout/MainLayout';
import { useAppBootstrap } from '@/hooks/useAppBootstrap';
import { DifySettingsPage } from '@/pages/settings/DifySettingsPage';
import { GeneralSettingsPage } from '@/pages/settings/GeneralSettingsPage';
import { LLMSettingsPage } from '@/pages/settings/LLMSettingsPage';
import { SettingsLayout } from '@/pages/settings/SettingsLayout';
import { TTSSettingsPage } from '@/pages/settings/TTSSettingsPage';

const router = createBrowserRouter([
  {
    path: '/settings',
    element: <SettingsLayout />,
    children: [
      { index: true, element: <Navigate to="/settings/llm" replace /> },
      { path: 'llm', element: <LLMSettingsPage /> },
      { path: 'tts', element: <TTSSettingsPage /> },
      { path: 'dify', element: <DifySettingsPage /> },
      { path: 'general', element: <GeneralSettingsPage /> },
    ],
  },
  { path: '*', element: <MainLayout /> },
]);

function App() {
  useAppBootstrap();

  return <RouterProvider router={router} />;
}

export default App;
