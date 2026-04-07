import Link from "next/link";
import { supabaseAdmin } from "@/lib/supabase-admin";
import OverrideForm from "@/components/OverrideForm";
import OverrideList from "@/components/OverrideList";

export const revalidate = 0; // always fresh

export default async function OverridesPage() {
  const [playersResp, overridesResp] = await Promise.all([
    supabaseAdmin
      .from("players")
      .select("id, name, position, teams(university_name)")
      .order("name"),
    supabaseAdmin
      .from("nil_overrides")
      .select("player_id, name, total_value, years, annualized_value, source_name, source_url")
      .order("annualized_value", { ascending: false }),
  ]);

  const players = (playersResp.data ?? []).map((p: Record<string, unknown>) => ({
    id: p.id as string,
    name: p.name as string,
    position: p.position as string | null,
    team_name: (p.teams as Record<string, unknown> | null)?.university_name as string | null ?? null,
  }));

  const overrides = (overridesResp.data ?? []).map((o: Record<string, unknown>) => ({
    player_id: o.player_id as string,
    player_name: o.name as string,
    total_value: o.total_value as number,
    years: o.years as number,
    annualized_value: o.annualized_value as number,
    source_name: o.source_name as string | null,
    source_url: o.source_url as string | null,
  }));

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="mx-auto max-w-4xl px-4 py-10 space-y-8">
        <div>
          <div className="flex items-center justify-between mb-1">
            <h1
              className="text-2xl font-bold text-slate-900 uppercase tracking-wide"
              style={{ fontFamily: "var(--font-oswald), sans-serif" }}
            >
              Override Management
            </h1>
            <Link href="/admin" className="text-sm text-slate-400 hover:text-slate-700 transition-colors">
              ← Back to Inbox
            </Link>
          </div>
          <p className="text-sm text-slate-500">
            Add or remove market overrides. Overrides bypass the algorithmic valuation entirely.
            Run the valuation engine after changes to update player values.
          </p>
        </div>

        <OverrideForm players={players} />

        <div>
          <h2
            className="text-lg font-bold text-slate-900 uppercase tracking-wide mb-4"
            style={{ fontFamily: "var(--font-oswald), sans-serif" }}
          >
            Active Overrides ({overrides.length})
          </h2>
          <OverrideList initialOverrides={overrides} />
        </div>
      </div>
    </div>
  );
}
