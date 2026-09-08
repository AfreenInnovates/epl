import { useEffect, useState } from "react";

import { streamAnswer } from "../api/client";
import type { AgentEvent, Answer, EvidenceBase, TraceStep } from "../types";

export type RunStatus = "idle" | "running" | "done" | "error";

interface State {
  status: RunStatus;
  question: string;
  steps: TraceStep[];
  evidence: EvidenceBase;
  answer: Answer | null;
  error: string | null;
}

const EMPTY_EVIDENCE: EvidenceBase = {
  subject: null,
  candidates: [],
  statsFor: [],
  webSources: [],
  toolCalls: 0,
  refusedSearches: 0,
};

const INITIAL: State = {
  status: "idle",
  question: "",
  steps: [],
  evidence: EMPTY_EVIDENCE,
  answer: null,
  error: null,
};

/** Close whichever step is still running, so only one line ever blinks. */
function settleActive(steps: TraceStep[]): TraceStep[] {
  return steps.map((step) =>
    step.status === "active" ? { ...step, status: "ok" } : step,
  );
}

/**
 * Append a step, folding it into the previous one when it repeats.
 *
 * The model will happily attempt a fourth and fifth web search after the budget
 * is spent. Each refusal is real, but printing them as separate lines reads as
 * something going wrong rather than something being handled.
 */
function appendStep(steps: TraceStep[], step: TraceStep): TraceStep[] {
  const settled = settleActive(steps);
  const last = settled[settled.length - 1];

  if (last && last.kind === step.kind && last.label === step.label) {
    return [
      ...settled.slice(0, -1),
      { ...last, repeats: (last.repeats ?? 1) + 1 },
    ];
  }

  return [...settled, step];
}

function collectEvidence(evidence: EvidenceBase, event: AgentEvent): EvidenceBase {
  const data = event.data;

  if (!data) {
    return evidence;
  }

  if (event.tool === "ml_player_search") {
    return {
      ...evidence,
      subject: data.query_player ?? evidence.subject,
      // A later search replaces the shortlist rather than concatenating, so the
      // panel always reflects one coherent set of candidates.
      candidates: data.candidates ?? evidence.candidates,
    };
  }

  if (event.tool === "player_stats_tool") {
    const merged = new Set([...evidence.statsFor, ...(data.players ?? [])]);
    return { ...evidence, statsFor: [...merged] };
  }

  if (event.tool === "search_football_web") {
    const seen = new Set(evidence.webSources.map((source) => source.url));
    const added = (data.sources ?? []).filter((source) => !seen.has(source.url));

    return { ...evidence, webSources: [...evidence.webSources, ...added] };
  }

  return evidence;
}

function reduce(state: State, event: AgentEvent): State {
  switch (event.type) {
    case "thinking":
      return {
        ...state,
        steps: appendStep(state.steps, {
          id: `think-${event.iteration ?? state.steps.length}`,
          kind: "thinking",
          label: event.label ?? "Thinking",
          detail: event.detail ?? "",
          status: "active",
        }),
      };

    case "tool_call":
      return {
        ...state,
        evidence: { ...state.evidence, toolCalls: state.evidence.toolCalls + 1 },
        steps: [
          ...settleActive(state.steps),
          {
            id: event.call_id ?? `tool-${state.steps.length}`,
            kind: "tool",
            label: event.label ?? "Calling a tool",
            detail: event.detail ?? "",
            tool: event.tool,
            status: "active",
          },
        ],
      };

    case "tool_result":
      return {
        ...state,
        evidence: collectEvidence(state.evidence, event),
        steps: state.steps.map((step) =>
          step.id === event.call_id
            ? {
                ...step,
                status: event.ok === false ? "failed" : "ok",
                detail: event.detail ?? step.detail,
                durationMs: event.duration_ms,
              }
            : step,
        ),
      };

    case "tool_skipped":
      return {
        ...state,
        evidence: {
          ...state.evidence,
          refusedSearches: state.evidence.refusedSearches + 1,
        },
        steps: appendStep(state.steps, {
          id: `${event.call_id ?? state.steps.length}-skipped`,
          kind: "skipped",
          label: event.label ?? "Skipped a repeat call",
          detail: event.detail ?? "",
          tool: event.tool,
          status: "skipped",
        }),
      };

    case "writing":
      return {
        ...state,
        steps: [
          ...settleActive(state.steps),
          {
            id: "writing",
            kind: "writing",
            label: event.label ?? "Writing answer",
            detail: event.detail ?? "",
            status: "active",
          },
        ],
      };

    case "answer":
      return {
        ...state,
        answer: event.answer ?? null,
        steps: settleActive(state.steps),
      };

    case "error":
      return {
        ...state,
        status: "error",
        error: event.detail ?? "Something went wrong.",
        steps: appendStep(state.steps, {
          id: `error-${state.steps.length}`,
          kind: "error",
          label: event.label ?? "Something went wrong",
          detail: event.detail ?? "",
          status: "failed",
        }),
      };

    case "done":
      return {
        ...state,
        status: state.status === "error" ? "error" : "done",
        steps: settleActive(state.steps),
      };

    default:
      return state;
  }
}

/**
 * Subscribe to a run of `question`, or sit idle when it is empty.
 *
 * The subscription is an effect keyed on the question rather than something
 * `ask()` starts imperatively. The imperative form could not survive a
 * remount: React unmounts and remounts every component once in development,
 * and the cleanup closed the EventSource without anything re-opening it — the
 * first two events arrived, the connection died, and the interface sat on
 * "Thinking" for as long as you left it. As an effect, a remount tears the
 * stream down and establishes it again, which is what a subscription is for.
 *
 * The question lives in the URL, so asking is navigation: set `?q=`, and the
 * effect below picks it up.
 */
export function useAgentStream(question: string, attempt = 0) {
  const [state, setState] = useState<State>(INITIAL);

  useEffect(() => {
    const asked = question.trim();

    if (!asked) {
      setState(INITIAL);
      return;
    }

    setState({ ...INITIAL, status: "running", question: asked });

    return streamAnswer(
      asked,
      (event) => setState((previous) => reduce(previous, event)),
      (message) =>
        setState((previous) => ({
          ...previous,
          status: "error",
          // A run that already said why it failed -- a rate limit, a missing
          // key -- has told the reader more than "lost the connection", which
          // is only how that same failure looks from the browser once the
          // server hangs up. Keep the first, more specific explanation.
          error: previous.error ?? message,
          steps: settleActive(previous.steps),
        })),
    );
    // `attempt` is the retry nonce: asking the same question again does not
    // change the URL, so without it a run could never be repeated.
  }, [question, attempt]);

  const active = state.steps.find((step) => step.status === "active") ?? null;

  return { ...state, active };
}
