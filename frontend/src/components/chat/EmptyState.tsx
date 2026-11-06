import { HeroOrb } from "@/components/chat/HeroOrb";
import { Icon, type IconName } from "@/components/ui/Icon";
import { SUGGESTIONS } from "@/lib/constants";

const SUGGESTION_ICONS: IconName[] = ["pulse", "doc", "moon"];

interface EmptyStateProps {
  onSuggestion: (value: string) => void;
}

export function EmptyState({ onSuggestion }: EmptyStateProps) {
  return (
    <section className="empty">
      <HeroOrb />

      <p className="empty__kicker">AI HEALTH AGENT</p>
      <h1>我是智诊</h1>
      <p className="empty__sub">会查指南、会读报告，不替代医生。</p>

      <div className="suggestions">
        {SUGGESTIONS.map((suggestion, index) => (
          <button
            className="suggestion"
            type="button"
            key={suggestion}
            onClick={() => onSuggestion(suggestion)}
          >
            <span className="suggestion__index">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="suggestion__icon">
              <Icon name={SUGGESTION_ICONS[index] ?? "pulse"} />
            </span>
            <span className="suggestion__text">{suggestion}</span>
            <span className="suggestion__arrow" aria-hidden="true">
              →
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
