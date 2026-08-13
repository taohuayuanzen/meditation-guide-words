import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { ArtifactWorkspace } from '@/components/workspace/ArtifactWorkspace';
import { AudioWorkspace } from '@/components/workspace/AudioWorkspace';
import { MusicWorkspace } from '@/components/workspace/MusicWorkspace';
import { ScriptWorkspace } from '@/components/workspace/ScriptWorkspace';
import { useAppStore } from '@/stores/appStore';

export function MainLayout() {
  const { currentWorkspace } = useAppStore();

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <div className={currentWorkspace === 'script' ? 'h-full' : 'hidden'}>
            <ScriptWorkspace />
          </div>
          <div className={currentWorkspace === 'audio' ? 'h-full' : 'hidden'}>
            <AudioWorkspace active={currentWorkspace === 'audio'} />
          </div>
          <div className={currentWorkspace === 'music' ? 'h-full' : 'hidden'}>
            <MusicWorkspace active={currentWorkspace === 'music'} />
          </div>
          <div className={currentWorkspace === 'artifact' ? 'h-full' : 'hidden'}>
            <ArtifactWorkspace active={currentWorkspace === 'artifact'} />
          </div>
        </main>
      </div>
    </div>
  );
}
