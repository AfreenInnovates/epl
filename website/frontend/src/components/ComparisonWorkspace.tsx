import { useEffect, useState } from "react";

import type { EvidenceBase, MlCandidate } from "../types";

interface Props {
  evidence: EvidenceBase;
}

const MAX_SELECTED = 4;

function agreementLabel(candidate: MlCandidate): string {
  if (candidate.models_retrieved === 3) return "strong consensus";
  if (candidate.models_retrieved === 2) return "two-model signal";
  return "single-model signal";
}

export function ComparisonWorkspace({ evidence }: Props) {
  const { candidates } = evidence;
  const [selected, setSelected] = useState<string[]>(
    candidates.slice(0, MAX_SELECTED).map((candidate) => candidate.player),
  );

  useEffect(() => {
    setSelected(candidates.slice(0, MAX_SELECTED).map((candidate) => candidate.player));
  }, [candidates]);

  if (candidates.length === 0) {
    return null;
  }

  const chosen = candidates.filter((candidate) => selected.includes(candidate.player));

  function toggle(player: string) {
    setSelected((current) => {
      if (current.includes(player)) {
        return current.filter((name) => name !== player);
      }

      if (current.length >= MAX_SELECTED) {
        return current;
      }

      return [...current, player];
    });
  }

  return (
    <section className="comparison-workspace" aria-label="Player comparison workspace">
      <div className="comparison-workspace__head">
        <div>
          <span className="section__eyebrow">Decision workspace</span>
          <h2>Compare the shortlist</h2>
        </div>
        <span className="comparison-workspace__count">
          {chosen.length}/{MAX_SELECTED} selected
        </span>
      </div>

      <p className="comparison-workspace__lede">
        Turn the model output into a decision. Select up to four candidates and compare the
        agreement signal rather than treating one similarity score as a verdict.
      </p>

      <div className="comparison-picker" role="group" aria-label="Choose players to compare">
        {candidates.map((candidate) => (
          <button
            className="comparison-picker__item"
            data-selected={selected.includes(candidate.player)}
            key={candidate.player}
            type="button"
            onClick={() => toggle(candidate.player)}
          >
            <span>{candidate.player}</span>
            <small>{candidate.models_retrieved}/3 models</small>
          </button>
        ))}
      </div>

      <div className="comparison-grid">
        {chosen.map((candidate) => {
          const agreement = (candidate.models_retrieved / 3) * 100;

          return (
            <article className="comparison-card" key={candidate.player}>
              <div className="comparison-card__rank">
                #{candidates.findIndex((item) => item.player === candidate.player) + 1}
              </div>
              <h3>{candidate.player}</h3>
              <p>
                {candidate.club ?? "Club unavailable"}
                {candidate.position ? ` · ${candidate.position}` : ""}
              </p>

              <div className="comparison-card__metric">
                <div>
                  <span>Model agreement</span>
                  <strong>{agreementLabel(candidate)}</strong>
                </div>
                <b>{candidate.models_retrieved}/3</b>
              </div>
              <div className="agreement-bar" aria-label={`${candidate.models_retrieved} of 3 models agreed`}>
                <span style={{ width: `${agreement}%` }} />
              </div>

              <dl className="comparison-card__facts">
                <div>
                  <dt>Mean similarity</dt>
                  <dd>{candidate.mean_similarity.toFixed(2)}</dd>
                </div>
                <div>
                  <dt>Interpretation</dt>
                  <dd>{candidate.models_retrieved === 3 ? "Robust" : "Review context"}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>
    </section>
  );
}
