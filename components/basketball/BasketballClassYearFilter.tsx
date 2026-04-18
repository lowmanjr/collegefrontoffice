"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";

const YEARS = ["2026", "2027", "2028"];

export default function BasketballClassYearFilter() {
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
    <div className="flex gap-1.5 flex-wrap">
      {YEARS.map((year) => (
        <button
          key={year}
          onClick={() => handleClick(year)}
          className={`px-3 py-2 rounded-lg text-xs font-semibold transition-colors ${
            currentYear === year
              ? "bg-emerald-500 text-white"
              : "bg-white text-slate-600 border border-gray-200 hover:border-slate-300"
          }`}
        >
          {`Class of ${year}`}
        </button>
      ))}
    </div>
  );
}
