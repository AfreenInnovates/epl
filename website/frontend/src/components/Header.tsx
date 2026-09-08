import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { Crest } from "./Media";
import type { Health, PlayerSummary } from "../types";

interface Props {
  health: Health | null;
}

/** Anchors live on the home page, so they are addressed from the root. */
const SECTIONS = [
  { label: "Clubs", href: "/#clubs" },
  { label: "Method", href: "/#how-it-works" },
  { label: "Models", href: "/#models" },
];

/** A player lookup that drops the visitor straight into a run. */
function PlayerSearch() {
  const [value, setValue] = useState("");
  const [matches, setMatches] = useState<PlayerSummary[]>([]);
  const [open, setOpen] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const needle = value.trim();

    if (needle.length < 3) {
      setMatches([]);
      return;
    }

    const timer = window.setTimeout(() => {
      api
        .players(needle)
        .then((results) => setMatches(results.slice(0, 6)))
        .catch(() => setMatches([]));
    }, 180);

    return () => window.clearTimeout(timer);
  }, [value]);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function pick(name: string) {
    setOpen(false);
    setValue("");
    navigate(`/ask?q=${encodeURIComponent(`Who plays like ${name}, and why?`)}`);
  }

  return (
    <div className="search" ref={containerRef}>
      <form
        className="search__field"
        onSubmit={(event) => {
          event.preventDefault();

          if (matches.length) {
            pick(matches[0].name);
          } else if (value.trim()) {
            navigate(`/ask?q=${encodeURIComponent(value.trim())}`);
            setValue("");
          }
        }}
      >
        <span className="search__icon" aria-hidden="true">
          &#9906;
        </span>
        <input
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search players"
          aria-label="Search players"
          autoComplete="off"
        />
      </form>

      {open && matches.length > 0 && (
        <div className="search__results" role="listbox">
          {matches.map((player) => (
            <button
              key={player.name}
              type="button"
              className="search__result"
              onClick={() => pick(player.name)}
            >
              {player.club && <Crest club={player.club} size={25} />}
              <span>
                <strong>{player.name}</strong>
                <span>
                  {player.club} · {player.position_label}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function Header({ health }: Props) {
  return (
    <header className="header">
      <div className="shell header__inner">
        <Link className="brand" to="/">
          <span className="brand__mark" aria-hidden="true">
            HS
          </span>
          <span className="brand__name">
            Halfspace
            <span>Premier League intelligence</span>
          </span>
        </Link>

        <nav className="nav" aria-label="Primary">
          <NavLink className="nav__link" to="/" end>
            Home
          </NavLink>

          <NavLink className="nav__link" to="/ask">
            Ask
          </NavLink>

          {SECTIONS.map((section) => (
            <a className="nav__link" key={section.href} href={section.href}>
              {section.label}
            </a>
          ))}
        </nav>

        <div className="header__tools">
          {health && !health.groq_configured && (
            <span className="pill pill--warn">
              <span className="pill__dot" />
              No model key
            </span>
          )}

          <PlayerSearch />

          <Link className="button button--accent button--sm" to="/ask">
            Ask
          </Link>
        </div>
      </div>
    </header>
  );
}
