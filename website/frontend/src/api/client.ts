import type {
  AgentEvent,
  Health,
  PlayerSummary,
  SimilarPlayer,
  WebSource,
} from "../types";

const BASE = (import.meta.env.VITE_API_BASE ?? "").trim();

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

  refreshWeb: (question: string) =>
    postJson<{ query: string; results: WebSource[] }>("/api/web/refresh", { question }),

  submitAnakinResearch: (question: string) =>
    postJson<{ job_id: string; status: string }>("/api/anakin/research", { question }),

  getAnakinResearch: (jobId: string) =>
    getJson<{
      job_id: string;
      status: string;
      report?: {
        summary: string | null;
        structured_data: Record<string, unknown>;
        citations: { title: string; url: string }[];
      };
      error?: string;
    }>(`/api/anakin/research/${encodeURIComponent(jobId)}`),
};

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const error = new Error(
      (detail as { detail?: string }).detail ?? response.statusText,
    ) as Error & { status?: number; retryAfter?: string | null };
    error.status = response.status;
    error.retryAfter = response.headers.get("Retry-After");
    throw error;
  }

  return (await response.json()) as T;
}

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
      const raw = String((message as MessageEvent).data ?? "")
        .replace(/^\uFEFF/, "")
        .trim();

      if (!raw) {
        return;
      }

      let event: AgentEvent;

      try {
        event = JSON.parse(raw) as AgentEvent;
      } catch (error) {
        onError(
          `Malformed ${name} event from the server: ${
            error instanceof Error ? error.message : "invalid JSON"
          }`,
        );
        close();
        return;
      }

      try {
        onEvent({ ...event, type: name });

        if (name === "done") {
          close();
        }
      } catch (error) {
        onError(
          `Could not process the ${name} event: ${
            error instanceof Error ? error.message : "unknown client error"
          }`,
        );
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
