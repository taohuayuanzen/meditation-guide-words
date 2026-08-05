import { AlertCircle, Send, Square } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AutoResizeTextarea } from '@/components/ui/auto-resize-textarea';
import { ChatMessage } from '@/components/workspace/ChatMessage';
import { ScriptEmptyState } from '@/components/workspace/ScriptEmptyState';
import { useToast } from '@/hooks/useToast';
import { readErrorDetail } from '@/services/http';
import { createScript } from '@/services/scriptService';
import { SSEDecoder, extractConversationId, extractStreamAnswer } from '@/utils/sseParser';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
}

export function ScriptWorkspace() {
  const { t } = useTranslation();
  const { success, error: showError } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState('');
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const nextId = () => {
    idRef.current += 1;
    return idRef.current;
  };

  useEffect(() => {
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const appendToLastAssistant = (text: string) => {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.role !== 'assistant') return prev;
      return [...prev.slice(0, -1), { ...last, content: last.content + text }];
    });
  };

  const handleSend = async () => {
    const content = input.trim();
    if (!content || isStreaming) return;

    setError('');
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', content }]);
    setInput('');
    setIsStreaming(true);
    setMessages((prev) => [...prev, { id: nextId(), role: 'assistant', content: '' }]);

    abortRef.current = new AbortController();

    try {
      const res = await fetch('/api/dify/script/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inputs: {},
          query: content,
          response_mode: 'streaming',
          conversation_id: conversationId,
          user: 'local-user',
        }),
        signal: abortRef.current.signal,
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));

      const reader = res.body?.getReader();
      if (!reader) throw new Error('Stream unavailable');
      const decoder = new TextDecoder();
      const parser = new SSEDecoder();
      let nextConversationId = conversationId;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const events = parser.push(decoder.decode(value, { stream: true }));
        for (const event of events) {
          const cid = extractConversationId(event);
          if (cid) nextConversationId = cid;
          const answer = extractStreamAnswer(event);
          if (answer) appendToLastAssistant(answer);
          if (event.event === 'error') {
            const detail = String(event.data.message ?? event.data.detail ?? t('chat.streamError'));
            setError(detail);
          }
        }
      }
      if (nextConversationId) setConversationId(nextConversationId);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        appendToLastAssistant(`\n${t('chat.stopped')}`);
      } else {
        const detail = err instanceof Error ? err.message : t('chat.streamError');
        setError(detail);
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleSaveMessage = async (content: string) => {
    try {
      await createScript({
        title: `${t('chat.save')} ${new Date().toLocaleString()}`,
        content,
        session_id: conversationId || null,
      });
      success(t('chat.saved'));
    } catch (err) {
      const detail = err instanceof Error ? err.message : t('chat.saveFailed');
      showError(detail);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      void handleSend();
    }
    if (e.key === 'Escape' && !isStreaming) {
      setInput('');
    }
  };

  const lastAssistant = messages.length > 0 ? messages[messages.length - 1] : null;
  const isAssistantStreaming = isStreaming && lastAssistant?.role === 'assistant';

  return (
    <div className="flex h-full flex-col p-4">
      {error ? (
        <Alert variant="destructive" className="mb-3">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{t('chat.streamError')}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="mb-4 flex-1 overflow-y-auto rounded-lg border p-4">
        {messages.length === 0 ? (
          <ScriptEmptyState onSelect={setInput} />
        ) : (
          messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              isStreaming={
                isAssistantStreaming && msg.id === lastAssistant?.id && msg.role === 'assistant'
              }
              onSave={
                msg.role === 'assistant' ? () => void handleSaveMessage(msg.content) : undefined
              }
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <AutoResizeTextarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.placeholder')}
          className="flex-1"
          minRows={2}
          maxRows={6}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <Button variant="destructive" onClick={handleStop}>
            <Square className="h-4 w-4" />
            <span className="ml-2 hidden sm:inline">{t('chat.stop')}</span>
          </Button>
        ) : (
          <Button onClick={() => void handleSend()} disabled={input.trim() === ''}>
            <Send className="h-4 w-4" />
            <span className="ml-2 hidden sm:inline">{t('chat.send')}</span>
          </Button>
        )}
      </div>
    </div>
  );
}
