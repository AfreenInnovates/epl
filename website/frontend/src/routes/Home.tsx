import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Crest, PlayerAvatar } from "../components/Media";
import {
  CLUBS,
  CLUB_TABLE,
  FEATURES,
  HERO_SLIDES,
  MATCHUPS,
  PROMPTS,
  TOP_CREATORS,
  TOP_SCORERS,
  clubShort,
} from "../data/showcase";
import type { Health } from "../types";

interface Props {
  health: Health | null;
  suggestions: string[];
}

const TOOLS = [
  {
    title: "Similarity search",
    body: "Three representations of every player — the scaled season features, a Siamese network and a triplet network. Candidates are ranked by how many of the three independently surfaced them.",
    tool: "ml_player_search",
  },
  {
    title: "Season statistics",
    body: "Per-90 rates read straight from the 2024/25 table. The assistant looks numbers up rather than recalling them, and says a player is missing rather than guessing.",
    tool: "player_stats_tool",
  },
  {
    title: "Tactical context",
    body: "Matching numbers do not mean a matching role. Web results supply the qualitative half — what a player actually does on the pitch — kept separate from the statistics.",
    tool: "search_football_web",
  },
];

const STEPS = [
  {
    title: "You ask",
    body: "A question about a player, in plain language. The assistant reads it and decides what evidence it needs.",
  },
  {
    title: "It searches the embeddings",
    body: "Three representations return their nearest neighbours. Candidates several models agree on rank above ones only a single model liked.",
  },
  {
    title: "It reads the numbers",
    body: "Per-90 rates for the players involved, pulled from the dataset. Every figure in the answer traces back to this step.",
  },
  {
    title: "It explains itself",
    body: "A structured answer separating what the statistics show from what they cannot, with the full candidate shortlist shown alongside.",
  },
];

const REPRESENTATIONS = [
  {
    name: "standard",
    dims: 41,
    what: "Scaled season features, no learning",
    consistency: "0.694",
    spread: "0.169",
    verdict: "Ranks best; no learned notion of style",
  },
  {
    name: "siamese",
    dims: 16,
    what: "Hard-pair contrastive encoder",
    consistency: "0.514",
    spread: "0.049",
    verdict: "Middling on both measures",
  },
  {
    name: "triplet",
    dims: 8,
    what: "Triplet-margin encoder",
    consistency: "0.861",
    spread: "0.002",
    verdict: "Learned position, not style",
  },
];

const ASK_PATH = (question: string) => `/ask?q=${encodeURIComponent(question)}`;

/** Nudges a horizontal rail by roughly one card. */
function useRail() {
  const ref = useRef<HTMLDivElement>(null);

  const scrollBy = (direction: 1 | -1) => {
    const rail = ref.current;

    if (rail) {
      rail.scrollBy({ left: direction * rail.clientWidth * 0.8, behavior: "smooth" });
    }
  };

  return { ref, scrollBy };
}

