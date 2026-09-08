import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { api } from "./api/client";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { Ask } from "./routes/Ask";
import { Home } from "./routes/Home";
import type { Health } from "./types";

const FALLBACK_SUGGESTIONS = [
  "Who plays like Bukayo Saka, and why?",
  "Which defenders are most similar to Virgil van Dijk?",
  "Do all three models agree on who resembles Cole Palmer?",
  "Compare Bukayo Saka and Mohamed Salah on the ball",
  "What are Bukayo Saka's goals, assists, shots and carries per 90?",
  "Which players have the closest statistical profile to Declan Rice?",
];

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));

    api
      .suggestions()
      .then((response) => setSuggestions(response.questions))
      .catch(() => undefined);
  }, []);

  return (
    <div className="app">
      <Header health={health} />

      <main>
        <Routes>
          <Route path="/" element={<Home health={health} suggestions={suggestions} />} />
          <Route
            path="/ask"
            element={<Ask health={health} suggestions={suggestions} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}
