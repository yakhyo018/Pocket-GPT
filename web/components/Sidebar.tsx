'use client';

import type { ConversationSummary, Health } from '@/lib/api';
import { ChipIcon, CloseIcon, LogoIcon, PlusIcon } from './icons';
import styles from '@/app/page.module.css';

/**
 * Today / Yesterday / Previous 7 days / Earlier — by the last message, in the browser's time zone.
 * `now` is taken when the list is fetched (an effect), never during render: Next.js prerenders this
 * page, and a clock read there would freeze the build time into the HTML.
 */
function groupByDay(conversations: ConversationSummary[], now: number): [string, ConversationSummary[]][] {
	const startOfToday = new Date(now);
	startOfToday.setHours(0, 0, 0, 0);
	const day = 24 * 60 * 60 * 1000;
	const groups = new Map<string, ConversationSummary[]>();
	for (const c of conversations) {
		const at = new Date(c.updated_at).getTime();
		const label =
			at >= startOfToday.getTime()
				? 'Today'
				: at >= startOfToday.getTime() - day
					? 'Yesterday'
					: at >= startOfToday.getTime() - 7 * day
						? 'Previous 7 days'
						: 'Earlier';
		groups.set(label, [...(groups.get(label) ?? []), c]);
	}
	return [...groups.entries()];
}

/** Where the replies come from, in words a visitor understands. */
export function describeProvider(provider: string): string {
	if (provider === 'llamacpp') return 'llama.cpp · on this Mac';
	if (provider === 'openrouter') return 'OpenRouter · cloud';
	return 'Test replies';
}

interface SidebarProps {
	open: boolean;
	health: Health | null;
	offline: boolean;
	conversations: ConversationSummary[];
	/** When the list was fetched (ms). */
	listedAt: number;
	activeId: string | null;
	busy: boolean;
	onNew: () => void;
	onOpen: (id: string) => void;
	onDelete: (id: string) => void;
	onClose: () => void;
}

export default function Sidebar(props: SidebarProps) {
	const { open, health, offline, conversations, listedAt, activeId, busy, onNew, onOpen, onDelete, onClose } = props;
	return (
		<>
			{open && <div className={styles.scrim} onClick={onClose} aria-hidden="true" />}
			<aside className={`${styles.sidebar} ${open ? styles.sidebarOpen : ''}`}>
				<div className={styles.brand}>
					<span className={styles.logo}>
						<LogoIcon size={18} />
					</span>
					<strong>PocketGPT</strong>
					<span className={styles.tag}>LOCAL</span>
				</div>

				<button type="button" className={styles.newChat} onClick={onNew} disabled={busy}>
					<PlusIcon size={16} />
					New chat
					<kbd>⌘ K</kbd>
				</button>

				<nav className={styles.list} aria-label="Conversations">
					{conversations.length === 0 && <p className={styles.listEmpty}>Your conversations appear here.</p>}
					{groupByDay(conversations, listedAt).map(([label, items]) => (
						<section key={label}>
							<h3 className={styles.group}>{label}</h3>
							{items.map((c) => (
								<div key={c.id} className={`${styles.item} ${c.id === activeId ? styles.active : ''}`}>
									<button type="button" className={styles.itemTitle} onClick={() => onOpen(c.id)}>
										{c.title || 'New chat'}
									</button>
									<button
										type="button"
										className={styles.itemDelete}
										aria-label={`Delete ${c.title || 'conversation'}`}
										onClick={() => onDelete(c.id)}
									>
										<CloseIcon size={14} />
									</button>
								</div>
							))}
						</section>
					))}
				</nav>

				<div className={styles.modelCard}>
					<span className={styles.chip}>
						<ChipIcon size={18} />
					</span>
					<div className={styles.modelText}>
						<b>{offline ? 'Backend offline' : health ? health.model || health.provider : 'Connecting…'}</b>
						<small>
							<span className={`${styles.dot} ${offline ? styles.dotOff : ''}`} />
							{offline ? 'Start pocket-api' : health ? describeProvider(health.provider) : '…'}
						</small>
					</div>
				</div>
			</aside>
		</>
	);
}
