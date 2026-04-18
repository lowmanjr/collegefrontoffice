import Link from "next/link";
import CfoLogo from "@/components/CfoLogo";

export default function Footer() {
  return (
    <footer className="bg-slate-950 text-gray-400 pt-10 pb-6">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-8 pb-8 border-b border-slate-800">
          {/* Brand */}
          <div className="max-w-xs">
            <CfoLogo height={28} showWordmark />
            <p className="mt-3 text-xs text-slate-500 leading-relaxed">
              Proprietary NIL valuations for college sports.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-12">
            <div>
              <ul className="space-y-2">
                {[
                  { label: "Teams", href: "/football/teams" },
                  { label: "Players", href: "/football/players" },
                  { label: "Recruits", href: "/football/recruits" },
                  { label: "Methodology", href: "/football/methodology" },
                ].map(({ label, href }) => (
                  <li key={href}>
                    <Link href={href} className="text-sm text-slate-400 hover:text-white transition-colors">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom */}
        <div className="pt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <p className="text-[11px] text-slate-600">
            © 2026 College Front Office. Not affiliated with the NCAA or any university.
          </p>
        </div>
      </div>
    </footer>
  );
}
