import { toast } from 'sonner';
import { useMemo } from 'react';

export function useToast() {
  return useMemo(
    () => ({
      toast: (message: string) => toast(message),
      success: (message: string) => toast.success(message),
      error: (message: string) => toast.error(message),
    }),
    [],
  );
}
