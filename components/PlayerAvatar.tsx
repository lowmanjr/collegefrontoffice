interface Props {
  headshot_url: string | null;
  name: string;
  position: string | null;
  size?: number;
  className?: string;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export default function PlayerAvatar({ headshot_url, name, position, size = 36, className = "" }: Props) {
  if (headshot_url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={headshot_url}
        alt={name}
        width={size}
        height={size}
        className={`rounded-full object-cover bg-slate-200 ${className}`}
        style={{ width: size, height: size }}
      />
    );
  }

  // Fallback: initials on a colored background
  const initials = getInitials(name);
  return (
    <div
      className={`rounded-full bg-slate-200 flex items-center justify-center shrink-0 ${className}`}
      style={{ width: size, height: size }}
    >
      <span className="text-slate-500 font-bold" style={{ fontSize: size * 0.38 }}>
        {initials}
      </span>
    </div>
  );
}
