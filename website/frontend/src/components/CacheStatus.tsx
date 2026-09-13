interface Props {
  state: "hit" | "saving" | "ready" | "refreshing" | "partial";
  onRetry?: () => void;
  retryAfter?: number | null;
}

const COPY = {
  hit: {
    label: "Local cache hit",
    title: "Restoring this research dossier",
    detail: "The same question was found in this browser. No agent run was started.",
    badge: "localStorage",
  },
  saving: {
    label: "Writing locally",
    title: "Saving the evidence trail",
    detail: "This completed dossier will be available instantly next time.",
    badge: "browser cache",
  },
  ready: {
    label: "Ready for replay",
    title: "Research saved to this browser",
    detail: "Ask the same question again to replay this dossier without a new run.",
    badge: "cached",
  },
  refreshing: {
    label: "Anakin refresh in flight",
    title: "Checking the missing web lane",
    detail: "The cached ML and stats evidence stays on screen while Anakin is retried.",
    badge: "web refresh",
  },
  partial: {
    label: "Partial dossier retained",
    title: "Anakin is still unavailable",
    detail: "The answer is cached locally. Retry the web lane when the provider is back.",
    badge: "retry available",
  },
} as const;

export function CacheStatus({ state, onRetry, retryAfter }: Props) {
  const copy = COPY[state];
  const detail =
    state === "partial" && retryAfter
      ? `Anakin rate-limited this refresh. Retry in about ${retryAfter} seconds.`
      : copy.detail;

  return (
    <aside className="cache-status" data-state={state} aria-live="polite">
      <div className="cache-status__visual" aria-hidden="true">
        <span className="cache-status__orbit" />
        <span className="cache-status__core">{state === "ready" ? "✓" : ""}</span>
        <span className="cache-status__scan" />
      </div>
      <div className="cache-status__copy">
        <div className="cache-status__label">
          <span>{copy.label}</span>
          <code>{copy.badge}</code>
        </div>
        <strong>{copy.title}</strong>
        <p>{detail}</p>
        {state === "partial" && onRetry && (
          <button className="cache-status__retry" type="button" onClick={onRetry}>
            Retry Anakin
          </button>
        )}
      </div>
    </aside>
  );
}
