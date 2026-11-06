"use client";

import { useEffect, useRef } from "react";

import { EmptyState } from "@/components/chat/EmptyState";
import { MessageItem } from "@/components/chat/MessageItem";
import type { ChatMessage } from "@/lib/types";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSuggestion: (value: string) => void;
  onChip: (chip: string) => void;
}

export function MessageList({
  messages,
  isStreaming,
  onSuggestion,
  onChip,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [messages, isStreaming]);

  return (
    <div className="chat__scroll" ref={scrollRef}>
      <div className="chat__inner">
        {messages.length === 0 ? (
          <EmptyState onSuggestion={onSuggestion} />
        ) : (
          messages.map((message) => (
            <MessageItem
              key={message.id}
              message={message}
              onChip={onChip}
            />
          ))
        )}
      </div>
    </div>
  );
}
