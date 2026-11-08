import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
	title: 'PocketGPT',
	description: 'A multilingual chat model that runs on your own computer.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
	return (
		<html lang="en">
			<body>{children}</body>
		</html>
	);
}
