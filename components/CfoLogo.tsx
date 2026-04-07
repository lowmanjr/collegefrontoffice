interface Props {
  height?: number;
  showWordmark?: boolean;
  className?: string;
}

export default function CfoLogo({ height = 32, showWordmark = false, className }: Props) {
  const scale = height / 32;
  const svgWidth = Math.round(52 * scale);
  const svgHeight = height;

  return (
    <span className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox="0 0 52 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="CFO logo"
        role="img"
      >
        {/* ── C ──────────────────────────────── */}
        {/* Left vertical */}
        <rect x="0" y="0" width="5" height="32" rx="1" fill="#ffffff" />
        {/* Top horizontal */}
        <rect x="0" y="0" width="14" height="5" rx="1" fill="#ffffff" />
        {/* Bottom horizontal */}
        <rect x="0" y="27" width="14" height="5" rx="1" fill="#ffffff" />

        {/* ── F ──────────────────────────────── */}
        {/* Left vertical */}
        <rect x="18" y="0" width="5" height="32" rx="1" fill="#ffffff" />
        {/* Top horizontal */}
        <rect x="18" y="0" width="14" height="5" rx="1" fill="#ffffff" />
        {/* Middle horizontal — GREEN accent, extends 2px past letter width */}
        <rect x="18" y="13.5" width="16" height="5" rx="1" fill="#22c55e" />

        {/* ── O ──────────────────────────────── */}
        {/* Left vertical */}
        <rect x="37" y="0" width="5" height="32" rx="1" fill="#ffffff" />
        {/* Right vertical */}
        <rect x="47" y="0" width="5" height="32" rx="1" fill="#ffffff" />
        {/* Top horizontal */}
        <rect x="37" y="0" width="15" height="5" rx="1" fill="#ffffff" />
        {/* Bottom horizontal */}
        <rect x="37" y="27" width="15" height="5" rx="1" fill="#ffffff" />
      </svg>

      {showWordmark && (
        <span
          className="text-sm font-semibold text-gray-200"
          style={{ fontFamily: "var(--font-oswald), sans-serif", letterSpacing: "0.06em" }}
        >
          CollegeFrontOffice
        </span>
      )}
    </span>
  );
}
