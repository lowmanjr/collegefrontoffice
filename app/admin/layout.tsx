import Link from "next/link";
import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase-server";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  // Server-side auth gate — middleware catches most cases, but this is a
  // defence-in-depth check that works even if middleware is misconfigured.
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login?redirect=/admin");
  }

  return (
    <div>
      {/* ── Admin Nav ─────────────────────────────────────────────────────── */}
      <nav className="bg-slate-950 border-b border-slate-800 px-4">
        <div className="mx-auto max-w-6xl flex items-center gap-1 h-12">
          <span
            className="text-xs font-bold uppercase tracking-widest text-green-400 mr-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Admin
          </span>
          <NavLink href="/admin">Valuation Inbox</NavLink>
          <NavLink href="/admin/overrides">Overrides</NavLink>
        </div>
      </nav>

      {children}
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="px-3 py-1.5 rounded text-xs font-semibold uppercase tracking-widest text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
      style={{ fontFamily: "var(--font-oswald), sans-serif" }}
    >
      {children}
    </Link>
  );
}
