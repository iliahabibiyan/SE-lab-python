import { useEffect, useState } from "react";

const API_URL: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8081";

type Health = { status: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
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