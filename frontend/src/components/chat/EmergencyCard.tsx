import { Icon } from "@/components/ui/Icon";
import type { EmergencyData } from "@/lib/types";

interface EmergencyCardProps {
  emergency: EmergencyData;
}

export function EmergencyCard({ emergency }: EmergencyCardProps) {
  return (
    <section className="emergency">
      <span className="emergency__badge">{emergency.level} · 立即急救</span>
      <h3>{emergency.title}</h3>
      <p>{emergency.desc}</p>
      {emergency.department ? (
        <p className="emergency__meta">
          {emergency.department} · {emergency.timeframe}
        </p>
      ) : null}
      <a className="emergency__call" href="tel:120">
        <Icon name="phone" />
        <span>{emergency.cta}</span>
      </a>
    </section>
  );
}
