import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "College Front Office — NIL Valuations for College Sports";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div style={{
        display: "flex", flexDirection: "column", width: "100%", height: "100%",
        background: "#0f172a", padding: "80px", fontFamily: "sans-serif",
        justifyContent: "center",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: 40 }}>
          <span style={{ color: "#94a3b8", fontSize: 24, fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
            College Front Office
          </span>
        </div>
        <span style={{
          color: "white", fontSize: 64, fontWeight: 800,
          textTransform: "uppercase" as const, lineHeight: 1.15, letterSpacing: "-0.02em",
          maxWidth: 900,
        }}>
          College NIL Valuations
        </span>
        <span style={{
          color: "#64748b", fontSize: 28, marginTop: 20, maxWidth: 700,
          lineHeight: 1.4,
        }}>
          The most comprehensive NIL valuation database in college sports.
        </span>
        <div style={{ display: "flex", gap: "24px", marginTop: 40 }}>
          {["Teams", "Players", "Recruits"].map((label) => (
            <span key={label} style={{
              background: "#1e293b", color: "#94a3b8", fontSize: 18, fontWeight: 600,
              padding: "8px 20px", borderRadius: 8, textTransform: "uppercase" as const, letterSpacing: "0.05em",
            }}>
              {label}
            </span>
          ))}
        </div>
        <span style={{ color: "#334155", fontSize: 16, fontWeight: 500, position: "absolute", bottom: 60, right: 80 }}>
          collegefrontoffice.com
        </span>
      </div>
    ),
    { ...size }
  );
}
