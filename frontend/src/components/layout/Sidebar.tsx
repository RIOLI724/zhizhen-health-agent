"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useChatStore } from "@/components/providers/AppProviders";
import { Icon } from "@/components/ui/Icon";

const NAV_ITEMS = [
  { href: "/", label: "对话", icon: "pulse" as const },
  { href: "/check", label: "症状自查", icon: "check" as const },
  { href: "/trends", label: "健康趋势", icon: "chart" as const },
  { href: "/reports", label: "报告库", icon: "doc" as const },
  { href: "/profile", label: "健康档案", icon: "shield" as const },
];

export function Sidebar({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const {
    conversations,
    currentId,
    newChat,
    selectConversation,
    clearAll,
  } = useChatStore();

  const goChat = () => {
    router.push("/");
    onClose();
  };

  const handleNew = () => {
    newChat();
    goChat();
  };

  const handleSelect = (id: string) => {
    selectConversation(id);
    goChat();
  };

  const handleClear = () => {
    if (window.confirm("清空所有本地对话记录？此操作不可恢复。")) {
      clearAll();
      onClose();
    }
  };

  return (
    <aside
      className={`sidebar ${isOpen ? "is-open" : ""}`}
      aria-label="应用导航"
    >
      <div className="sidebar__brand">
        <span className="brand-mark">
          <Icon name="shield" />
        </span>
        <span className="brand-text">
          <strong>智诊</strong>
        </span>
        <button
          className="sidebar__close"
          type="button"
          onClick={onClose}
          aria-label="关闭菜单"
        >
          ×
        </button>
      </div>

      <nav className="sidebar__nav" aria-label="功能导航">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? "is-active" : ""}`}
            onClick={onClose}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <button className="new-chat" type="button" onClick={handleNew}>
        <Icon name="plus" />
        <span>新对话</span>
      </button>

      <div className="sidebar__label">
        <span>对话记录</span>
        <button type="button" onClick={handleClear}>
          清空
        </button>
      </div>

      <nav className="history" aria-label="历史对话">
        {conversations.length === 0 ? (
          <p className="history-empty">对话记录会显示在这里</p>
        ) : (
          conversations.map((conversation) => (
            <button
              className={`history-item ${
                conversation.id === currentId && pathname === "/"
                  ? "is-active"
                  : ""
              }`}
              type="button"
              key={conversation.id}
              onClick={() => handleSelect(conversation.id)}
            >
              <span className="history-item__dot" aria-hidden="true" />
              <span className="history-item__title">
                {conversation.title}
              </span>
              <small>{formatTime(conversation.updatedAt)}</small>
            </button>
          ))
        )}
      </nav>

      <div className="sidebar__foot">
        <span>内容仅供参考 · 非诊断</span>
      </div>
    </aside>
  );
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  return `${String(date.getHours()).padStart(2, "0")}:${String(
    date.getMinutes()
  ).padStart(2, "0")}`;
}
