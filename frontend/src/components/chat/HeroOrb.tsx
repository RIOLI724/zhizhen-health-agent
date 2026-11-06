export function HeroOrb() {
  return (
    <div className="hero-orb" aria-hidden="true">
      <svg className="hero-orb__svg" viewBox="0 0 240 240">
        <defs>
          <radialGradient id="orbCore" cx="35%" cy="30%" r="72%">
            <stop offset="0%" stopColor="#f7fffc" />
            <stop offset="45%" stopColor="#b9ecdd" />
            <stop offset="100%" stopColor="#0f5f52" />
          </radialGradient>
          <linearGradient id="orbRing" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#c98a5f" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#a7e3d0" stopOpacity="0.1" />
          </linearGradient>
          <filter id="orbGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="10" />
          </filter>
        </defs>

        <circle
          cx="120"
          cy="120"
          r="86"
          fill="#a7e3d0"
          opacity="0.18"
          filter="url(#orbGlow)"
        />

        <circle cx="120" cy="120" r="64" fill="url(#orbCore)" />
        <circle
          cx="120"
          cy="120"
          r="64"
          fill="none"
          stroke="rgba(255,255,255,0.35)"
          strokeWidth="1"
        />

        <circle
          className="hero-orb__ring hero-orb__ring--a"
          cx="120"
          cy="120"
          r="86"
          fill="none"
          stroke="url(#orbRing)"
          strokeWidth="1.2"
          strokeDasharray="4 8"
        />
        <circle
          cx="120"
          cy="120"
          r="102"
          fill="none"
          stroke="rgba(201,138,95,0.18)"
          strokeWidth="1"
        />

        <path
          className="hero-orb__pulse"
          d="M64 124h22l10-22 14 44 12-34 10 12h36"
          fill="none"
          stroke="#fbf8f2"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        <circle className="hero-orb__dot hero-orb__dot--a" cx="196" cy="78" r="4" fill="#c98a5f" />
        <circle className="hero-orb__dot hero-orb__dot--b" cx="54" cy="164" r="3" fill="#a7e3d0" />
      </svg>
    </div>
  );
}
