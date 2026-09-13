import type { EvidenceBase as Evidence } from "../types";

interface Props {
  evidence: Evidence;
  namedInAnswer: string[];
}

/**
 * What the system actually did, separate from what the model chose to write.
 *
 * The answer's prose may discuss one player out of ten the models returned.
 * This panel shows the whole shortlist, how many of the three representations
 * retrieved each name, and which of them the answer went on to mention -- so a
 * reader can see the ML output directly rather than inferring it.
 */
export function EvidenceBasePanel({ evidence, namedInAnswer }: Props) {
  const { candidates, statsFor, webSources, subject, refusedSearches } = evidence;
  const scraped = webSources.filter((source) => source.scraped).length;
  const cached = webSources.filter((source) => source.cache_hit).length;

  if (candidates.length === 0 && statsFor.length === 0 && webSources.length === 0) {
    return null;
  }

  const named = new Set(namedInAnswer);

  return (
    <section className="panel panel--evidence">
      <h3 className="panel__title">
        How this was derived
        <span className="panel__count">{evidence.toolCalls} tool calls</span>
      </h3>

      {candidates.length > 0 && (
        <div className="derived">
          <div className="derived__label">
            Similarity shortlist
            {subject && <span className="derived__sub"> for {subject}</span>}
          </div>

          <p className="derived__note">
            {candidates.length} candidates returned by the embedding search.
            {named.size > 0 && ` The answer discusses ${named.size}.`} Agreement
            counts how many of the three representations put the player in their
            own top results.
          </p>

          <div className="table-wrap">
            <table className="data">
            <thead>
              <tr>
                <th>Player</th>
                <th>Club</th>
                <th className="num">Agreement</th>
                <th className="num">Similarity</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr
                  key={candidate.player}
                  data-named={named.has(candidate.player)}
                >
                  <td>
                    {candidate.player}
                    {named.has(candidate.player) && (
                      <span className="shortlist__flag">in answer</span>
                    )}
                  </td>
                  <td className="muted">{candidate.club ?? "—"}</td>
                  <td className="num">
                    {candidate.models_retrieved} of 3
                  </td>
                  <td className="num muted">
                    {candidate.mean_similarity.toFixed(2)}
                  </td>
                </tr>
              ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {statsFor.length > 0 && (
        <div className="derived">
          <div className="derived__label">Statistics read</div>
          <p className="derived__note">
            Per-90 rows pulled from the 2024/25 table for{" "}
            {statsFor.join(", ")}.
          </p>
        </div>
      )}

      {evidence.agenticResearch?.summary && (
        <div className="derived derived--agentic">
          <div className="derived__label">Anakin Agentic Research</div>
          <p className="derived__note">{evidence.agenticResearch.summary}</p>
          {evidence.agenticResearch.citations.length > 0 && (
            <div className="agentic-citations">
              {evidence.agenticResearch.citations.slice(0, 5).map((source) => (
                <a href={source.url} key={source.url} target="_blank" rel="noreferrer noopener">
                  {source.title}
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {webSources.length > 0 && (
        <div className="derived">
          <div className="derived__label">Web pages retrieved</div>
          <p className="derived__note">
            {webSources.length} pages searched for tactical context, {scraped} scraped for
            page-level evidence.
            {cached > 0 && ` ${cached} result${cached === 1 ? " was" : "s were"} reused from cache.`}
            {evidence.anakinRefreshRequired &&
              " Official corpus evidence is available while Anakin refresh is pending."}
            {refusedSearches > 0 &&
              ` ${refusedSearches} further search${
                refusedSearches === 1 ? " was" : "es were"
              } declined once the two-search limit was reached.`}
          </p>

          <div className="source-evidence">
            {webSources.map((source) => (
              <details className="source-evidence__item" key={source.url}>
                <summary>
                  <span>{source.title}</span>
                  <span className="source-evidence__meta">
                    {source.official ? "official" : source.scraped ? "scraped" : "snippet"}
                    {source.cache_hit ? " · cached" : ""}
                  </span>
                </summary>
                {source.excerpt && <p>{source.excerpt}</p>}
              </details>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
