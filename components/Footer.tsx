import CfoLogo from "@/components/CfoLogo";

export default function Footer() {
  return (
    <footer className="bg-slate-950 text-gray-400 pt-10 pb-6">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="pb-8 border-b border-slate-800">
          <div className="max-w-xs">
            <CfoLogo height={28} showWordmark />
            <p className="mt-3 text-xs text-slate-500 leading-relaxed">
              Proprietary NIL valuations for college sports.
            </p>
          </div>
        </div>
        <div className="pt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <p className="text-[11px] text-slate-600">
            © 2026 College Front Office. Not affiliated with the NCAA or any
            university.
          </p>
        </div>
      </div>
    </footer>
  );
}
