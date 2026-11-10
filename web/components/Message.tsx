'use client';

import { Children, isValidElement, ReactElement, ReactNode, useState } from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage, DoneInfo } from '@/lib/api';
import { BoltIcon, CheckIcon, CopyIcon, LogoIcon } from './icons';
import styles from '@/app/page.module.css';

/** A "Copy" button that says "Copied" for a moment. Clipboard needs a secure context (localhost is one). */
function CopyButton({ text, label = 'Copy', className }: { text: string; label?: string; className?: string }) {
	const [copied, setCopied] = useState<boolean>(false);
	const copyHandler = async () => {
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 1500);
		} catch {
			// No clipboard permission — nothing to do; the text is still selectable.
		}
	};
	return (
		<button type="button" className={className} onClick={copyHandler}>
			{copied ? <CheckIcon size={13} /> : <CopyIcon size={13} />}
			{copied ? 'Copied' : label}
		</button>
	);
}

/** A fenced code block: react-markdown renders <pre><code class="language-x">…</code></pre>. */
function CodeBlock({ children }: { children?: ReactNode }) {
	const child = Children.toArray(children)[0];
	const code = isValidElement(child) ? (child as ReactElement<{ className?: string; children?: ReactNode }>) : null;
	const language = code?.props.className?.replace('language-', '') ?? '';
	const text = String(code?.props.children ?? '').replace(/\n$/, '');
	return (
		<div className={styles.code}>
			<header>
				<span>{language || 'code'}</span>
				<CopyButton text={text} />
			</header>
			<pre>{children}</pre>
		</div>
	);
}

const markdownComponents: Components = {
	pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
};

interface MessageProps {
	message: ChatMessage;
	/** Timing of the reply that just finished; shown under the last reply only. */
	run?: DoneInfo | null;
	writing: boolean;
}

export default function Message({ message, run, writing }: MessageProps) {
	if (message.role === 'user') return <div className={styles.user}>{message.content}</div>;

	return (
		<div className={styles.reply}>
			<span className={styles.avatar}>
				<LogoIcon size={16} />
			</span>
			<div className={styles.replyBody}>
				<div className={styles.markdown}>
					{message.content ? (
						<ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
							{message.content}
						</ReactMarkdown>
					) : (
						<span className={styles.typing} aria-label="Writing">
							<i />
							<i />
							<i />
						</span>
					)}
				</div>
				{message.stopped && <p className={styles.stopped}>Stopped</p>}
				{message.content && !writing && (
					<div className={styles.actions}>
						<CopyButton text={message.content} />
						{run && (
							<span className={styles.stats}>
								<BoltIcon size={13} />
								<b>{run.first_token_ms} ms</b> to first token · <b>{(run.total_ms / 1000).toFixed(1)} s</b>{' '}
								total
							</span>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
