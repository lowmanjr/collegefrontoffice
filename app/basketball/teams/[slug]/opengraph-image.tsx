import { ImageResponse } from "next/og";
import { createClient } from "@supabase/supabase-js";
import { formatCompactCurrency } from "@/lib/utils";

export const runtime = "edge";
export const alt = "Team Valuation Card";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export default async function OGImage(props: { params: Promise<{ slug: string }> }) {
  const { slug } = await props.params;

  const teamResp = await supabase
    .from("basketball_teams")
    .select("id, university_name, conference")
    .eq("slug", slug)
    .single();
  const teamId = teamResp.data?.id;

  const rosterResp = teamId
    ? await supabase
        .from("basketball_players")
        .select("cfo_valuation, is_public")
        .eq("team_id", teamId)
        .eq("roster_status", "active")
        .not("cfo_valuation", "is", null)
    : { data: [] };

  const team = teamResp.data;
  const players = rosterResp.data ?? [];
  const totalValue = players.reduce(
    (sum, p) => sum + (p.is_public !== false && p.cfo_valuation ? p.cfo_valuation : 0),
    0
  );
  const playerCount = players.length;

  if (!team) {
    return new ImageResponse(
      (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          width: "100%", height: "100%", background: "#0f172a", color: "white",
          fontSize: 48, fontWeight: 700,
        }}>
          College Front Office
        </div>
      ),
      { ...size }
    );
  }

  return new ImageResponse(
    (
      <div style={{
        display: "flex", flexDirection: "column", width: "100%", height: "100%",
        background: "#0f172a", padding: "60px 80px", fontFamily: "sans-serif",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#94a3b8", fontSize: 18, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
            College Front Office
          </span>
          {team.conference && (
            <span style={{
              background: "#1e293b", color: "#94a3b8", fontSize: 18, fontWeight: 600,
              padding: "6px 16px", borderRadius: 8, textTransform: "uppercase" as const,
            }}>
              {team.conference}
            </span>
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", marginTop: 40, flex: 1 }}>
          <span style={{ color: "#64748b", fontSize: 20, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
            Basketball Team Dashboard
          </span>
          <span style={{
            color: "white", fontSize: 72, fontWeight: 800,
            textTransform: "uppercase" as const, lineHeight: 1.1, marginTop: 8,
          }}>
            {team.university_name}
          </span>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ color: "#64748b", fontSize: 16, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
              Total Roster Market Cap
            </span>
            <span style={{ color: "#34d399", fontSize: 64, fontWeight: 900, lineHeight: 1.1, marginTop: 4 }}>
              {formatCompactCurrency(totalValue)}
            </span>
            <span style={{ color: "#475569", fontSize: 18, marginTop: 8 }}>
              {playerCount} active player{playerCount !== 1 ? "s" : ""}
            </span>
          </div>
          <span style={{ color: "#334155", fontSize: 16, fontWeight: 500 }}>
            collegefrontoffice.com
          </span>
        </div>
      </div>
    ),
    { ...size }
  );
}
