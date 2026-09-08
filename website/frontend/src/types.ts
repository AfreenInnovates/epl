export type AgentEventType =
  | "start"
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "tool_skipped"
  | "writing"
  | "answer"
  | "error"
  | "done";

export type ToolName =
  | "ml_player_search"
  | "player_stats_tool"
  | "search_football_web";

export interface AgentEvent {
  type: AgentEventType;
  label?: string;
  detail?: string;
  tool?: ToolName;
  call_id?: string;
  iteration?: number;
  ok?: boolean;
  duration_ms?: number;
  arguments?: Record<string, unknown>;
  data?: ToolHighlights;
  answer?: Answer;
  timestamp?: number;
}

/** A display-ready slice of what a tool actually returned. */
export interface ToolHighlights {
  query_player?: string;
  candidates?: MlCandidate[];
  players?: string[];
  sources?: { title: string; url: string }[];
}

export interface MlCandidate {
  player: string;
  club: string | null;
  position: string | null;
  models_retrieved: number;
  mean_similarity: number;
}

/** Everything the tools produced during one run, for the evidence panel. */
export interface EvidenceBase {
  subject: string | null;
  candidates: MlCandidate[];
  statsFor: string[];
  webSources: { title: string; url: string }[];
  toolCalls: number;
  refusedSearches: number;
}

export interface AnswerSimilarPlayer {
  player: string;
  reason: string;
}

export interface AnswerSource {
  title: string;
  url: string;
}

export interface Answer {
  title: string;
  summary: string;
  similar_players: AnswerSimilarPlayer[];
  statistical_evidence: string[];
  tactical_evidence: string[];
  limitations: string[];
  sources: AnswerSource[];
}

export interface PlayerSummary {
  name: string;
  club: string | null;
  position: string | null;
  position_label: string | null;
}

export interface SimilarPlayer {
  player: string;
  club: string | null;
  position: string | null;
  models_retrieved: number;
  mean_rank: number;
  best_rank: number;
  mean_similarity: number;
}

export interface Health {
  status: string;
  players: number;
  models: string[];
  groq_configured: boolean;
  web_search_configured: boolean;
  stats_available: boolean;
}

/** A completed or in-flight step, as rendered in the trace timeline. */
export interface TraceStep {
  id: string;
  kind: "thinking" | "tool" | "writing" | "error" | "skipped";
  label: string;
  detail: string;
  tool?: ToolName;
  status: "active" | "ok" | "failed" | "skipped";
  durationMs?: number;
  /** Repeats of an identical skipped step are folded into one line. */
  repeats?: number;
}
