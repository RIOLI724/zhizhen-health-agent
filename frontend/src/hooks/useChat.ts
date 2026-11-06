"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { streamChat } from "@/lib/api";
import { loadState, saveState } from "@/lib/storage";
import type {
  ChatMessage,
  Conversation,
  ReportImagePayload,
  Role,
  SessionProfile,
} from "@/lib/types";

function createId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createMessage(role: Role, content: string): ChatMessage {
  return {
    id: createId(),
    role,
    content,
    toolCalls: [],
    citations: [],
    chips: [],
    streaming: false,
  };
}

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState("");
  const [hydrated, setHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect -- 首次挂载从 localStorage 恢复历史，属于外部存储同步 */
  useEffect(() => {
    const saved = loadState();
    setConversations(saved.conversations);
    setCurrentId(saved.currentId);
    setHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (hydrated) saveState({ conversations, currentId });
  }, [conversations, currentId, hydrated]);

  const current = useMemo(
    () => conversations.find((conversation) => conversation.id === currentId) ?? null,
    [conversations, currentId]
  );

  const messages = current?.messages ?? [];

  const newChat = useCallback(() => {
    setCurrentId(null);
    setError("");
  }, []);

  const selectConversation = useCallback((id: string) => {
    setCurrentId(id);
    setError("");
  }, []);

  const clearAll = useCallback(() => {
    setConversations([]);
    setCurrentId(null);
    setError("");
  }, []);

  const sendMessage = useCallback(
    async (
      text: string,
      deepSearch = false,
      profile?: SessionProfile,
      reportImage?: ReportImagePayload | null
    ) => {
      const value = text.trim();
      if ((!value && !reportImage) || isStreaming) return;

      setError("");
      setIsStreaming(true);

      const existing = current;
      const conversationId = existing?.id ?? createId();
      // 过滤空内容消息（如请求失败留下的占位），避免 422 死循环
      const history = existing
        ? existing.messages
            .filter((message) => message.content.trim().length > 0)
            .map(({ role, content }) => ({ role, content }))
        : [];

      const userMessage: ChatMessage = {
        ...createMessage("user", value || "（上传了报告图片）"),
        ...(reportImage
          ? { image: { data: reportImage.data, mime: reportImage.mime } }
          : {}),
      };
      const assistantMessage: ChatMessage = {
        ...createMessage("assistant", ""),
        fromImage: Boolean(reportImage),
        streaming: true,
      };

      setConversations((previous) => {
        if (existing) {
          return previous.map((conversation) =>
            conversation.id === conversationId
              ? {
                  ...conversation,
                  messages: [
                    ...conversation.messages,
                    userMessage,
                    assistantMessage,
                  ],
                  updatedAt: Date.now(),
                }
              : conversation
          );
        }

        const conversation: Conversation = {
          id: conversationId,
          title: value.slice(0, 18),
          messages: [userMessage, assistantMessage],
          updatedAt: Date.now(),
        };
        return [conversation, ...previous];
      });
      setCurrentId(conversationId);

      const updateAssistant = (
        updater: (message: ChatMessage) => ChatMessage
      ): void => {
        setConversations((previous) =>
          previous.map((conversation) =>
            conversation.id === conversationId
              ? {
                  ...conversation,
                  messages: conversation.messages.map((message) =>
                    message.id === assistantMessage.id
                      ? updater(message)
                      : message
                  ),
                  updatedAt: Date.now(),
                }
              : conversation
          )
        );
      };

      try {
        await streamChat({
          message: value,
          history,
          deepSearch,
          profile,
          reportImage,
          onEvent: (event) => {
            switch (event.type) {
              case "delta":
                updateAssistant((message) => ({
                  ...message,
                  content: message.content + event.content,
                }));
                break;
              case "replace":
                updateAssistant((message) => ({
                  ...message,
                  content: event.content,
                }));
                break;
              case "tool_call":
                updateAssistant((message) => ({
                  ...message,
                  toolCalls: [
                    ...message.toolCalls,
                    { name: event.name, arguments: event.arguments },
                  ],
                }));
                break;
              case "chips":
                updateAssistant((message) => ({
                  ...message,
                  chips: event.items,
                }));
                break;
              case "citations":
                updateAssistant((message) => ({
                  ...message,
                  citations: event.items,
                }));
                break;
              case "emergency":
                updateAssistant((message) => ({
                  ...message,
                  emergency: event.data,
                }));
                break;
              case "report":
                updateAssistant((message) => ({
                  ...message,
                  report: event.data,
                }));
                break;
              case "risk":
                updateAssistant((message) => ({
                  ...message,
                  risk: event.data,
                }));
                break;
              case "done":
                updateAssistant((message) => ({
                  ...message,
                  streaming: false,
                }));
                break;
              case "error":
                updateAssistant((message) => ({
                  ...message,
                  error: event.detail,
                  streaming: false,
                }));
                setError(event.detail);
                break;
              default:
                break;
            }
          },
        });
      } catch (streamError) {
        const detail =
          streamError instanceof Error ? streamError.message : "请求失败";
        updateAssistant((message) => ({
          ...message,
          error: detail,
          streaming: false,
        }));
        setError(detail);
      } finally {
        setIsStreaming(false);
      }
    },
    [current, isStreaming]
  );

  return {
    conversations,
    currentId,
    messages,
    isStreaming,
    error,
    sendMessage,
    newChat,
    selectConversation,
    clearAll,
  };
}
