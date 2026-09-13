import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { AgentTrace } from "../components/AgentTrace";
import { AnakinResearchPanel } from "../components/AnakinResearchPanel";
import { AnswerView } from "../components/AnswerView";
import { AskBar } from "../components/AskBar";
import { CacheStatus } from "../components/CacheStatus";
import { ComparisonWorkspace } from "../components/ComparisonWorkspace";
import { EvidenceBasePanel } from "../components/EvidenceBase";
import { ResearchSquad } from "../components/ResearchSquad";
import { SavedRuns } from "../components/SavedRuns";
import { ScoutBriefActions } from "../components/ScoutBriefActions";
import { useAgentStream } from "../hooks/useAgentStream";
import { useSavedRuns } from "../hooks/useSavedRuns";
import type { AgenticResearchReport, Health, SavedResearchRun } from "../types";

interface Props {
  health: Health | null;
  suggestions: string[];
}

export function Ask({ health, suggestions }: Props) {
  const [params, setParams] = useSearchParams();

  /** Bumped to re-run a question the URL already holds. */
  const [attempt, setAttempt] = useState(0);
  const [restoredRun, setRestoredRun] = useState<SavedResearchRun | null>(null);
  const [webRefreshAttemptedId, setWebRefreshAttemptedId] = useState<string | null>(null);
  const [webRefreshState, setWebRefreshState] = useState<
    "idle" | "refreshing" | "ready" | "error"
  >("idle");
  const [webRetryAfter, setWebRetryAfter] = useState<number | null>(null);
  const [researchStartedId, setResearchStartedId] = useState<string | null>(null);
  const [researchStatus, setResearchStatus] = useState<
    "idle" | "pending" | "processing" | "completed" | "failed"
  >("idle");
  const { runs: savedRuns, save, remove, lastSavedId } = useSavedRuns();

  /** The question lives in the URL, so a run is shareable and survives a reload. */
  const asked = params.get("q") ?? "";
  const normalizedAsked = asked.trim().toLocaleLowerCase();
  const cachedRun =
    savedRuns.find((saved) => saved.id === normalizedAsked) ?? null;
  const usingCache = Boolean(cachedRun) && attempt === 0 && !restoredRun;
  const liveRun = useAgentStream(asked, attempt, !usingCache);
  const run = restoredRun
    ? {
        status: "done" as const,
        question: restoredRun.question,
        steps: restoredRun.steps,
        evidence: restoredRun.evidence,
        answer: restoredRun.answer,
        error: null,
        active: null,
      }
    : cachedRun
      ? {
          status: "done" as const,
          question: cachedRun.question,
          steps: cachedRun.steps,
          evidence: cachedRun.evidence,
          answer: cachedRun.answer,
          error: null,
          active: null,
        }
      : liveRun;
  const showingCache = Boolean(restoredRun || (cachedRun && attempt === 0));
  const replayedRun = restoredRun ?? (cachedRun && attempt === 0 ? cachedRun : null);
  const webRefreshRequired = Boolean(
    replayedRun?.webRefreshRequired ??
      replayedRun?.evidence.anakinRefreshRequired ??
      replayedRun?.steps.some(
        (step) => step.tool === "search_football_web" && step.status === "failed",
      ),
  );
  const justSaved =
    liveRun.status === "done" &&
    liveRun.question.length > 0 &&
    lastSavedId === liveRun.question.trim().toLocaleLowerCase();

  const completeResearch = useCallback(
    (report: AgenticResearchReport) => {
      if (!run.answer || !run.question) return;

      const id = run.question.trim().toLocaleLowerCase();
      const saved = savedRuns.find((item) => item.id === id);
      const base: SavedResearchRun = saved ?? {
        id,
        question: run.question,
        answer: run.answer,
        evidence: run.evidence,
        steps: run.steps,
        savedAt: Date.now(),
      };
      const sources = [
        ...base.answer.sources,
        ...report.citations.filter(
          (source) => !base.answer.sources.some((item) => item.url === source.url),
        ),
      ];

      save({
        ...base,
        answer: {
          ...base.answer,
          sources,
          tactical_evidence: report.summary
            ? [...base.answer.tactical_evidence, `Anakin research: ${report.summary}`]
            : base.answer.tactical_evidence,
        },
        evidence: { ...base.evidence, agenticResearch: report },
        savedAt: Date.now(),
      });
      setResearchStatus("completed");
    },
    [run.answer, run.evidence, run.question, run.steps, save, savedRuns],
  );

  const researchEnabled = Boolean(
    (health?.web_search_configured ?? true) && liveRun.status === "done" && run.answer && run.question,
  );
  const effectiveResearchStatus = run.evidence.agenticResearch
    ? "completed"
    : researchStatus;

  useEffect(() => {
    if (liveRun.status !== "done" || !liveRun.answer || !liveRun.question) {
      return;
    }

    save({
      id: liveRun.question.trim().toLocaleLowerCase(),
      question: liveRun.question,
      answer: liveRun.answer,
      evidence: liveRun.evidence,
      steps: liveRun.steps,
      savedAt: Date.now(),
      webRefreshRequired: liveRun.steps.some(
        (step) => step.tool === "search_football_web" && step.status === "failed",
      ) || Boolean(liveRun.evidence.anakinRefreshRequired),
    });
  }, [liveRun.status, liveRun.question, liveRun.answer, liveRun.evidence, liveRun.steps, save]);

  const refreshAnakin = useCallback(() => {
    if (!replayedRun) {
      return;
    }

    setWebRefreshState("refreshing");
    setWebRetryAfter(null);

    api
      .refreshWeb(replayedRun.question)
      .then((response) => {
        const refreshedSteps = replayedRun.steps.map((step) =>
          step.tool === "search_football_web" && step.status === "failed"
            ? {
                ...step,
                status: "ok" as const,
                detail: "Anakin evidence refreshed without rerunning the ML lanes.",
              }
            : step,
        );

        const refreshedRun: SavedResearchRun = {
          ...replayedRun,
          answer: {
            ...replayedRun.answer,
            sources: [
              ...replayedRun.answer.sources,
              ...response.results
                .filter(
                  (source) =>
                    !replayedRun.answer.sources.some((item) => item.url === source.url),
                )
                .map(({ title, url }) => ({ title, url })),
            ],
          },
          evidence: {
            ...replayedRun.evidence,
            webSources: response.results,
            toolCalls: replayedRun.evidence.toolCalls + 1,
            anakinRefreshRequired: false,
          },
          steps: refreshedSteps,
          savedAt: Date.now(),
          webRefreshRequired: false,
        };

        save(refreshedRun);
        setRestoredRun((current) => (current ? refreshedRun : current));
        setWebRefreshState("ready");
      })
      .catch((error: Error & { retryAfter?: string | null }) => {
        setWebRetryAfter(error.retryAfter ? Number(error.retryAfter) : null);
        setWebRefreshState("error");
      });
  }, [replayedRun, save]);

  useEffect(() => {
    if (!replayedRun || !webRefreshRequired || webRefreshAttemptedId === replayedRun.id) {
      return;
    }

    setWebRefreshAttemptedId(replayedRun.id);
    refreshAnakin();
  }, [replayedRun, webRefreshRequired, webRefreshAttemptedId, refreshAnakin]);

  const ask = useCallback(
    (question: string) => {
      setRestoredRun(null);
      const normalized = question.trim().toLocaleLowerCase();
      const saved = savedRuns.find((run) => run.id === normalized);

      if (saved) {
        setWebRefreshAttemptedId(null);
        setWebRefreshState("idle");
        setWebRetryAfter(null);
        setResearchStartedId(null);
        setResearchStatus(saved.evidence.agenticResearch ? "completed" : "idle");
        setAttempt(0);
        setParams({ q: question });
      } else if (question === asked) {
        // No cached result exists, so repeating the current question is a
        // deliberate fresh run rather than an accidental duplicate request.
        setAttempt((count) => count + 1);
      } else {
        setWebRefreshAttemptedId(null);
        setWebRefreshState("idle");
        setWebRetryAfter(null);
        setResearchStartedId(null);
        setResearchStatus("idle");
        setAttempt(0);
        setParams({ q: question });
      }

      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [asked, savedRuns, setParams],
  );

  const retry = useCallback(() => {
    setRestoredRun(null);
    setWebRefreshAttemptedId(null);
    setWebRefreshState("idle");
    setWebRetryAfter(null);
    setResearchStartedId(null);
    setResearchStatus("idle");
    setAttempt((count) => count + 1);
  }, []);

  const clear = useCallback(() => {
    setRestoredRun(null);
    setWebRefreshAttemptedId(null);
    setWebRefreshState("idle");
    setWebRetryAfter(null);
    setResearchStartedId(null);
    setResearchStatus("idle");
    setParams({});
  }, [setParams]);

  const openSaved = useCallback(
    (saved: SavedResearchRun) => {
      setRestoredRun(saved);
      setWebRefreshAttemptedId(null);
      setWebRefreshState("idle");
      setWebRetryAfter(null);
      setResearchStartedId(null);
      setResearchStatus(saved.evidence.agenticResearch ? "completed" : "idle");
      setParams({});
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [setParams],
  );

  const missingKey = health !== null && !health.groq_configured;
  const idle = run.status === "idle";
  const cacheState = showingCache
    ? webRefreshState === "refreshing"
      ? "refreshing"
      : webRefreshState === "error"
        ? "partial"
        : webRefreshState === "ready"
          ? "ready"
          : "hit"
    : justSaved
      ? "ready"
      : "saving";

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
            <span className="section__eyebrow">ScoutLab workspace</span>
            <h1>Build a player research brief</h1>
            <p>
              Not a chatbot wrapper. Your question is routed through an ML scout, a stats
              auditor, an Anakin web scout and a report editor.
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

          <ResearchSquad steps={[]} active={null} status="idle" />

           <SavedRuns runs={savedRuns} onOpen={openSaved} onRemove={remove} />
        </>
      ) : (
        <div className="run">
          <div className="run__question">
            <h1>{run.question}</h1>
            <button className="button button--ghost button--sm" type="button" onClick={clear}>
              New question
            </button>
          </div>

          {(showingCache || liveRun.status === "running" || justSaved) && (
            <CacheStatus
              state={cacheState}
              onRetry={
                webRefreshState === "error" && webRefreshRequired ? refreshAnakin : undefined
              }
              retryAfter={webRetryAfter}
            />
          )}

          <ResearchSquad
            steps={run.steps}
            active={run.active}
            status={run.status}
            cached={showingCache}
            webRefreshing={webRefreshState === "refreshing"}
            researchStatus={effectiveResearchStatus}
          />

          <AgentTrace steps={run.steps} active={run.active} status={run.status} />

          <AnakinResearchPanel
            key={`${run.question}-${attempt}`}
            question={run.question}
            enabled={researchEnabled && researchStartedId !== `${run.question}-${attempt}`}
            initialReport={run.evidence.agenticResearch}
            onStatusChange={setResearchStatus}
            onComplete={(report) => {
              setResearchStartedId(`${run.question}-${attempt}`);
              completeResearch(report);
            }}
          />

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

          {run.answer && (
            <ScoutBriefActions question={run.question} answer={run.answer} evidence={run.evidence} />
          )}

          <ComparisonWorkspace key={run.question} evidence={run.evidence} />

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
