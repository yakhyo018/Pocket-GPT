'use client';

import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api, ChatMessage, ConversationSummary, DoneInfo, Health, streamMessage } from '@/lib/api';
import styles from './page.module.css';

const EXAMPLES = [
	'Explain what a LoRA adapter is in two sentences.',
	'Привет! Что можно посмотреть в Самарканде?',
	"Salom! Toshkentda qaysi joylarni ko'rish mumkin?",
];

/**
 * PocketGPT: conversations on the left, the open one on the right. A reply streams in as the model
 * writes it; Stop closes the connection and keeps what was written. Everything is stored by the
 * local backend — nothing leaves the computer unless the provider is OpenRouter.
 */
export default function ChatPage() {
	const [health, setHealth] = useState<Health | null>(null);
	const [offline, setOffline] = useState<boolean>(false);
	const [conversations, setConversations] = useState<ConversationSummary[]>([]);
	const [activeId, setActiveId] = useState<string | null>(null);
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [draft, setDraft] = useState<string>('');
	const [streaming, setStreaming] = useState<boolean>(false);
	const [lastRun, setLastRun] = useState<DoneInfo | null>(null);
	const [error, setError] = useState<string>('');
	const abortRef = useRef<AbortController | null>(null);
	const bottomRef = useRef<HTMLDivElement>(null);

	const refreshList = useCallback(async () => {
		setConversations(await api.list());
	}, []);

	/** LIFECYCLES **/
	useEffect(() => {
		api
			.health()
			.then((h) => {
				setHealth(h);
				return refreshList();
			})
			.catch(() => setOffline(true));
	}, [refreshList]);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
	}, [messages]);

	/** HANDLERS **/
	const openHandler = async (id: string) => {
		if (streaming) return;
		const conversation = await api.get(id);
		setActiveId(id);
		setMessages(conversation.messages);
		setLastRun(null);
		setError('');
	};

	const newHandler = () => {
		if (streaming) return;
		setActiveId(null);
		setMessages([]);
		setLastRun(null);
		setError('');
	};

	const deleteHandler = async (id: string) => {
		if (streaming || !window.confirm('Delete this conversation?')) return;
		await api.remove(id);
		if (id === activeId) newHandler();
		await refreshList();
	};

	const send = async (text: string) => {
		const content = text.trim();
		if (!content || streaming) return;
		setError('');
		setDraft('');
		let id = activeId;
		if (!id) {
			id = (await api.create()).id;
			setActiveId(id);
		}
		setMessages((prev) => [...prev, { role: 'user', content }, { role: 'assistant', content: '' }]);
		setStreaming(true);
		const controller = new AbortController();
		abortRef.current = controller;
		const appendToReply = (patch: (last: ChatMessage) => ChatMessage) =>
			setMessages((prev) => [...prev.slice(0, -1), patch(prev[prev.length - 1])]);
		try {
			await streamMessage(
				id,
				content,
				{
					onDelta: (piece) => appendToReply((last) => ({ ...last, content: last.content + piece })),
					onDone: (info) => setLastRun(info),
					onError: (message) => setError(message),
				},
				controller.signal,
			);
		} catch (err) {
			if ((err as Error).name === 'AbortError') appendToReply((last) => ({ ...last, stopped: true }));
			else setError('The backend is not reachable. Is `pocket-api` running?');
		} finally {
			setStreaming(false);
			abortRef.current = null;
			await refreshList();
		}
	};

	const submitHandler = (event: FormEvent) => {
		event.preventDefault();
		send(draft);
	};

	/** Enter sends, Shift+Enter makes a new line — the usual chat keys. */
	const keyHandler = (event: KeyboardEvent<HTMLTextAreaElement>) => {
		if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
			event.preventDefault();
			send(draft);
		}
	};

	const stopHandler = () => abortRef.current?.abort();

	return (
		<div className={styles.app}>
			<aside className={styles.sidebar}>
				<div className={styles.brand}>
					<span className={styles.logo}>P</span>
					<strong>PocketGPT</strong>
				</div>
				<button type="button" className={styles.newChat} onClick={newHandler} disabled={streaming}>
					+ New chat
				</button>
				<nav className={styles.list} aria-label="Conversations">
					{conversations.map((c) => (
						<div key={c.id} className={`${styles.item} ${c.id === activeId ? styles.active : ''}`}>
							<button type="button" className={styles.itemTitle} onClick={() => openHandler(c.id)}>
								{c.title || 'New chat'}
							</button>
							<button
								type="button"
								className={styles.itemDelete}
								aria-label={`Delete ${c.title || 'conversation'}`}
								onClick={() => deleteHandler(c.id)}
							>
								×
							</button>
						</div>
					))}
				</nav>
				<p className={styles.model}>
					{offline ? 'Backend offline' : health ? `Model: ${health.provider}` : 'Connecting…'}
				</p>
			</aside>

			<main className={styles.main}>
				<div className={styles.thread}>
					{messages.length === 0 ? (
						<div className={styles.empty}>
							<h1>What can I help with?</h1>
							<p>English, Русский or O‘zbek — PocketGPT answers in your language, on your computer.</p>
							<div className={styles.examples}>
								{EXAMPLES.map((example) => (
									<button key={example} type="button" onClick={() => send(example)} disabled={offline}>
										{example}
									</button>
								))}
							</div>
						</div>
					) : (
						messages.map((m, index) => (
							<div key={m.id ?? `local-${index}`} className={`${styles.message} ${styles[m.role]}`}>
								{m.role === 'assistant' ? (
									<div className={styles.markdown}>
										{m.content ? (
											<ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
										) : (
											<span className={styles.typing} aria-label="Writing">
												<i />
												<i />
												<i />
											</span>
										)}
										{m.stopped && <p className={styles.stopped}>Stopped</p>}
									</div>
								) : (
									<p>{m.content}</p>
								)}
							</div>
						))
					)}
					<div ref={bottomRef} />
				</div>

				{error && <p className={styles.error}>{error}</p>}
				{offline && (
					<p className={styles.error}>
						The backend is not running. Start it with <code>pocket-api</code> (see README).
					</p>
				)}

				<form className={styles.composer} onSubmit={submitHandler}>
					<textarea
						value={draft}
						onChange={(event) => setDraft(event.target.value)}
						onKeyDown={keyHandler}
						placeholder="Message PocketGPT…"
						rows={1}
						maxLength={8000}
						aria-label="Your message"
						disabled={offline}
					/>
					{streaming ? (
						<button type="button" className={styles.stop} onClick={stopHandler}>
							Stop
						</button>
					) : (
						<button type="submit" className={styles.send} disabled={!draft.trim() || offline}>
							Send
						</button>
					)}
				</form>
				<p className={styles.footnote}>
					{lastRun
						? `${lastRun.provider} · first token ${lastRun.first_token_ms} ms · ${lastRun.total_ms} ms total`
						: 'A small local model: it can be wrong. Check important answers.'}
				</p>
			</main>
		</div>
	);
}
