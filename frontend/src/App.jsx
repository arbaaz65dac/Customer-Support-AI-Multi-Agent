import { useEffect, useState } from "react";

function App() {
  const [status, setStatus] = useState("Checking backend...");
  const [error, setError] = useState("");

  useEffect(() => {
    // Ask the Python backend whether it is healthy.
    fetch("http://127.0.0.1:8000/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend returned an error.");
        }
        return response.json();
      })
      .then((data) => {
        setStatus(data.message);
      })
      .catch(() => {
        setError("Could not connect to FastAPI. Is the backend running?");
      });
  }, []);

  return (
    <main style={{ fontFamily: "Arial, sans-serif", padding: "2rem" }}>
      <h1>Customer Support AI Assistant</h1>
      <p>Day 1: Frontend and backend integration</p>

      <h2>Backend status</h2>
      {error ? <p role="alert">{error}</p> : <p>{status}</p>}
    </main>
  );
}

export default App;