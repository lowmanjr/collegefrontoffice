"use client";

import { useRouter } from "next/navigation";

const CONFERENCES = [
  { label: "All", slug: "", dbValue: "" },
  { label: "SEC", slug: "sec", dbValue: "SEC" },
  { label: "Big Ten", slug: "big-ten", dbValue: "Big Ten" },
  { label: "Big 12", slug: "big-12", dbValue: "Big 12" },
  { label: "ACC", slug: "acc", dbValue: "ACC" },
] as const;

interface ConferenceFilterProps {
  activeConf: string | null;
  counts: Record<string, number>;
  totalCount: number;
}

export default function ConferenceFilter({
  activeConf,
  counts,
  totalCount,
}: ConferenceFilterProps) {
  const router = useRouter();

  function handleClick(slug: string) {
    router.push(slug ? `/teams?conf=${slug}` : "/teams", { scroll: false });
  }

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {CONFERENCES.map((conf) => {
        const isActive = conf.slug === (activeConf ?? "");
        const count = conf.slug === "" ? totalCount : (counts[conf.dbValue] ?? 0);

        return (
          <button
            key={conf.slug}
            onClick={() => handleClick(conf.slug)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              isActive
                ? "bg-emerald-500 text-white"
                : "bg-white border border-gray-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {conf.label}
            <span className="ml-1.5 text-xs opacity-70">({count})</span>
          </button>
        );
      })}
    </div>
  );
}

/** Map URL slug to DB conference value */
export function confSlugToDb(slug: string | null): string | null {
  if (!slug) return null;
  const entry = CONFERENCES.find((c) => c.slug === slug);
  return entry?.dbValue || null;
}
