"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";

const YEARS = ["2026", "2027", "2028"];

export default function ClassYearFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentYear = searchParams.get("year") ?? "2026";

  function handleClick(year: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("year", year);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  return (
    <div className="flex gap-2 mb-4">
      {YEARS.map((year) => (
        <button
          key={year}
          onClick={() => handleClick(year)}
          className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
            currentYear === year
              ? "bg-emerald-500 text-white"
              : "bg-white border border-gray-200 text-slate-600 hover:bg-slate-50"
          }`}
        >
          {`Class of ${year}`}
        </button>
      ))}
    </div>
  );
}
