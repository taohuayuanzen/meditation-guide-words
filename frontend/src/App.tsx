import { MainLayout } from '@/components/layout/MainLayout';
import { useAppBootstrap } from '@/hooks/useAppBootstrap';

function App() {
  useAppBootstrap();

  return <MainLayout />;
}

export default App;
