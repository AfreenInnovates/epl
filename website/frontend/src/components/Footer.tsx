import { Link } from "react-router-dom";

const COLUMNS = [
  {
    heading: "Explore",
    links: [
      { label: "Ask the assistant", to: "/ask" },
      { label: "Clubs", to: "/#clubs" },
      { label: "Squad output", to: "/#clubs" },
      { label: "Featured comparisons", to: "/" },
    ],
  },
  {
    heading: "Method",
    links: [
      { label: "How it works", to: "/#how-it-works" },
      { label: "What per 90 means", to: "/#per-90" },
      { label: "The three models", to: "/#models" },
      { label: "The pipeline", to: "/#pipeline" },
    ],
  },
  {
    heading: "The data",
    links: [
      { label: "2024/25 season", to: "/#clubs" },
      { label: "397 players, 41 features", to: "/#pipeline" },
      { label: "What it cannot answer", to: "/#per-90" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="footer">
      <div className="shell footer__grid">
        <div className="footer__brand">
          <span className="brand__mark" aria-hidden="true">
            HS
          </span>
          <p className="footer__blurb">
            A research assistant for Premier League player analysis, built on public
            2024/25 season statistics. Not affiliated with the Premier League.
          </p>
        </div>

        {COLUMNS.map((column) => (
          <nav className="footer__column" key={column.heading} aria-label={column.heading}>
            <h3>{column.heading}</h3>
            <ul>
              {column.links.map((link) => (
                <li key={link.label + link.to}>
                  {link.to.startsWith("/#") ? (
                    <a href={link.to}>{link.label}</a>
                  ) : (
                    <Link to={link.to}>{link.label}</Link>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        ))}

        <div className="footer__cta">
          <h3>Ask it something</h3>
          <p>
            Statistical similarity is evidence, not proof that two players share a role
            — so the assistant shows every candidate it considered.
          </p>
          <Link className="button button--accent button--sm" to="/ask">
            Open the assistant
          </Link>
        </div>
      </div>

      <div className="shell footer__legal">
        <p>Player statistics from the 2024/25 Premier League season, published on Kaggle.</p>
        <p>Crests and portraits © Premier League. Photography from Unsplash.</p>
      </div>
    </footer>
  );
}
