"use client";

import Link from "next/link";
import "./landing.css";

export default function LandingPage() {
  const pillars = [
    {
      title: "How it works",
      bullets: [
        "Ask anything about UMD courses, professors, or GenEds.",
        "We pull fresh PlanetTerp data via MCP semantic search.",
        "Gemini summarizes with GPA context, ratings, and advice.",
      ],
    },
    {
      title: "Best prompts",
      bullets: [
        "Mention semesters or constraints (e.g., \"Fall night class\").",
        "Request comparisons to weigh multiple professors.",
        "Paste a schedule draft for heat-check feedback.",
      ],
    },
  ];

  return (
    <main className="landing-wrapper">
      <div className="landing-content">
        <div className="landing-header">
          <span className="landing-badge">PlanetTerp · Gemini · MCP</span>
          <h1>
            PlanetTerp <span className="gradient-text">Navigator</span>
          </h1>
          <p className="lead">
            A minimal, high-signal assistant for UMD students. It fuses PlanetTerp's source-of-truth data with Gemini's
            reasoning, so every answer cites real averages, grade patterns, and rating context.
          </p>
        </div>

        <div className="landing-panels">
          {pillars.map((pillar) => (
            <article key={pillar.title} className="panel-card">
              <h2>{pillar.title}</h2>
              <ul>
                {pillar.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        <div className="cta-section">
          <Link href="/chat" className="cta-button">
            Get started
          </Link>
          <p className="cta-description">Jump in, ask anything, and iterate—context sticks with you.</p>
        </div>
      </div>
    </main>
  );
}