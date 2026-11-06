"use client";

import { useState } from "react";
import Link from "next/link";

import { Composer } from "@/components/chat/Composer";
import { MessageList } from "@/components/chat/MessageList";
import { useChatStore, useProfilesStore } from "@/components/providers/AppProviders";
import { useUi } from "@/components/layout/AppShell";
import { Icon } from "@/components/ui/Icon";

export function ChatPage() {
  const { messages, isStreaming, sendMessage } = useChatStore();
  const { activeProfile } = useProfilesStore();
  const { openSidebar } = useUi();
  const [prepOpen, setPrepOpen] = useState(false);
  const [prepText, setPrepText] = useState("");
  const [prepError, setPrepError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleSend = (
    text: string,
    deepSearch: boolean,
    reportImage: Parameters<typeof sendMessage>[2]
  ) => {
    sendMessage(text, deepSearch, reportImage);
  };

  const handleChip = (chip: string) => {
    sendMessage(chip);
  };

  const openPrep = async () => {
    setPrepOpen(true);
    setPrepText("");
    setPrepError("");
    setCopied(false);
    try {
      const history = messages
        .filter((message) => message.content.trim())
        .map(({ role, content }) => ({ role, content }));
      const response = await fetch("/api/visit-prep", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          history,
          profile: {
            relation: activeProfile.relation,
            age: activeProfile.age ? Number(activeProfile.age) : null,
            sex: activeProfile.sex || null,
            pregnant:
              activeProfile.sex === "female"
                ? activeProfile.pregnant
                : null,
          },
        }),
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      setPrepText(data.text);
    } catch {
      setPrepError("生成失败：请确认后端已启动");
    }
  };

  const copyPrep = async () => {
    try {
      await navigator.clipboard.writeText(prepText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setPrepError("复制失败，请手动选中文本复制");
    }
  };

  return (
    <div className="chat">
      <header className="chat__top">
        <button
          className="menu-btn"
          type="button"
          onClick={openSidebar}
          aria-label="打开菜单"
        >
          <Icon name="menu" />
        </button>
        <div className="chat__title">
          <strong>对话</strong>
        </div>
        <div className="chat__status">
          <button
            className="chat__prep"
            type="button"
            onClick={openPrep}
            aria-label="生成就医准备单"
          >
            <Icon name="doc" />
            <span>就医准备</span>
          </button>
          <Link href="/profile" className="profile-chip">
            {activeProfile.label}
            {activeProfile.age ? ` · ${activeProfile.age}岁` : ""}
          </Link>
          <span className="status-pill">
            <i aria-hidden="true" />
            Agent 在线
          </span>
        </div>
      </header>

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        onSuggestion={handleChip}
        onChip={handleChip}
      />

      <Composer onSend={handleSend} isStreaming={isStreaming} />

      {prepOpen ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => setPrepOpen(false)}
        >
          <div
            className="modal"
            role="dialog"
            aria-label="就医准备单"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal__head">
              <strong>就医准备单</strong>
              <button
                type="button"
                onClick={() => setPrepOpen(false)}
                aria-label="关闭"
              >
                ×
              </button>
            </div>
            {prepError ? (
              <p className="page__error">{prepError}</p>
            ) : (
              <textarea
                readOnly
                rows={12}
                value={prepText}
                placeholder="正在整理本次对话…"
              />
            )}
            <div className="modal__actions">
              <button
                type="button"
                className="page__cta"
                onClick={copyPrep}
                disabled={!prepText}
              >
                {copied ? "已复制" : "复制清单"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
