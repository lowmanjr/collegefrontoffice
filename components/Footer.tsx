import Link from "next/link";
import CfoLogo from "@/components/CfoLogo";

export default function Footer() {
  return (
    <footer className="bg-slate-950 text-gray-400 pt-12 pb-8">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* Grid */}
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3 pb-8 border-b border-slate-800">
          {/* Col 1: Brand */}
          <div>
            <CfoLogo height={28} showWordmark />
            <p className="mt-2 text-xs text-slate-500 leading-relaxed max-w-xs">
              Proprietary NIL valuations for college sports. Built on depth charts, production data, draft projections, and market modeling.
            </p>
          </div>

          {/* Col 2: Navigation */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Navigate</p>
            <ul className="space-y-2">
              {[
                { label: "Teams", href: "/teams" },
                { label: "Big Board", href: "/players" },
                { label: "Futures", href: "/futures" },
                { label: "Methodology", href: "/methodology" },
              ].map(({ label, href }) => (
                <li key={href}>
                  <Link href={href} className="text-sm text-slate-400 hover:text-white transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 3: About */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">About</p>
            <ul className="space-y-2">
              <li>
                <Link href="/methodology" className="text-sm text-slate-400 hover:text-white transition-colors">
                  How Valuations Work
                </Link>
              </li>
            </ul>
            <p className="mt-4 text-xs text-slate-600 leading-relaxed">
              Valuations are proprietary estimates, not financial disclosures. Not affiliated with the NCAA or any university.
            </p>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <p className="text-xs text-slate-600">© 2026 College Front Office. All rights reserved.</p>
          <p className="text-xs text-slate-700">C.F.O. Valuation Engine V3.5</p>
        </div>
      </div>
    </footer>
  );
}
