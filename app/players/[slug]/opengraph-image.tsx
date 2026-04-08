import { ImageResponse } from "next/og";
import { createClient } from "@supabase/supabase-js";

export const runtime = "edge";
export const alt = "Player Valuation Card";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export default async function OGImage(props: { params: Promise<{ slug: string }> }) {
  const { slug } = await props.params;

  const { data: player } = await supabase
    .from("players")
    .select("name, position, star_rating, cfo_valuation, player_tag, is_public, teams(university_name)")
    .eq("slug", slug)
    .single();

  if (!player) {
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

  const team = player.teams as unknown as { university_name: string } | null;
  const isPrivate = player.is_public === false;
  const stars = "★".repeat(Math.min(Math.max(player.star_rating ?? 0, 0), 5));

  return new ImageResponse(
    (
      <div style={{
        display: "flex", flexDirection: "column", width: "100%", height: "100%",
        background: "#0f172a", padding: "60px 80px", fontFamily: "sans-serif",
      }}>
        {/* Top bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#94a3b8", fontSize: 18, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
            College Front Office
          </span>
          {player.position && (
            <span style={{
              background: "#1e293b", color: "#94a3b8", fontSize: 20, fontWeight: 700,
              padding: "6px 16px", borderRadius: 8, textTransform: "uppercase" as const, letterSpacing: "0.05em",
            }}>
              {player.position}
            </span>
          )}
        </div>

        {/* Player name */}
        <div style={{ display: "flex", flexDirection: "column", marginTop: 40, flex: 1 }}>
          <span style={{
            color: "white", fontSize: 72, fontWeight: 800,
            textTransform: "uppercase" as const, lineHeight: 1.1, letterSpacing: "-0.02em",
          }}>
            {player.name}
          </span>

          <div style={{ display: "flex", alignItems: "center", gap: "16px", marginTop: 16 }}>
            <span style={{ color: "#facc15", fontSize: 28 }}>{stars}</span>
            {team?.university_name && (
              <span style={{ color: "#64748b", fontSize: 22, fontWeight: 500 }}>
                {team.university_name}
              </span>
            )}
          </div>
        </div>

        {/* Valuation */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ color: "#64748b", fontSize: 16, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
              {player.player_tag === "High School Recruit" ? "CFO Futures Value" : "CFO Valuation"}
            </span>
            <span style={{
              color: isPrivate ? "#475569" : "#34d399",
              fontSize: isPrivate ? 36 : 64,
              fontWeight: 900,
              lineHeight: 1.1,
              marginTop: 4,
            }}>
              {isPrivate ? "Private" : player.cfo_valuation != null ? formatCurrency(player.cfo_valuation) : "—"}
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
