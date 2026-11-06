import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "shield"
  | "plus"
  | "send"
  | "paperclip"
  | "doc"
  | "pulse"
  | "alert"
  | "phone"
  | "menu"
  | "moon"
  | "check"
  | "chart";

const PATHS: Record<IconName, ReactNode> = {
  shield: (
    <>
      <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />
      <path d="M7.5 12h2.5l1.4-2.8 1.8 5.2 1.3-2.4h2" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  send: <path d="M12 19V5M5 12l7-7 7 7" />,
  paperclip: (
    <path d="M21 12.5l-8.5 8.5a5 5 0 0 1-7-7l8.5-8.5a3.5 3.5 0 0 1 5 5L10.5 19a2 2 0 0 1-3-3l7.5-7.5" />
  ),
  doc: (
    <>
      <path d="M6 3h8l4 4v14H6z" />
      <path d="M14 3v4h4" />
      <path d="M9 12h6M9 16h4" />
    </>
  ),
  pulse: <path d="M3 12h4l2-5 4 10 2-5h6" />,
  alert: (
    <>
      <path d="M12 4l9 16H3L12 4Z" />
      <path d="M12 10v4M12 17h.01" />
    </>
  ),
  phone: (
    <path d="M5 4h4l2 5-3 2a12 12 0 0 0 5 5l2-3 5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z" />
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4a7 7 0 1 0 10.5 10.5Z" />,
  check: (
    <>
      <path d="M9 4h6v3H9z" />
      <path d="M9 5.5H7a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V7A1.5 1.5 0 0 0 17 5.5h-2" />
      <path d="M9.5 13l2 2 3.5-4" />
    </>
  ),
  chart: (
    <>
      <path d="M4 4v16h16" />
      <path d="M7 15l3.5-4 3 2.5L18 8" />
      <path d="M18 8h.01" />
    </>
  ),
};

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "name"> {
  name: IconName;
}

export function Icon({ name, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {PATHS[name]}
    </svg>
  );
}
