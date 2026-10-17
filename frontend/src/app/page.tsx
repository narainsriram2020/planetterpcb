"use client";

import Link from "next/link";
import "./landing.css";

export default function LandingPage() {
  const pillars = [
    {
      title: "How it works",
      bullets: [
        "Ask about UMD courses, professors, or GenEds in plain English.",
        "An AI agent picks which PlanetTerp lookups to run through an MCP server.",
        "You get a short answer with real GPAs, ratings, and review takeaways.",
      ],
    },
    {
      title: "Try asking",
      bullets: [
        "\"Who should I take for CMSC330?\"",
        "\"Easy GenEds about astronomy?\"",
        "\"How hard is MATH141, and who grades nicest?\"",
      ],
    },
  ];

  return (
    <main className="landing-wrapper">
      <div className="landing-content">
        <div className="landing-header">
          <span className="landing-badge">PlanetTerp · Gemini · MCP</span>
          <h1>
            Terp<span className="gradient-text">Advisor</span>
          </h1>
          <p className="lead">
            An AI course advisor for UMD students. It looks up PlanetTerp&apos;s grade distributions, professor
            ratings, and student reviews, then answers with the numbers that matter.
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
            Start chatting
          </Link>
          <p className="cta-description">Follow-up questions keep the context of your conversation.</p>
        </div>
      </div>
    </main>
  );
}
