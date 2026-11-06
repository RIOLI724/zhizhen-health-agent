"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon } from "@/components/ui/Icon";

const ITEMS = [
  { href: "/", label: "对话", icon: "pulse" as const },
  { href: "/check", label: "自查", icon: "check" as const },
  { href: "/trends", label: "趋势", icon: "chart" as const },
  { href: "/reports", label: "报告", icon: "doc" as const },
  { href: "/profile", label: "档案", icon: "shield" as const },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="bottom-nav" aria-label="底部导航">
      {ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`bottom-nav__item ${
            pathname === item.href ? "is-active" : ""
          }`}
        >
          <Icon name={item.icon} />
          <span>{item.label}</span>
        </Link>
      ))}
    </nav>
  );
}
