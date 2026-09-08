import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { Answer, PlayerSummary } from "../types";

interface Props {
  answer: Answer;
  onAskFollowUp: (question: string) => void;
}

function EvidencePanel({
  title,
  items,
  variant,
}: {
  title: string;
  items: string[];
  variant?: "tactical" | "limits";
}) {
  if (items.length === 0) {
    return null;
  }

  const className = ["panel", variant ? `panel--${variant}` : ""].join(" ").trim();

  return (
    <section className={className}>
      <h3 className="panel__title">
        {title}
        <span className="panel__count">{items.length}</span>
      </h3>

      <ul className="evidence">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

/**
 * The model names the comparable players; we attach club and position from the
 * dataset so the reader can place each name without leaving the page. Cards are
 * clickable, which turns a list of names into the obvious next question.
 */
function SimilarPlayers({
  answer,
  onAskFollowUp,
}: {
  answer: Answer;
  onAskFollowUp: (question: string) => void;
}) {
  const [profiles, setProfiles] = useState<Record<string, PlayerSummary>>({});

  const names = answer.similar_players.map((item) => item.player).join("|");

  useEffect(() => {
    if (!names) {
      return;
    }

    let cancelled = false;

    Promise.all(
      names
        .split("|")
        .slice(0, 8)
        .map((name) =>
          api
            .players(name)
            .then((results) => results.find((player) => player.name === name) ?? null)
            .catch(() => null),
        ),
    ).then((results) => {
      if (cancelled) {
        return;
      }

      const next: Record<string, PlayerSummary> = {};

      for (const player of results) {
        if (player) {
          next[player.name] = player;
        }
      }

      setProfiles(next);
    });

    return () => {
      cancelled = true;
    };
  }, [names]);

  if (answer.similar_players.length === 0) {
    return null;
  }

  return (
    <section className="panel">
      <h3 className="panel__title">
        Comparable players
        <span className="panel__count">{answer.similar_players.length}</span>
      </h3>

      <div className="player-grid">
        {answer.similar_players.map((item) => {
          const profile = profiles[item.player];

          return (
            <button
              key={item.player}
              type="button"
              className="player-card"
              onClick={() => onAskFollowUp(`Who plays like ${item.player}, and why?`)}
              title={`Ask about ${item.player}`}
            >
              <div className="player-card__name">{item.player}</div>
              <p className="player-card__reason">{item.reason}</p>

              {profile && (
                <div className="player-card__meta">
                  {profile.club && <span className="badge">{profile.club}</span>}
                  {profile.position_label && (
                    <span className="badge badge--strong">{profile.position_label}</span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}

export function AnswerView({ answer, onAskFollowUp }: Props) {
  return (
    <div className="answer">
      <header className="answer__head">
        <h2>{answer.title}</h2>
        <p>{answer.summary}</p>
      </header>

      <SimilarPlayers answer={answer} onAskFollowUp={onAskFollowUp} />

      <EvidencePanel title="Statistical evidence" items={answer.statistical_evidence} />

      <EvidencePanel
        title="Tactical evidence"
        items={answer.tactical_evidence}
        variant="tactical"
      />

      <EvidencePanel
        title="What this does not prove"
        items={answer.limitations}
        variant="limits"
      />

      {answer.sources.length > 0 && (
        <section className="panel">
          <h3 className="panel__title">
            Sources
            <span className="panel__count">{answer.sources.length}</span>
          </h3>

          <div className="sources">
            {answer.sources.map((source) => (
              <a
                key={source.url}
                className="source"
                href={source.url}
                target="_blank"
                rel="noreferrer noopener"
              >
                <strong>{source.title}</strong>
                <span>{source.url}</span>
              </a>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
