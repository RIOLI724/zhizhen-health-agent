import { EmergencyCard } from "@/components/chat/EmergencyCard";
import { FollowUpChips } from "@/components/chat/FollowUpChips";
import { ReportCard } from "@/components/chat/ReportCard";
import { Icon } from "@/components/ui/Icon";
import type { ChatMessage } from "@/lib/types";

interface MessageItemProps {
  message: ChatMessage;
  onChip: (chip: string) => void;
}

export function MessageItem({ message, onChip }: MessageItemProps) {
  if (message.role === "user") {
    const placeholderOnly =
      message.content === "（上传了报告图片）" && message.image;
    return (
      <article className="message message--user">
        <div className="message__body">
          <div className="bubble bubble--user">
            {message.image ? (
              // eslint-disable-next-line @next/next/no-img-element -- base64 内存图片，next/image 无法优化 data URL
              <img
                className="message__image"
                src={`data:${message.image.mime};base64,${message.image.data}`}
                alt="上传的报告图片"
              />
            ) : null}
            {message.content && !placeholderOnly ? (
              <p className="bubble__text">{message.content}</p>
            ) : null}
          </div>
        </div>
        <span className="message__avatar message__avatar--user" aria-hidden="true">
          你
        </span>
      </article>
    );
  }

  const isTyping = message.streaming && message.content.length === 0;

  return (
    <article className="message">
      <span className="message__avatar" aria-hidden="true">
        <Icon name="shield" />
      </span>
      <div className="message__body">
        <div className="message__meta">智诊 · AI 健康助手 · 刚刚</div>
        <div className="bubble bubble--agent">
          {isTyping ? <TypingDots /> : null}
          {message.content ? <ReplyBlocks text={message.content} /> : null}
          {message.emergency ? (
            <EmergencyCard emergency={message.emergency} />
          ) : null}
          {message.report ? <ReportCard report={message.report} /> : null}
          <FollowUpChips chips={message.chips} onSelect={onChip} />
          {message.error ? (
            <p className="red-note">
              <Icon name="alert" />
              <span>{message.error}</span>
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

interface ReplySection {
  title: string;
  body: string;
}

const SECTION_TITLES: Record<string, string> = {
  结论: "结论",
  需要注意: "需要注意",
  就医建议: "就医建议",
};

function parseSections(text: string): ReplySection[] | null {
  const pattern = /【(结论|需要注意|就医建议)】\s*/g;
  const titles: { title: string; start: number; end: number }[] = [];
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    titles.push({ title: match[1], start: match.index, end: pattern.lastIndex });
  }
  if (titles.length < 2) return null;

  return titles.map((section, index) => {
    const bodyStart = section.end;
    const bodyEnd = index + 1 < titles.length ? titles[index + 1].start : text.length;
    return {
      title: SECTION_TITLES[section.title] ?? section.title,
      body: text.slice(bodyStart, bodyEnd).trim(),
    };
  });
}

function ReplyBlocks({ text }: { text: string }) {
  const sections = parseSections(text);
  if (!sections) {
    return <p className="reply-text">{text}</p>;
  }
  return (
    <div className="reply-blocks">
      {sections.map((section) => (
        <section className={`reply-block reply-block--${section.title}`} key={section.title}>
          <strong>{section.title}</strong>
          <p>{section.body}</p>
        </section>
      ))}
    </div>
  );
}

function TypingDots() {
  return (
    <div className="bubble--typing" aria-label="智诊正在思考">
      <span />
      <span />
      <span />
    </div>
  );
}
