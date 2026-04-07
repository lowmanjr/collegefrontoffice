import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        width: 32,
        height: 32,
        background: "#0f172a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 6,
        padding: "4px 3px",
        gap: 1,
      }}
    >
      {/* C */}
      <div style={{ display: "flex", flexDirection: "column", width: 8, height: 22, position: "relative" }}>
        <div style={{ width: 8, height: 3, background: "white", borderRadius: 1 }} />
        <div style={{ width: 3, height: 22, background: "white", borderRadius: 1, position: "absolute", left: 0, top: 0 }} />
        <div style={{ width: 8, height: 3, background: "white", borderRadius: 1, position: "absolute", bottom: 0, left: 0 }} />
      </div>

      {/* F */}
      <div style={{ display: "flex", flexDirection: "column", width: 9, height: 22, position: "relative" }}>
        <div style={{ width: 8, height: 3, background: "white", borderRadius: 1 }} />
        <div style={{ width: 3, height: 22, background: "white", borderRadius: 1, position: "absolute", left: 0, top: 0 }} />
        <div style={{ width: 9, height: 3, background: "#22c55e", borderRadius: 1, position: "absolute", top: 9, left: 0 }} />
      </div>

      {/* O */}
      <div style={{ display: "flex", flexDirection: "column", width: 9, height: 22, position: "relative" }}>
        <div style={{ width: 9, height: 3, background: "white", borderRadius: 1 }} />
        <div style={{ width: 3, height: 22, background: "white", borderRadius: 1, position: "absolute", left: 0, top: 0 }} />
        <div style={{ width: 3, height: 22, background: "white", borderRadius: 1, position: "absolute", right: 0, top: 0 }} />
        <div style={{ width: 9, height: 3, background: "white", borderRadius: 1, position: "absolute", bottom: 0, left: 0 }} />
      </div>
    </div>,
    { ...size }
  );
}
