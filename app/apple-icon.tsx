import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        width: "100%", height: "100%", background: "#0f172a",
        borderRadius: 36,
      }}>
        <span style={{ color: "white", fontSize: 80, fontWeight: 900, letterSpacing: "-0.03em" }}>
          CFO
        </span>
      </div>
    ),
    { ...size }
  );
}
