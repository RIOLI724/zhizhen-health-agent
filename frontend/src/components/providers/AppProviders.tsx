"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";

import { useChat } from "@/hooks/useChat";
import { useProfiles, type ProfilesStore } from "@/hooks/useProfiles";
import { useReports, type ReportsStore } from "@/hooks/useReports";
import type { ReportImagePayload } from "@/lib/types";

type ChatBase = ReturnType<typeof useChat>;

export interface ChatStore extends Omit<ChatBase, "sendMessage"> {
  sendMessage: (
    text: string,
    deepSearch?: boolean,
    reportImage?: ReportImagePayload | null
  ) => void;
}

const ProfilesContext = createContext<ProfilesStore | null>(null);
const ReportsContext = createContext<ReportsStore | null>(null);
const ChatContext = createContext<ChatStore | null>(null);

export function useProfilesStore(): ProfilesStore {
  const store = useContext(ProfilesContext);
  if (!store) throw new Error("useProfilesStore 必须在 AppProviders 内使用");
  return store;
}

export function useReportsStore(): ReportsStore {
  const store = useContext(ReportsContext);
  if (!store) throw new Error("useReportsStore 必须在 AppProviders 内使用");
  return store;
}

export function useChatStore(): ChatStore {
  const store = useContext(ChatContext);
  if (!store) throw new Error("useChatStore 必须在 AppProviders 内使用");
  return store;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const profiles = useProfiles();
  const reports = useReports();
  const chat = useChat();
  const savedRef = useRef<Set<string>>(new Set());

  // 档案注入：发送时自动带上当前激活的就诊人
  const chatStore = useMemo<ChatStore>(() => {
    const sendMessage = (
      text: string,
      deepSearch = false,
      reportImage: ReportImagePayload | null = null
    ) => {
      void chat.sendMessage(
        text,
        deepSearch,
        profiles.activeProfile,
        reportImage
      );
    };
    return { ...chat, sendMessage };
  }, [chat, profiles.activeProfile]);

  // 报告自动入库：带报告卡的完成消息 → 报告库
  useEffect(() => {
    const message = chat.messages[chat.messages.length - 1];
    if (
      !message ||
      message.role !== "assistant" ||
      message.streaming ||
      !message.report
    ) {
      return;
    }
    if (savedRef.current.has(message.id)) return;
    savedRef.current.add(message.id);
    reports.addReport({
      title: message.report.title,
      source: message.fromImage ? "upload" : "sample",
      rows: message.report.rows,
      note: message.report.note,
      interpretation: message.content,
      citations: message.citations,
    });
  }, [chat.messages, reports]);

  return (
    <ProfilesContext.Provider value={profiles}>
      <ReportsContext.Provider value={reports}>
        <ChatContext.Provider value={chatStore}>
          {children}
        </ChatContext.Provider>
      </ReportsContext.Provider>
    </ProfilesContext.Provider>
  );
}
