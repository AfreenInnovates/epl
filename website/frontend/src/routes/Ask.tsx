import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { AgentTrace } from "../components/AgentTrace";
import { AnswerView } from "../components/AnswerView";
import { AskBar } from "../components/AskBar";
import { EvidenceBasePanel } from "../components/EvidenceBase";
import { useAgentStream } from "../hooks/useAgentStream";
import type { Health } from "../types";

interface Props {
  health: Health | null;
  suggestions: string[];
}

export function Ask({ health, suggestions }: Props) {
  const [params, setParams] = useSearchParams();

  /** Bumped to re-run a question the URL already holds. */
  const [attempt, setAttempt] = useState(0);

  /** The question lives in the URL, so a run is shareable and survives a reload. */
  const asked = params.get("q") ?? "";
  const run = useAgentStream(asked, attempt);

  const ask = useCallback(
    (question: string) => {
      // Asking what the URL already says would not change anything to react
      // to, so a repeat -- a retry after a rate limit, most often -- goes
      // through the nonce instead.
      if (question === asked) {
        setAttempt((count) => count + 1);
      } else {
        setParams({ q: question });
      }

      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [asked, setParams],
  );

  const retry = useCallback(() => setAttempt((count) => count + 1), []);

  const clear = useCallback(() => setParams({}), [setParams]);

  const missingKey = health !== null && !health.groq_configured;
  const idle = run.status === "idle";

  return (
    <div className="shell ask-page">
      {missingKey && (
        <div className="notice" style={{ marginBottom: "1.5rem" }}>
          <span>&#9888;</span>
          <span>
            No <code>GROQ_API_KEY</code> is configured, so the assistant cannot answer
            yet. Add it to <code>.env</code> in the project root and restart the backend.
            Player search and statistics still work without it.
          </span>
        </div>
      )}

      {idle ? (
        <>
          <header className="ask-page__head">
            <h1>Ask about a player</h1>
            <p>
              Name any of the {health?.players ?? 397} players with 450 or more minutes in
              the 2024/25 season. The assistant will show each step as it works.
            </p>
          </header>

          <AskBar onAsk={ask} autoFocus />

          <p className="ask__hint">
            Start typing a player&rsquo;s name for suggestions, or pick a question below.
          </p>

          <div className="chips">
            {suggestions.map((question) => (
              <button
                key={question}
                type="button"
                className="chip"
                onClick={() => ask(question)}
              >
                {question}
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="run">
          <div className="run__question">
            <h1>{run.question}</h1>
            <button className="button button--ghost button--sm" type="button" onClick={clear}>
              New question
            </button>
          </div>

          <AgentTrace steps={run.steps} active={run.active} status={run.status} />

          {run.error && (
            <div className="notice notice--error">
              <span>&#9888;</span>
              <span>{run.error}</span>
              <button
                className="button button--ghost button--sm"
                type="button"
                onClick={retry}
              >
                Try again
              </button>
            </div>
          )}

          {run.answer && <AnswerView answer={run.answer} onAskFollowUp={ask} />}

          {run.status !== "running" && (
            <EvidenceBasePanel
              evidence={run.evidence}
              namedInAnswer={
                run.answer?.similar_players.map((item) => item.player) ?? []
              }
            />
          )}

          {run.status !== "running" && (
            <AskBar onAsk={ask} placeholder="Ask a follow-up…" />
          )}
        </div>
      )}
    </div>
  );
}
