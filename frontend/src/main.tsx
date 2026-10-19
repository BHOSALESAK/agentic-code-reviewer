import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Health = {
  status: string;
  environment: string;
  demo_mode: boolean;
};

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/health")
      .then((response) => {
        if (!response.ok) throw new Error(`Backend returned ${response.status}`);
        return response.json() as Promise<Health>;
      })
      .then(setHealth)
      .catch(() => setError("Backend unavailable. Start the API on port 8000."));
  }, []);

  return (
    <main className="shell">
      <nav className="topbar">
        <span className="mark">AR</span>
        <span className="brand">Agentic Review</span>
        <span className="mode">Milestone 1 / Foundation</span>
      </nav>
      <section className="hero">
        <p className="eyebrow">Evidence before opinion</p>
        <h1>Reliable code review,<br /><em>built in layers.</em></h1>
        <p className="intro">A local-first workspace for repository context, specialist analysis, and verified findings.</p>
        <div className="status-panel">
          <div>
            <span className="label">API STATUS</span>
            <strong className={health ? "online" : error ? "offline" : "pending"}>
              {health ? "Connected" : error ? "Unavailable" : "Connecting..."}
            </strong>
          </div>
          <div>
            <span className="label">ENVIRONMENT</span>
            <strong>{health?.environment ?? "demo"}</strong>
          </div>
          <div>
            <span className="label">ANALYSIS MODE</span>
            <strong>{health?.demo_mode ? "Mock / offline" : "Configured"}</strong>
          </div>
        </div>
      </section>
      <section className="next-step">
        <span className="step-number">01</span>
        <div>
          <p className="eyebrow">Ready for the next layer</p>
          <h2>Connect a pull request</h2>
          <p>GitHub retrieval, repository context, and the review graph arrive in Milestones 3 and 4.</p>
        </div>
        <span className="arrow" aria-hidden="true">↗</span>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
