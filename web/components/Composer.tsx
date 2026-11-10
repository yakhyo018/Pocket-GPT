'use client';

import { ChangeEvent, FormEvent, KeyboardEvent, useRef } from 'react';
import { ArrowUpIcon, StopIcon } from './icons';
import styles from '@/app/page.module.css';

interface ComposerProps {
	value: string;
	onChange: (value: string) => void;
	onSend: () => void;
	onStop: () => void;
	streaming: boolean;
	disabled: boolean;
}

/** The message box: grows with the text up to 200 px; Enter sends, Shift+Enter makes a new line. */
export default function Composer({ value, onChange, onSend, onStop, streaming, disabled }: ComposerProps) {
	const boxRef = useRef<HTMLTextAreaElement>(null);

	const changeHandler = (event: ChangeEvent<HTMLTextAreaElement>) => {
		const box = event.target;
		box.style.height = 'auto';
		box.style.height = `${Math.min(box.scrollHeight, 200)}px`;
		onChange(box.value);
	};

	const send = () => {
		onSend();
		if (boxRef.current) boxRef.current.style.height = 'auto';
	};

	const submitHandler = (event: FormEvent) => {
		event.preventDefault();
		send();
	};

	const keyHandler = (event: KeyboardEvent<HTMLTextAreaElement>) => {
		if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
			event.preventDefault();
			send();
		}
	};

	return (
		<div className={styles.composerWrap}>
			<form className={styles.composer} onSubmit={submitHandler}>
				<textarea
					ref={boxRef}
					value={value}
					onChange={changeHandler}
					onKeyDown={keyHandler}
					placeholder="Message PocketGPT…"
					rows={1}
					maxLength={8000}
					aria-label="Your message"
					disabled={disabled}
				/>
				{streaming ? (
					<button type="button" className={styles.stop} onClick={onStop} aria-label="Stop">
						<StopIcon size={14} />
					</button>
				) : (
					<button type="submit" className={styles.send} disabled={!value.trim() || disabled} aria-label="Send">
						<ArrowUpIcon size={18} />
					</button>
				)}
			</form>
			<p className={styles.hint}>
				<kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line · A small local model — check
				important answers.
			</p>
		</div>
	);
}
