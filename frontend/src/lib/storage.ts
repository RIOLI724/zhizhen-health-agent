import type { Conversation } from "./types";

const STORAGE_KEY = "zhizhen-agent-v2";

export interface StoredState {
  conversations: Conversation[];
  currentId: string | null;
}

const EMPTY_STATE: StoredState = { conversations: [], currentId: null };

export function loadState(): StoredState {
  if (typeof window === "undefined") return EMPTY_STATE;

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_STATE;

    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return EMPTY_STATE;

    const candidate = parsed as Partial<StoredState>;
    const conversations = Array.isArray(candidate.conversations)
      ? candidate.conversations.filter(isConversation).map(normalizeConversation)
      : [];
    const currentId =
      typeof candidate.currentId === "string" &&
      conversations.some((conversation) => conversation.id === candidate.currentId)
        ? candidate.currentId
        : null;

    return { conversations, currentId };
  } catch {
    return EMPTY_STATE;
  }
}

function normalizeConversation(conversation: Conversation): Conversation {
  return {
    ...conversation,
    messages: conversation.messages.map((message) =>
      message.streaming ? { ...message, streaming: false } : message
    ),
  };
}

export function saveState(state: StoredState): void {
  if (typeof window === "undefined") return;

  try {
    // 报告图片只在会话内展示，持久化时剥离，避免占满 localStorage 配额
    const serialized = JSON.stringify(state, (key, value) =>
      key === "image" ? undefined : value
    );
    window.localStorage.setItem(STORAGE_KEY, serialized);
  } catch {
    // 隐私模式 / 配额不足时静默降级，不影响对话
  }
}

function isConversation(value: unknown): value is Conversation {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Conversation>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    Array.isArray(candidate.messages)
  );
}
