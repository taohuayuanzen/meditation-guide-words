export interface DifyStreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export class SSEDecoder {
  private buffer = '';
  private eventName = 'message';
  private dataLines: string[] = [];

  push(text: string): DifyStreamEvent[] {
    this.buffer += text;
    const events: DifyStreamEvent[] = [];

    while (true) {
      const newline = this.buffer.indexOf('\n');
      if (newline === -1) break;
      const rawLine = this.buffer.slice(0, newline);
      this.buffer = this.buffer.slice(newline + 1);
      const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;

      if (line === '') {
        const event = this.flushEvent();
        if (event) events.push(event);
      } else if (!line.startsWith(':')) {
        const sep = line.indexOf(':');
        const field = sep === -1 ? line : line.slice(0, sep);
        const value = sep === -1 ? '' : line.slice(sep + 1).trimStart();
        if (field === 'event') {
          this.eventName = value;
        } else if (field === 'data') {
          this.dataLines.push(value);
        }
      }
    }

    return events;
  }

  private flushEvent(): DifyStreamEvent | null {
    const name = this.eventName;
    const data = this.dataLines;
    this.eventName = 'message';
    this.dataLines = [];
    if (data.length === 0) return null;
    const payload = data.join('\n');
    try {
      return { event: name, data: JSON.parse(payload) as Record<string, unknown> };
    } catch {
      return { event: name, data: { raw: payload } };
    }
  }
}

export function extractStreamAnswer(event: DifyStreamEvent): string {
  if (
    event.event === 'message' ||
    event.event === 'agent_message' ||
    event.event === 'message_replace'
  ) {
    return typeof event.data.answer === 'string' ? event.data.answer : '';
  }
  return '';
}

export function extractConversationId(event: DifyStreamEvent): string | undefined {
  const id = event.data.conversation_id;
  return typeof id === 'string' && id !== '' ? id : undefined;
}
