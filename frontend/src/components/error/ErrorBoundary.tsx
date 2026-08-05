import { Component, type ReactNode } from 'react';

import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen flex-col items-center justify-center gap-4 p-6 text-center">
          <h1 className="text-2xl font-semibold">出错了</h1>
          <p className="max-w-md text-muted-foreground">
            {this.state.error?.message ?? '应用发生未知错误，请刷新页面重试。'}
          </p>
          <Button onClick={() => window.location.reload()}>刷新页面</Button>
        </div>
      );
    }

    return this.props.children;
  }
}
