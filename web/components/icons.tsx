/** Inline SVG icons (stroke = currentColor) — a handful, so no icon package. */

import type { ReactNode } from 'react';

type IconProps = { size?: number };

function Svg({ size = 18, children, width = 2 }: IconProps & { children: ReactNode; width?: number }) {
	return (
		<svg
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth={width}
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
		>
			{children}
		</svg>
	);
}

export const LogoIcon = ({ size }: IconProps) => (
	<Svg size={size} width={2.2}>
		<path d="M4 6.5A3.5 3.5 0 0 1 7.5 3h9A3.5 3.5 0 0 1 20 6.5v6a3.5 3.5 0 0 1-3.5 3.5H11l-4.5 4v-4A2.5 2.5 0 0 1 4 13.5z" />
		<path d="M9 9.5h6" />
	</Svg>
);

export const PlusIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M12 5v14M5 12h14" />
	</Svg>
);

export const ChipIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<rect x="5" y="5" width="14" height="14" rx="2" />
		<path d="M9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
	</Svg>
);

export const MenuIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M4 7h16M4 12h16M4 17h10" />
	</Svg>
);

export const EditIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M12 20h9" />
		<path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
	</Svg>
);

export const CopyIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<rect x="8" y="8" width="12" height="12" rx="2" />
		<path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
	</Svg>
);

export const CheckIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M5 12.5 10 17l9-10" />
	</Svg>
);

export const BoltIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M13 2 4 14h7l-1 8 9-12h-7z" />
	</Svg>
);

export const ArrowUpIcon = ({ size }: IconProps) => (
	<Svg size={size} width={2.4}>
		<path d="M12 19V5M5 12l7-7 7 7" />
	</Svg>
);

export const ArrowRightIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M5 12h14M13 6l6 6-6 6" />
	</Svg>
);

export const StopIcon = ({ size }: IconProps) => (
	<svg width={size ?? 14} height={size ?? 14} viewBox="0 0 24 24" aria-hidden="true">
		<rect x="5" y="5" width="14" height="14" rx="3" fill="currentColor" />
	</svg>
);

export const CloseIcon = ({ size }: IconProps) => (
	<Svg size={size}>
		<path d="M6 6l12 12M18 6 6 18" />
	</Svg>
);
