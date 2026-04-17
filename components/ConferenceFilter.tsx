"use client";

import { useRouter, usePathname } from "next/navigation";

export type ConferenceOption = { label: string; slug: string };

interface ConferenceFilterProps {
  conferences: ConferenceOption[];
  activeConf: string | null;
  paramName?: string;
}

export default function ConferenceFilter({
  conferences,
  activeConf,
  paramName = "conf",
}: ConferenceFilterProps) {
  const router = useRouter();
  const pathname = usePathname();

  const options: ConferenceOption[] = [{ label: "All", slug: "" }, ...conferences];

  function handleClick(slug: string) {
    router.push(slug ? `${pathname}?${paramName}=${slug}` : pathname, { scroll: false });
  }

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {options.map((conf) => {
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
