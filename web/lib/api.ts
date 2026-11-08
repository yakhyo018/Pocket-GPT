/** The PocketGPT backend (FastAPI on :8200). The URL is inlined at build time (NEXT_PUBLIC_). */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8200';

export type Role = 'user' | 'assistant';

export interface ChatMessage {
	id?: number;
	role: Role;
	content: string;
	/** The user pressed Stop: this reply was cut short. */
	stopped?: boolean;
}

export interface ConversationSummary {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
}

export interface Conversation extends ConversationSummary {
	messages: ChatMessage[];
}

export interface Health {
	status: string;
	version: string;
	provider: string;
}

export interface DoneInfo {
	provider: string;
	pieces: number;
	first_token_ms: number;
	total_ms: number;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${API_URL}${path}`, init);
	if (!response.ok) throw new Error(`${init?.method ?? 'GET'} ${path} → ${response.status}`);
	return (await response.json()) as T;
}

export const api = {
	health: () => json<Health>('/health'),
	list: () => json<ConversationSummary[]>('/v1/conversations'),
	create: () => json<ConversationSummary>('/v1/conversations', { method: 'POST' }),
	get: (id: string) => json<Conversation>(`/v1/conversations/${id}`),
	remove: async (id: string) => {
		const response = await fetch(`${API_URL}/v1/conversations/${id}`, { method: 'DELETE' });
		if (!response.ok && response.status !== 404) throw new Error(`DELETE → ${response.status}`);
	},
};

export interface StreamHandlers {
	onDelta: (text: string) => void;
	onDone: (info: DoneInfo) => void;
	onError: (message: string) => void;
}

/**
 * Sends one message and reads the reply as Server-Sent Events from a POST response. The browser's
 * EventSource only does GET, so the stream is read by hand: bytes → text → blocks split by a
 * blank line → `event:` + `data:`. Aborting `signal` (the Stop button) closes the connection;
 * the server then stops generating and saves what was written.
 */
export async function streamMessage(
	conversationId: string,
	content: string,
	handlers: StreamHandlers,
	signal: AbortSignal,
): Promise<void> {
	const response = await fetch(`${API_URL}/v1/conversations/${conversationId}/messages`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ content }),
		signal,
	});
	if (!response.ok || !response.body) {
		handlers.onError(`The server answered ${response.status}.`);
		return;
	}
	const reader = response.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	for (;;) {
		const { value, done } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		let end = buffer.indexOf('\n\n');
		while (end !== -1) {
			dispatch(buffer.slice(0, end), handlers);
			buffer = buffer.slice(end + 2);
			end = buffer.indexOf('\n\n');
		}
	}
}

function dispatch(block: string, handlers: StreamHandlers): void {
	let event = 'message';
	let data = '';
	for (const line of block.split('\n')) {
		if (line.startsWith('event: ')) event = line.slice(7);
		else if (line.startsWith('data: ')) data += line.slice(6);
	}
	if (!data) return;
	const payload = JSON.parse(data);
	if (event === 'delta') handlers.onDelta(payload.text);
	else if (event === 'done') handlers.onDone(payload as DoneInfo);
	else if (event === 'error') handlers.onError(payload.message);
}
