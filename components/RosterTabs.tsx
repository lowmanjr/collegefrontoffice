"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";

export interface RosterTab<T> {
  key: string;
  label: string;
  emptyMessage: string;
  predicate: (player: T) => boolean;
}

interface RosterTabsProps<T> {
  tabs: RosterTab<T>[];
  players: T[];
  children: (filtered: T[], activeKey: string) => ReactNode;
  defaultKey?: string;
}

export default function RosterTabs<T>({
  tabs,
  players,
  children,
  defaultKey,
}: RosterTabsProps<T>) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const fallbackKey = defaultKey ?? tabs[0]?.key ?? "";
  const activeKey = searchParams.get("view") ?? fallbackKey;

  function handleTabClick(key: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (key === fallbackKey) {
      params.delete("view");
    } else {
      params.set("view", key);
    }
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  const activeTab = tabs.find((t) => t.key === activeKey) ?? tabs[0];
  const filtered = players.filter(activeTab.predicate);

  return (
    <>
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleTabClick(tab.key)}
            className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              activeKey === tab.key
                ? "bg-emerald-500 text-white"
                : "bg-white border border-gray-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl shadow-md border border-gray-100 p-12 text-center">
          <p className="text-sm font-semibold text-slate-400">
            {activeTab.emptyMessage}
          </p>
        </div>
      ) : (
        children(filtered, activeKey)
      )}
    </>
  );
}
