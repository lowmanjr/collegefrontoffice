interface OverrideSourceLinkProps {
  sourceUrl?: string | null;
}

export default function OverrideSourceLink({ sourceUrl }: OverrideSourceLinkProps) {
  if (!sourceUrl) return null;

  let hostname: string;
  try {
    hostname = new URL(sourceUrl).hostname.replace(/^www\./, "");
  } catch {
    hostname = "link";
  }

  return (
    <p className="mt-1 text-xs text-slate-500 italic">
      Source:{" "}
      <a
        href={sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="underline hover:text-slate-300 transition-colors"
      >
        {hostname}
      </a>
    </p>
  );
}
