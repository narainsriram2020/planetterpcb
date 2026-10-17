import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";

// Link preview shown by Reddit, Discord, iMessage, etc. Rendered once at build time.
export const alt = "TerpGuide: who to take at UMD, backed by PlanetTerp data";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// MATH141 grade shares from the landing page example (real PlanetTerp data, Fall 2022 – Spring 2026).
const BARS = [
  { grade: "A", share: 0.3 },
  { grade: "B", share: 0.33 },
  { grade: "C", share: 0.21 },
  { grade: "D", share: 0.06 },
  { grade: "F", share: 0.04 },
  { grade: "W", share: 0.06 },
];

async function loadFont(weight: number): Promise<ArrayBuffer | null> {
  // Google Fonts serves TTF to clients without a modern user agent, which is what Satori needs.
  try {
    const css = await (
      await fetch(`https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@${weight}`)
    ).text();
    const url = css.match(/src: url\((.+?)\) format\('(?:truetype|opentype)'\)/)?.[1];
    return url ? await (await fetch(url)).arrayBuffer() : null;
  } catch {
    return null; // fall back to the default font rather than failing the build
  }
}

export default async function OpenGraphImage() {
  const [logo, bold, regular] = await Promise.all([
    readFile(join(process.cwd(), "public", "shell.png")),
    loadFont(800),
    loadFont(500),
  ]);
  const logoSrc = `data:image/png;base64,${logo.toString("base64")}`;
  const fonts = [
    ...(bold ? [{ name: "Bricolage", data: bold, weight: 800 as const }] : []),
    ...(regular ? [{ name: "Bricolage", data: regular, weight: 500 as const }] : []),
  ];
  const peak = Math.max(...BARS.map((b) => b.share));

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#faf8f5",
          fontFamily: fonts.length ? "Bricolage" : undefined,
          padding: "64px 72px",
          borderTop: "14px solid #e21833",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={logoSrc} width={52} height={66} alt="" />
            <div style={{ display: "flex", fontSize: 44, fontWeight: 800, color: "#1b1815", letterSpacing: -1.5 }}>
              Terp<span style={{ color: "#e21833" }}>Guide</span>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
            <div style={{ display: "flex", flexDirection: "column", fontSize: 76, fontWeight: 800, lineHeight: 1, letterSpacing: -3, color: "#1b1815" }}>
              <span>Who should I take</span>
              <span style={{ color: "#e21833" }}>for this class?</span>
            </div>
            <div style={{ fontSize: 30, fontWeight: 500, color: "#57514a", maxWidth: 640, lineHeight: 1.35 }}>
              Real PlanetTerp grade distributions, ratings, and reviews, answered in seconds.
            </div>
          </div>

          <div style={{ display: "flex", fontSize: 26, fontWeight: 500, color: "#8b8379" }}>terpguide.vercel.app</div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            width: 330,
            alignSelf: "center",
            padding: "28px 30px",
            borderRadius: 24,
            background: "#ffffff",
            border: "2px solid #e6e0d7",
            boxShadow: "0 24px 48px -16px rgba(27,24,21,0.18)",
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: 2, color: "#8b8379" }}>GRADE DISTRIBUTION</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 6 }}>
            <span style={{ fontSize: 36, fontWeight: 800, color: "#1b1815" }}>MATH141</span>
            <span style={{ fontSize: 36, fontWeight: 800, color: "#1b1815" }}>2.82</span>
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 14, height: 190, marginTop: 22, borderBottom: "2px solid #ece7df" }}>
            {BARS.map((b) => (
              <div key={b.grade} style={{ display: "flex", flex: 1, justifyContent: "center", alignItems: "flex-end", height: "100%" }}>
                <div style={{ width: 28, height: `${(b.share / peak) * 92}%`, background: "#e21833", borderRadius: "6px 6px 0 0" }} />
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
            {BARS.map((b) => (
              <div key={b.grade} style={{ display: "flex", flex: 1, justifyContent: "center", fontSize: 20, fontWeight: 800, color: "#8b8379" }}>
                {b.grade}
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
    { ...size, fonts },
  );
}
