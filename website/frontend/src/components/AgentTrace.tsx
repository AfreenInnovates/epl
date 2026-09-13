import { useEffect, useRef } from "react";

import type { TraceStep } from "../types";
import type { RunStatus } from "../hooks/useAgentStream";

interface Props {
  steps: TraceStep[];
  active: TraceStep | null;
  status: RunStatus;
}

const MARKERS: Record<TraceStep["status"], string> = {
  active: "•",
  ok: "✓",
  failed: "!",
  skipped: "↩",
};

/**
 * The live line answers one question: what is the assistant doing *right now*?
 *
 * While a tool is running it names the tool. Between tool calls, when the model
 * is deciding what to do next, it says "Thinking" -- because that is genuinely
 * all we can honestly report. The model's private reasoning is never shown.
 */
function liveCopy(active: TraceStep | null, status: RunStatus) {
  if (active) {
    return {
      kind: active.kind === "tool" ? "tool" : "thinking",
      label: active.label,
      detail: active.detail,
      tool: active.tool,
      blinking: true,
    };
  }

  if (status === "running") {
    return { kind: "thinking", label: "Thinking", detail: "", tool: undefined, blinking: true };
  }

  if (status === "error") {
    return { kind: "idle", label: "Stopped", detail: "", tool: undefined, blinking: false };
  }

  return {
    kind: "idle",
    label: "Finished",
    detail: "All evidence gathered",
    tool: undefined,
    blinking: false,
  };
}

export function AgentTrace({ steps, active, status }: Props) {
  const listRef = useRef<HTMLUListElement>(null);

  // Keep the newest step in view as the run progresses.
  useEffect(() => {
    const list = listRef.current;

    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [steps.length]);

  const live = liveCopy(active, status);

  return (
    <section className="trace" aria-label="Agent activity">
      <div
        className="trace__live"
        data-kind={live.kind}
        data-active={live.blinking}
        aria-live="polite"
      >
        <span className="trace__pulse" />

        <div className="trace__live-text">
          <div className="trace__live-label">
            <span>{live.label}</span>
            {live.tool && <span className="tool-tag">{live.tool}</span>}
          </div>
          {live.detail && <div className="trace__live-detail">{live.detail}</div>}
        </div>
      </div>

      {steps.length > 0 && (
        <ul className="trace__steps" ref={listRef}>
          {steps.map((step) => (
            <li className="step" key={step.id} data-status={step.status}>
              <span className="step__marker">{MARKERS[step.status]}</span>

              <div className="step__body">
                <div className="step__label">
                  <span>{step.label}</span>

                  {step.tool && (
                    <span
                      className={
                        step.status === "ok" ? "tool-tag" : "tool-tag tool-tag--muted"
                      }
                    >
                      {step.tool}
                    </span>
                  )}

                  {step.repeats && step.repeats > 1 && (
                    <span className="step__duration">x{step.repeats}</span>
                  )}

                  {step.durationMs !== undefined && (
                    <span className="step__duration">{step.durationMs} ms</span>
                  )}
                </div>

                {step.detail && <div className="step__detail">{step.detail}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