function Hero() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) {
      return;
    }

    const timer = window.setInterval(
      () => setIndex((current) => (current + 1) % HERO_SLIDES.length),
      7000,
    );

    return () => window.clearInterval(timer);
  }, [paused]);

  const slide = HERO_SLIDES[index];
  const [firstLine, secondLine] = slide.title.split("\n");

  return (
    <section
      className="hero"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="hero__art" role="presentation" />

      <div className="shell hero__inner">
        <div className="hero__copy" key={index}>
          <span className="hero__eyebrow">{slide.eyebrow}</span>

          <h1>
            {firstLine}
            {secondLine && (
              <>
                <br />
                {secondLine}
              </>
            )}
          </h1>

          <p className="hero__lede">{slide.lede}</p>

          <div className="hero__actions">
            <Link className="button button--primary" to="/ask">
              Ask a question
            </Link>
            <a className="button button--ghost" href="#clubs">
              Explore clubs
            </a>
          </div>
        </div>

        <div className="hero__dots">
          {HERO_SLIDES.map((item, dot) => (
            <button
              key={item.title}
              type="button"
              className="hero__dot"
              data-active={dot === index}
              aria-label={`Slide ${dot + 1}: ${item.eyebrow}`}
              aria-current={dot === index}
              onClick={() => setIndex(dot)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function Matchups() {
  const rail = useRail();

  return (
    <section className="section section--rail">
      <div className="shell">
        <div className="rail__head">
          <h2 className="rail__title">Featured comparisons</h2>
          <Link className="rail__more" to="/ask">
            Ask your own <span aria-hidden="true">&rarr;</span>
          </Link>
        </div>
      </div>

      <div className="rail">
        <div className="shell rail__viewport" ref={rail.ref}>
          {MATCHUPS.map((matchup) => (
            <Link
              className="fixture"
              key={matchup.question}
              to={ASK_PATH(matchup.question)}
            >
              <span className="fixture__tag">{matchup.tag}</span>

              <div className="fixture__body">
                <span className="fixture__side">
                  <PlayerAvatar
                    opta={matchup.left.opta}
                    club={matchup.left.club}
                    name={matchup.left.player}
                  />
                  <strong>{matchup.left.player}</strong>
                  <span>{clubShort(matchup.left.club)}</span>
                </span>

                <span className="fixture__vs">vs</span>

                <span className="fixture__side">
                  <PlayerAvatar
                    opta={matchup.right.opta}
                    club={matchup.right.club}
                    name={matchup.right.player}
                  />
                  <strong>{matchup.right.player}</strong>
                  <span>{clubShort(matchup.right.club)}</span>
                </span>
              </div>

              <span className="fixture__cta">Compare</span>
            </Link>
          ))}
        </div>

        <button
          className="rail__arrow"
          type="button"
          aria-label="Scroll comparisons"
          onClick={() => rail.scrollBy(1)}
        >
          <span aria-hidden="true">&rarr;</span>
        </button>
      </div>
    </section>
  );
}

function ClubTable() {
  const [expanded, setExpanded] = useState(false);
  const rows = expanded ? CLUB_TABLE : CLUB_TABLE.slice(0, 6);

  return (
    <div className="panel-card">
      <div className="panel-card__head">
        <h2>Squad output</h2>
        <button
          className="panel-card__more"
          type="button"
          onClick={() => setExpanded((open) => !open)}
        >
          {expanded ? "Show top six" : "Show all 20"}{" "}
          <span aria-hidden="true">&rarr;</span>
        </button>
      </div>

      <table className="league">
        <thead>
          <tr>
            <th>#</th>
            <th>Club</th>
            <th className="num">Sq</th>
            <th className="num">G</th>
            <th className="num">A</th>
            <th className="num">G+A</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, position) => (
            <tr key={row.club}>
              <td className="league__pos">{position + 1}</td>
              <td>
                <span className="league__club">
                  <Crest club={row.club} size={25} />
                  {clubShort(row.club)}
                </span>
              </td>
              <td className="num">{row.squad}</td>
              <td className="num">{row.goals}</td>
              <td className="num">{row.assists}</td>
              <td className="num league__strong">{row.goals + row.assists}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="panel-card__note">
        Ranked by goals scored by the players in the dataset. These are not league
        positions — the dataset holds no results, so there are no points to show.
      </p>
    </div>
  );
}

function Leaderboard() {
  const [metric, setMetric] = useState<"goals" | "assists">("goals");
  const leaders = metric === "goals" ? TOP_SCORERS : TOP_CREATORS;

  return (
    <div className="panel-card">
      <div className="panel-card__head">
        <h2>{metric === "goals" ? "Top scorers" : "Top creators"}</h2>

        <div className="toggle" role="tablist" aria-label="Leaderboard metric">
          <button
            type="button"
            role="tab"
            aria-selected={metric === "goals"}
            data-active={metric === "goals"}
            onClick={() => setMetric("goals")}
          >
            Goals
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={metric === "assists"}
            data-active={metric === "assists"}
            onClick={() => setMetric("assists")}
          >
            Assists
          </button>
        </div>
      </div>

      <ol className="leaders">
        {leaders.slice(0, 6).map((leader, position) => (
          <li key={leader.player + metric}>
            <span className="leaders__pos">{position + 1}</span>

            <PlayerAvatar opta={leader.opta} club={leader.club} name={leader.player} />

            <span className="leaders__name">
              <strong>{leader.player}</strong>
              <span>{clubShort(leader.club)}</span>
            </span>

            <span className="leaders__value">
              <strong>{leader.value}</strong>
              <span>{leader.per90.toFixed(2)} per 90</span>
            </span>
          </li>
        ))}
      </ol>

      <p className="panel-card__note">
        Season totals with the per-90 rate beside them — the rate is what the
        assistant compares players on.
      </p>
    </div>
  );
}

export function Home({ health, suggestions }: Props) {
  const players = health?.players ?? 397;

  return (
    <>
      <Hero />

      <section className="section section--strip">
        <div className="shell">
          <div className="stats">
            <div>
              <strong>{players}</strong>
              <span>players with 450+ minutes</span>
            </div>
            <div>
              <strong>20</strong>
              <span>clubs, 2024/25 season</span>
            </div>
            <div>
              <strong>{health?.models.length ?? 3}</strong>
              <span>independent representations</span>
            </div>
            <div>
              <strong>3</strong>
              <span>tools the assistant can call</span>
            </div>
          </div>
        </div>
      </section>

      <Matchups />

      <section className="section section--tight">
        <div className="shell split">
          <ClubTable />
          <Leaderboard />
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="rail__head">
            <h2 className="rail__title">From the research log</h2>
            <a className="rail__more" href="#how-it-works">
              Read the method <span aria-hidden="true">&rarr;</span>
            </a>
          </div>

          <div className="features">
            {FEATURES.map((feature) => (
              <a className="feature" key={feature.href} href={feature.href}>
                <span className="feature__media">
                  <img src={feature.image} alt="" loading="lazy" />
                </span>
                <span className="feature__kicker">{feature.kicker}</span>
                <span className="feature__title">{feature.title}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="section section--tight" id="clubs">
        <div className="shell split split--wide">
          <div className="panel-card">
            <div className="panel-card__head">
              <h2>Start with a question</h2>
              <Link className="panel-card__more" to="/ask">
                Open the assistant <span aria-hidden="true">&rarr;</span>
              </Link>
            </div>

            <div className="prompts">
              {PROMPTS.map((prompt) => (
                <Link
                  className="prompt"
                  key={prompt.question}
                  to={ASK_PATH(prompt.question)}
                >
                  <PlayerAvatar
                    opta={prompt.opta}
                    club={prompt.club}
                    name={prompt.question}
                  />
                  <span className="prompt__body">
                    <strong>{prompt.question}</strong>
                    <span>{prompt.label}</span>
                  </span>
                </Link>
              ))}
            </div>
          </div>

          <div className="panel-card">
            <div className="panel-card__head">
              <h2>Explore clubs</h2>
              <Link className="panel-card__more" to="/ask">
                Ask about a squad <span aria-hidden="true">&rarr;</span>
              </Link>
            </div>

            <div className="clubs">
              {CLUBS.map((club) => (
                <Link
                  className="club"
                  key={club.name}
                  to={ASK_PATH(`Which ${club.short} players stand out statistically?`)}
                >
                  <Crest club={club.name} size={70} />
                  <span>{club.short}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section section--tint" id="how-it-works">
        <div className="shell">
          <div className="section__head">
            <span className="section__eyebrow">How it works</span>
            <h2 className="section__title">Four steps, all of them visible</h2>
            <p className="section__lede">
              Nothing happens behind a spinner. While the assistant works, the interface
              names the tool it is running; between calls it says it is thinking, because
              that is all that can honestly be reported.
            </p>
          </div>

          <div className="steps">
            {STEPS.map((step) => (
              <article className="step-card" key={step.title}>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section__head">
            <span className="section__eyebrow">Capabilities</span>
            <h2 className="section__title">Three tools, one question at a time</h2>
            <p className="section__lede">
              The assistant decides which to call and in what order. Two read your own
              data in milliseconds; the third goes to the open web.
            </p>
          </div>

          <div className="grid grid--3">
            {TOOLS.map((tool) => (
              <article className="card" key={tool.tool}>
                <h3>{tool.title}</h3>
                <p>{tool.body}</p>
                <code className="card__tool">{tool.tool}</code>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section section--tint" id="per-90">
        <div className="shell">
          <div className="section__head">
            <span className="section__eyebrow">Reading the output</span>
            <h2 className="section__title">What "per 90" means</h2>
            <p className="section__lede">
              Per 90 minutes — that is, per full match played. Season totals reward
              whoever played most: a starter with 3,000 minutes out-scores a substitute
              with 500 almost regardless of ability. Dividing by minutes asks a fairer
              question.
            </p>
          </div>

          <div className="grid grid--2">
            <article className="card">
              <h3>In a typical full match</h3>
              <p>
                Every counting statistic is divided by minutes played and multiplied by
                90, so two players can be compared on rate rather than availability.
              </p>

              <div className="guide__example">
                <b>0.77</b>
                <span className="guide__arrow">means</span>
                <span>a goal roughly every 1.3 full matches</span>
              </div>

              <div className="guide__example">
                <b>0.31</b>
                <span className="guide__arrow">means</span>
                <span>a goal roughly every 3 full matches</span>
              </div>

              <p className="table-note">
                Players under 450 minutes are excluded entirely — a per-90 rate from a
                handful of appearances is mostly noise.
              </p>
            </article>

            <article className="card">
              <h3>What the data does not include</h3>
              <p>
                One season of on-pitch counting statistics, and nothing else. Questions
                hinging on any of the following cannot be answered from it, and the
                assistant is instructed to say so rather than substitute a figure it
                found in a news article.
              </p>

              <ul className="list">
                <li>Wages, transfer fees and market values</li>
                <li>Age and contract length</li>
                <li>Injury history and availability</li>
                <li>Expected goals and other modelled metrics</li>
                <li>Anything match-by-match — these are season aggregates</li>
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section className="section" id="models">
        <div className="shell">
          <div className="section__head">
            <span className="section__eyebrow">Under the hood</span>
            <h2 className="section__title">
              No single representation is trustworthy
            </h2>
            <p className="section__lede">
              Each of the three was measured across all {players} players. Position
              consistency is the share of a player's ten nearest neighbours sharing
              their listed position. Neighbour spread is the gap between the closest and
              tenth-closest score — a model whose top ten are all equally similar is not
              ranking anything.
            </p>
          </div>

          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Representation</th>
                  <th>What it is</th>
                  <th className="num">Dims</th>
                  <th className="num">Consistency</th>
                  <th className="num">Spread</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {REPRESENTATIONS.map((row) => (
                  <tr key={row.name}>
                    <td>
                      <code>{row.name}</code>
                    </td>
                    <td className="muted">{row.what}</td>
                    <td className="num">{row.dims}</td>
                    <td className="num">{row.consistency}</td>
                    <td className="num">{row.spread}</td>
                    <td className="muted">{row.verdict}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="table-note">
            The triplet model scores best on consistency and is close to worthless on
            spread — it collapsed into position clusters, which the consistency metric
            cannot detect. That is precisely why the assistant uses all three and ranks
            by agreement, and why every candidate is shown with the number of models that
            retrieved it.
          </p>
        </div>
      </section>

      <section className="section section--tint" id="pipeline">
        <div className="shell">
          <div className="section__head">
            <span className="section__eyebrow">The pipeline</span>
            <h2 className="section__title">From raw CSV to a similarity index</h2>
            <p className="section__lede">
              Everything below runs once, offline. Nothing is computed while you wait,
              which is why a similarity lookup returns in tens of milliseconds.
            </p>
          </div>

          <div className="pipeline">
            <div className="pipeline__stage">
              <span className="pipeline__value">562</span>
              <span className="pipeline__label">players in the raw dataset</span>
            </div>
            <div className="pipeline__stage">
              <span className="pipeline__value">397</span>
              <span className="pipeline__label">after the 450-minute filter</span>
            </div>
            <div className="pipeline__stage">
              <span className="pipeline__value">51</span>
              <span className="pipeline__label">per-90 and percentage features</span>
            </div>
            <div className="pipeline__stage">
              <span className="pipeline__value">41</span>
              <span className="pipeline__label">after pruning correlations &gt; 0.90</span>
            </div>
            <div className="pipeline__stage">
              <span className="pipeline__value">3 &times;</span>
              <span className="pipeline__label">397 &times; 397 similarity grids</span>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section__head">
            <span className="section__eyebrow">Try it</span>
            <h2 className="section__title">Questions this can answer well</h2>
            <p className="section__lede">
              These stay inside what the embeddings and the per-90 table actually know.
            </p>
          </div>

          <div className="examples">
            {suggestions.slice(0, 6).map((question) => (
              <Link className="example" key={question} to={ASK_PATH(question)}>
                <span>{question}</span>
                <span className="example__arrow">&rarr;</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="cta">
        <div className="shell shell--narrow">
          <h2>Ask it something</h2>
          <p>Type a player's name and the assistant will show its working.</p>
          <Link className="button button--accent" to="/ask">
            Open the assistant
          </Link>
        </div>
      </section>
    </>
  );
}
