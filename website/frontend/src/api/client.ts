import type { AgentEvent, Health, PlayerSummary, SimilarPlayer } from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`);

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail as { detail?: string }).detail ?? response.statusText);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => getJson<Health>("/api/health"),

  suggestions: () => getJson<{ questions: string[] }>("/api/suggestions"),

  players: (query: string) =>
    getJson<PlayerSummary[]>(`/api/players?q=${encodeURIComponent(query)}&limit=8`),

  similar: (name: string, topK = 5) =>
    getJson<{ query_player: string; results: SimilarPlayer[] }>(
      `/api/players/${encodeURIComponent(name)}/similar?top_k=${topK}`,
    ),
};

const EVENT_NAMES: AgentEvent["type"][] = [
  "start",
  "thinking",
  "tool_call",
  "tool_result",
  "tool_skipped",
  "writing",
  "answer",
  "error",
  "done",
];

/**
 * Subscribe to the agent's execution stream.
 *
 * Returns a cancel function. The stream closes itself on `done`; EventSource
 * would otherwise reconnect and silently re-run the whole question.
 */
export function streamAnswer(
  question: string,
  onEvent: (event: AgentEvent) => void,
  onError: (message: string) => void,
): () => void {
  const source = new EventSource(
    `${BASE}/api/ask/stream?q=${encodeURIComponent(question)}`,
  );

  let closed = false;

  const close = () => {
    if (!closed) {
      closed = true;
      source.close();
    }
  };

  for (const name of EVENT_NAMES) {
    source.addEventListener(name, (message) => {
      try {
        const event = JSON.parse((message as MessageEvent).data) as AgentEvent;
        onEvent({ ...event, type: name });

        if (name === "done") {
          close();
        }
      } catch {
        onError("Received a malformed event from the server.");
        close();
      }
    });
  }

  source.onerror = () => {
    if (!closed) {
      onError("Lost the connection to the assistant.");
      close();
    }
  };

  return close;
}
