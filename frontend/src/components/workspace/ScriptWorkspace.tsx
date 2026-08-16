import { AlertCircle, Send, Square } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { AutoResizeTextarea } from '@/components/ui/auto-resize-textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ChatMessage } from '@/components/workspace/ChatMessage';
import { ScriptEmptyState } from '@/components/workspace/ScriptEmptyState';
import { useToast } from '@/hooks/useToast';
import { readErrorDetail } from '@/services/http';
import { parseGeneratedScript } from '@/services/difyService';
import { createScript } from '@/services/scriptService';
import type { GeneratedScript } from '@/types';
import { SSEDecoder, extractConversationId, extractStreamAnswer } from '@/utils/sseParser';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  script?: GeneratedScript;
}

export function ScriptWorkspace() {
  const { t } = useTranslation();
  const { success, error: showError } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState('');
  const [error, setError] = useState('');
  const [errorTitle, setErrorTitle] = useState('');
  const [scriptToSave, setScriptToSave] = useState<GeneratedScript | null>(null);
  const [scriptTitle, setScriptTitle] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const getErrorTitle = (detail: string) => {
    if (detail.includes('Failed to fetch') || detail.includes('NetworkError')) {
      return t('chat.backendUnreachable');
    }
    if (detail.includes('Dify 配置未完成') || detail.toLowerCase().includes('configuration')) {
      return t('chat.difyConfigError');
    }
    if (detail.includes('Dify 连接失败') || detail.includes('Dify request failed')) {
      return t('chat.difyConnectionError');
    }
    return t('chat.streamError');
  };

  const setChatError = (detail: string) => {
    setError(detail);
    setErrorTitle(getErrorTitle(detail));
  };

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
    setErrorTitle('');
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
      let completeAnswer = '';
      let streamFailed = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const events = parser.push(decoder.decode(value, { stream: true }));
        for (const event of events) {
          const cid = extractConversationId(event);
          if (cid) nextConversationId = cid;
          const answer = extractStreamAnswer(event);
          if (answer) {
            completeAnswer += answer;
            appendToLastAssistant(answer);
          }
          if (event.event === 'error') {
            streamFailed = true;
            const detail = String(event.data.message ?? event.data.detail ?? t('chat.streamError'));
            setChatError(detail);
          }
        }
      }
      if (nextConversationId) setConversationId(nextConversationId);
      if (!streamFailed) {
        try {
          const script = parseGeneratedScript(completeAnswer);
          const readableContent = script.blocks.map((block) => block.text).join('\n\n');
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (!last || last.role !== 'assistant') return prev;
            return [...prev.slice(0, -1), { ...last, content: readableContent, script }];
          });
        } catch (parseError) {
          const detail = parseError instanceof Error ? parseError.message : t('chat.streamError');
          setChatError(`结构化引导词解析失败：${detail}`);
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        appendToLastAssistant(`\n${t('chat.stopped')}`);
      } else {
        const detail = err instanceof Error ? err.message : t('chat.streamError');
        setChatError(detail);
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const closeSaveDialog = () => {
    if (isSaving) return;
    setScriptToSave(null);
    setScriptTitle('');
  };

  const openSaveDialog = (script: GeneratedScript) => {
    setScriptToSave(script);
    setScriptTitle(script.title);
  };

  const handleSaveMessage = async () => {
    if (!scriptToSave || !scriptTitle.trim() || isSaving) return;
    setIsSaving(true);
    try {
      await createScript({
        title: scriptTitle.trim(),
        script_plan: {
          version: 1,
          target_duration_seconds: scriptToSave.target_duration_seconds,
          blocks: scriptToSave.blocks,
        },
        session_id: conversationId || null,
      });
      success(t('chat.saved'));
      setScriptToSave(null);
      setScriptTitle('');
    } catch (err) {
      const detail = err instanceof Error ? err.message : t('chat.saveFailed');
      showError(detail);
    } finally {
      setIsSaving(false);
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
    <div className="flex h-full flex-col bg-background">
      {error ? (
        <Alert variant="destructive" className="mx-auto mt-4 max-w-3xl">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>{errorTitle || t('chat.streamError')}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto min-h-full max-w-3xl">
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
                  msg.role === 'assistant' && msg.script
                    ? () => openSaveDialog(msg.script as GeneratedScript)
                    : undefined
                }
              />
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t bg-background px-4 py-4">
        <div className="mx-auto flex max-w-3xl items-end gap-3">
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
            <Button variant="destructive" onClick={handleStop} className="shrink-0">
              <Square className="h-4 w-4" />
              <span className="hidden sm:inline">{t('chat.stop')}</span>
            </Button>
          ) : (
            <Button onClick={() => void handleSend()} disabled={input.trim() === ''} className="shrink-0">
              <Send className="h-4 w-4" />
              <span className="hidden sm:inline">{t('chat.send')}</span>
            </Button>
          )}
        </div>
      </div>

      <Dialog open={scriptToSave !== null} onOpenChange={(open) => !open && closeSaveDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('chat.saveDialogTitle')}</DialogTitle>
            <DialogDescription>{t('chat.saveDialogHint')}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="script-title">{t('chat.scriptName')}</Label>
            <Input
              id="script-title"
              autoFocus
              value={scriptTitle}
              onChange={(e) => setScriptTitle(e.target.value)}
              placeholder={t('chat.scriptNamePlaceholder')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleSaveMessage();
              }}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeSaveDialog} disabled={isSaving}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => void handleSaveMessage()} disabled={isSaving || !scriptTitle.trim()}>
              {isSaving ? t('common.saving') : t('common.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
