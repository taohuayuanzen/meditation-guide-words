import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

interface AutoResizeTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  minRows?: number;
  maxRows?: number;
}

export const AutoResizeTextarea = forwardRef<HTMLTextAreaElement, AutoResizeTextareaProps>(
  ({ minRows = 2, maxRows = 6, className, onChange, ...props }, forwardedRef) => {
    const innerRef = useRef<HTMLTextAreaElement>(null);
    useImperativeHandle(forwardedRef, () => innerRef.current as HTMLTextAreaElement);
    const [rows, setRows] = useState(minRows);

    // biome-ignore lint/correctness/useExhaustiveDependencies: value changes textarea scrollHeight
    useEffect(() => {
      const el = innerRef.current;
      if (!el) return;

      const lineHeight = Number.parseInt(window.getComputedStyle(el).lineHeight, 10) || 20;
      const padding =
        Number.parseInt(window.getComputedStyle(el).paddingTop, 10) +
        Number.parseInt(window.getComputedStyle(el).paddingBottom, 10);

      el.style.height = 'auto';
      const desiredRows = Math.min(
        maxRows,
        Math.max(minRows, Math.floor((el.scrollHeight - padding) / lineHeight)),
      );
      setRows(desiredRows);
      el.style.height = '';
    }, [props.value, minRows, maxRows]);

    return (
      <Textarea
        ref={innerRef}
        rows={rows}
        className={cn('resize-none', className)}
        onChange={onChange}
        {...props}
      />
    );
  },
);
AutoResizeTextarea.displayName = 'AutoResizeTextarea';
