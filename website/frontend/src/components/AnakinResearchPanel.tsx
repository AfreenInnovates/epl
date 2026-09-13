import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { AgenticResearchReport } from "../types";

type Status = "idle" | "pending" | "processing" | "completed" | "failed";

interface Props {
  question: string;
  enabled: boolean;
  initialReport?: AgenticResearchReport;
  onComplete: (report: AgenticResearchReport) => void;
  onStatusChange?: (status: Status) => void;
}

export function AnakinResearchPanel({
  question,
  enabled,
  initialReport,
  onComplete,
  onStatusChange,
}: Props) {
  const [status, setStatus] = useState<Status>(initialReport ? "completed" : "idle");
  const [report, setReport] = useState<AgenticResearchReport | undefined>(initialReport);
  const [error, setError] = useState<string | null>(null);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  function updateStatus(next: Status) {
    setStatus(next);
    onStatusChange?.(next);
  }

  useEffect(() => {
    if (!enabled || initialReport || !question) return;

    let cancelled = false;
    let timer: number | undefined;

    async function poll(jobId: string) {
      try {
        const result = await api.getAnakinResearch(jobId);
        if (cancelled) return;

        updateStatus(result.status as Status);

        if (result.status === "completed" && result.report) {
          setReport(result.report);
          onCompleteRef.current(result.report);
          return;
        }

        if (result.status === "failed") {
          setError(result.error ?? "Anakin research failed.");
          return;
        }

        timer = window.setTimeout(() => poll(jobId), 10_000);
      } catch (pollError) {
        if (!cancelled) {
          updateStatus("failed");
          setError(pollError instanceof Error ? pollError.message : "Polling failed.");
        }
      }
    }

    updateStatus("pending");
    api
      .submitAnakinResearch(question)
      .then((result) => {
        if (!cancelled) {
          updateStatus(result.status as Status);
          void poll(result.job_id);
        }
      })
      .catch((submitError) => {
        if (!cancelled) {
          updateStatus("failed");
          setError(
            submitError instanceof Error ? submitError.message : "Could not start research.",
          );
        }
      });

    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [enabled, initialReport, onStatusChange, question]);

  if (!enabled && !initialReport) return null;

  return (
    <section className="anakin-research" aria-live="polite">
      <div className="anakin-research__head">
        <div>
          <span className="section__eyebrow">Anakin Agentic Search</span>
          <h2>Four-stage external research</h2>
        </div>
        <span className="anakin-research__status" data-status={status}>
          {status === "completed"
            ? "complete"
            : status === "failed"
              ? "unavailable"
              : status === "idle"
                ? "queued"
                : "researching"}
        </span>
      </div>

      <p className="anakin-research__lede">
        Anakin refines the query, searches, scrapes citations, and synthesises a second research
        view. It runs asynchronously so the local ML brief is available first.
      </p>

      {status !== "completed" && status !== "failed" && (
        <div className="anakin-research__progress"><span /></div>
      )}

      {error && <p className="anakin-research__error">{error}</p>}
      {report?.summary && <p className="anakin-research__summary">{report.summary}</p>}

      {report && report.citations.length > 0 && (
        <div className="anakin-research__sources">
          {report.citations.slice(0, 5).map((source) => (
            <a href={source.url} key={source.url} target="_blank" rel="noreferrer noopener">
              {source.title}
            </a>
          ))}
        </div>
      )}
    </section>
  );
}
