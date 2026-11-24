import { useEffect, useState } from "react";

type Health = { status: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/health") // same origin: the Vite dev server and nginx both forward it to the service
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: Health) => setHealth(data))
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: 24 }}>
      <h1>LabBank - S1 (Customer &amp; Account)</h1>
      {health && (
        <p>
          GET /health: <b>{health.status}</b>
        </p>
      )}
      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}
      {!health && !error && <p>Loading...</p>}
    </main>
  );
}