'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Composer from '@/components/Composer';
import { ArrowRightIcon, EditIcon, LogoIcon, MenuIcon } from '@/components/icons';
import Message from '@/components/Message';
import Sidebar from '@/components/Sidebar';
import { api, ChatMessage, ConversationSummary, DoneInfo, Health, streamMessage } from '@/lib/api';
import styles from './page.module.css';

const EXAMPLES = [
	{ kind: 'Explain', text: 'Explain what a LoRA adapter is in two sentences.' },
	{ kind: 'Code', text: 'Write a Python function that checks whether a string is a palindrome.' },
	{ kind: 'Compare', text: 'What is the difference between Server-Sent Events and WebSockets?' },
];

/** The badge under the greeting and in the top bar: where the model runs. */
function whereItRuns(health: Health | null, offline: boolean): { text: string; up: boolean } {
	if (offline) return { text: 'Backend offline', up: false };
	if (!health) return { text: 'Connecting…', up: false };
	if (health.provider === 'llamacpp') return { text: 'Running on this Mac', up: true };
	if (health.provider === 'openrouter') return { text: 'Cloud model · OpenRouter', up: true };
	return { text: 'Test mode · canned replies', up: true };
}

/**
 * PocketGPT: conversations on the left, the open one on the right. A reply streams in as the model
 * writes it; Stop closes the connection and keeps what was written. Everything is stored by the
 * local backend — nothing leaves the computer unless the provider is OpenRouter.
 */
export default function ChatPage() {
	const [health, setHealth] = useState<Health | null>(null);
	const [offline, setOffline] = useState<boolean>(false);
	const [conversations, setConversations] = useState<ConversationSummary[]>([]);
	const [listedAt, setListedAt] = useState<number>(0);
	const [activeId, setActiveId] = useState<string | null>(null);
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [draft, setDraft] = useState<string>('');
	const [streaming, setStreaming] = useState<boolean>(false);
	const [lastRun, setLastRun] = useState<DoneInfo | null>(null);
	const [error, setError] = useState<string>('');
	const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
	const abortRef = useRef<AbortController | null>(null);
	const bottomRef = useRef<HTMLDivElement>(null);

	const refreshList = useCallback(async () => {
		const list = await api.list();
		setListedAt(Date.now());
		setConversations(list);
	}, []);

	const newHandler = useCallback(() => {
		setDrawerOpen(false);
		if (streaming) return;
		setActiveId(null);
		setMessages([]);
		setLastRun(null);
		setError('');
	}, [streaming]);

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

	/** ⌘K / Ctrl+K starts a new chat, as in most chat apps. */
	useEffect(() => {
		const keyHandler = (event: globalThis.KeyboardEvent) => {
			if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
				event.preventDefault();
				newHandler();
			}
		};
		window.addEventListener('keydown', keyHandler);
		return () => window.removeEventListener('keydown', keyHandler);
	}, [newHandler]);

	/** HANDLERS **/
	const openHandler = async (id: string) => {
		setDrawerOpen(false);
		if (streaming) return;
		const conversation = await api.get(id);
		setActiveId(id);
		setMessages(conversation.messages);
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
		setLastRun(null);
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

	const stopHandler = () => abortRef.current?.abort();

	const title = conversations.find((c) => c.id === activeId)?.title || 'New chat';
	const where = whereItRuns(health, offline);
	const dot = `${styles.dot} ${where.up ? '' : styles.dotOff}`;

	return (
		<div className={styles.app}>
			<Sidebar
				open={drawerOpen}
				health={health}
				offline={offline}
				conversations={conversations}
				listedAt={listedAt}
				activeId={activeId}
				busy={streaming}
				onNew={newHandler}
				onOpen={openHandler}
				onDelete={deleteHandler}
				onClose={() => setDrawerOpen(false)}
			/>

			<main className={styles.main}>
				<header className={styles.topbar}>
					<button
						type="button"
						className={`${styles.iconBtn} ${styles.phoneOnly}`}
						onClick={() => setDrawerOpen(true)}
						aria-label="Open conversations"
					>
						<MenuIcon size={20} />
					</button>
					<h2>{title}</h2>
					<span className={`${styles.pill} ${styles.topPill}`}>
						<span className={dot} />
						{where.text}
					</span>
					<button
						type="button"
						className={`${styles.iconBtn} ${styles.phoneOnly}`}
						onClick={newHandler}
						disabled={streaming}
						aria-label="New chat"
					>
						<EditIcon size={19} />
					</button>
				</header>

				{messages.length === 0 ? (
					<section className={styles.empty}>
						<div className={styles.glow} aria-hidden="true" />
						<span className={styles.bigLogo}>
							<LogoIcon size={32} />
						</span>
						<h1>What can I help with?</h1>
						<p>A fine-tuned 1.5B model. It also answers in Русский and O‘zbek.</p>
						<span className={`${styles.pill} ${styles.local}`}>
							<span className={dot} />
							{health?.provider === 'llamacpp' ? 'Runs 100% on your computer · nothing leaves this Mac' : where.text}
						</span>
						<div className={styles.cards}>
							{EXAMPLES.map((example) => (
								<button
									key={example.text}
									type="button"
									className={styles.card}
									onClick={() => send(example.text)}
									disabled={offline || streaming}
								>
									<span className={styles.cardKind}>{example.kind}</span>
									<span className={styles.cardText}>{example.text}</span>
									<span className={styles.cardGo}>
										<ArrowRightIcon size={16} />
									</span>
								</button>
							))}
						</div>
					</section>
				) : (
					<section className={styles.thread}>
						{messages.map((m, index) => {
							const last = index === messages.length - 1;
							return (
								<Message
									key={m.id ?? `local-${index}`}
									message={m}
									run={last ? lastRun : null}
									writing={last && streaming}
								/>
							);
						})}
						<div ref={bottomRef} />
					</section>
				)}

				{error && <p className={styles.error}>{error}</p>}
				{offline && (
					<p className={styles.error}>
						The backend is not running. Start it with <code>pocket-api</code> (see README).
					</p>
				)}

				<Composer
					value={draft}
					onChange={setDraft}
					onSend={() => send(draft)}
					onStop={stopHandler}
					streaming={streaming}
					disabled={offline}
				/>
			</main>
		</div>
	);
}
