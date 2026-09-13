import type { RunStatus } from "../hooks/useAgentStream";
import type { ToolName, TraceStep } from "../types";

type LaneState = "queued" | "active" | "complete" | "cached" | "failed";
type ResearchStatus = "idle" | "pending" | "processing" | "completed" | "failed";

interface Props {
  steps: TraceStep[];
  active: TraceStep | null;
  status: RunStatus;
  cached?: boolean;
  webRefreshing?: boolean;
  researchStatus?: ResearchStatus;
}

const LANES: Array<{
  id: string;
  name: string;
  role: string;
  detail: string;
  tool?: ToolName;
}> = [
  {
    id: "scout",
    name: "Embedding scout",
    role: "ML retrieval",
    detail: "Cross-checks standard, Siamese and triplet representations.",
    tool: "ml_player_search",
  },
  {
    id: "auditor",
    name: "Stats auditor",
    role: "Per-90 verification",
    detail: "Pulls the actual season rows instead of trusting model memory.",
    tool: "player_stats_tool",
  },
  {
    id: "web",
    name: "Anakin web scout",
    role: "Tactical context",
    detail: "Searches the open web and scrapes page-level evidence.",
    tool: "search_football_web",
  },
  {
    id: "editor",
    name: "Report editor",
    role: "Groq synthesis",
    detail: "Separates measured evidence from interpretation and limitations.",
  },
  {
    id: "agentic",
    name: "Anakin research agent",
    role: "External synthesis",
    detail: "Runs query refinement, search, citation scraping and report synthesis.",
  },
];

function laneState(
  lane: (typeof LANES)[number],
  steps: TraceStep[],
  active: TraceStep | null,
  status: RunStatus,
  cached: boolean,
  webRefreshing: boolean,
  researchStatus: ResearchStatus,
): LaneState {
  if (lane.id === "agentic") {
    if (researchStatus === "pending" || researchStatus === "processing") return "active";
    if (researchStatus === "completed") return cached ? "cached" : "complete";
    if (researchStatus === "failed") return "failed";
    return "queued";
  }

  if (lane.id === "web" && webRefreshing) {
    return "active";
  }

  if (cached) {
    return "cached";
  }

  if (lane.id === "editor") {
    if (active?.kind === "writing") return "active";
    if (status === "done") return "complete";
    if (steps.some((step) => step.kind === "writing" && step.status === "failed")) {
      return "failed";
    }
    return "queued";
  }

  const calls = steps.filter((step) => step.tool === lane.tool);

  if (active?.tool === lane.tool) return "active";
  if (calls.some((step) => step.status === "failed")) return "failed";
  if (calls.some((step) => step.status === "ok")) return "complete";
  return "queued";
}

const STATE_LABEL: Record<LaneState, string> = {
  queued: "queued",
  active: "working",
  complete: "complete",
  cached: "replayed",
  failed: "needs attention",
};

export function ResearchSquad({
  steps,
  active,
  status,
  cached = false,
  webRefreshing = false,
  researchStatus = "idle",
}: Props) {
  const completed = LANES.filter(
    (lane) =>
      laneState(lane, steps, active, status, cached, webRefreshing, researchStatus) ===
      "complete",
  ).length;

  return (
    <section className="research-squad" aria-label="Research agent squad">
      <div className="research-squad__head">
        <div>
          <span className="section__eyebrow">Research room</span>
          <h2>Five specialist lanes, one evidence chain</h2>
        </div>
        <span className="research-squad__count">
          {webRefreshing
            ? "4 replayed · web checking"
            : cached
              ? "5 replayed"
              : `${completed}/5 complete`}
        </span>
      </div>

      <p className="research-squad__lede">
        This is an orchestrated research team, not a single chatbot reply. Groq coordinates the
        run; Anakin powers the web scout and external research agent; the other lanes read the
        local ML and stats data.
      </p>

      <div className="research-squad__grid">
        {LANES.map((lane) => {
          const state = laneState(
            lane,
            steps,
            active,
            status,
            cached,
            webRefreshing,
            researchStatus,
          );

          return (
            <article className="agent-card" data-state={state} key={lane.id}>
              <div className="agent-card__topline">
                <span className="agent-card__signal" aria-hidden="true" />
                <span>{STATE_LABEL[state]}</span>
              </div>
              <strong>{lane.name}</strong>
              <span className="agent-card__role">{lane.role}</span>
              <p>{lane.detail}</p>
              {lane.tool && <code>{lane.tool}</code>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
