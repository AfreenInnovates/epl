import type { SavedResearchRun } from "../types";

interface Props {
  runs: SavedResearchRun[];
  onOpen: (run: SavedResearchRun) => void;
  onRemove: (id: string) => void;
}

export function SavedRuns({ runs, onOpen, onRemove }: Props) {
  if (runs.length === 0) {
    return null;
  }

  return (
    <section className="saved-runs" aria-label="Saved research">
      <div className="saved-runs__head">
        <div>
          <span className="section__eyebrow">In this browser</span>
          <h2>Saved research</h2>
        </div>
        <span>{runs.length} saved</span>
      </div>

      <div className="saved-runs__list">
        {runs.map((run) => (
          <article className="saved-run" key={run.id}>
            <button className="saved-run__open" type="button" onClick={() => onOpen(run)}>
              <strong>{run.answer.title}</strong>
              <span>{run.question}</span>
              <small>
                 {new Date(run.savedAt).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                 })}
                 {" · "}
                 {run.evidence.toolCalls} tool calls
                 {(
                   run.webRefreshRequired ??
                   run.steps.some(
                     (step) => step.tool === "search_football_web" && step.status === "failed",
                   )
                 )
                   ? " · Anakin pending"
                   : " · Anakin ready"}
               </small>
            </button>
            <button
              className="saved-run__remove"
              type="button"
              aria-label={`Remove ${run.answer.title}`}
              onClick={() => onRemove(run.id)}
            >
              ×
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
