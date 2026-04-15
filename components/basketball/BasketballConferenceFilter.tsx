"use client";

import { useRouter } from "next/navigation";

const CONFERENCES = [
  { label: "All", slug: "" },
  { label: "SEC", slug: "sec" },
  { label: "Big Ten", slug: "big-ten" },
  { label: "Big 12", slug: "big-12" },
  { label: "ACC", slug: "acc" },
  { label: "Big East", slug: "big-east" },
  { label: "Other", slug: "other" },
] as const;

interface BasketballConferenceFilterProps {
  activeConf: string | null;
}

export default function BasketballConferenceFilter({
  activeConf,
}: BasketballConferenceFilterProps) {
  const router = useRouter();

  function handleClick(slug: string) {
    router.push(
      slug ? `/basketball/teams?conf=${slug}` : "/basketball/teams",
      { scroll: false },
    );
  }

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {CONFERENCES.map((conf) => {
        const isActive = conf.slug === (activeConf ?? "");

        return (
          <button
            key={conf.slug}
            onClick={() => handleClick(conf.slug)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              isActive
                ? "bg-emerald-500 text-white"
                : "bg-white border border-gray-200 text-slate-600 hover:border-slate-300"
            }`}
          >
            {conf.label}
          </button>
        );
      })}
    </div>
  );
}
