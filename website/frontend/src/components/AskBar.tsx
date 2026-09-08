import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type { PlayerSummary } from "../types";

interface Props {
  onAsk: (question: string) => void;
  disabled?: boolean;
  autoFocus?: boolean;
  placeholder?: string;
  initialValue?: string;
}

/** The last whitespace-delimited fragment, used as the typeahead needle. */
function trailingFragment(value: string): string {
  const match = value.match(/([\p{L}'-]+(?:\s+[\p{L}'-]+)?)\s*$/u);
  return match ? match[1] : "";
}

export function AskBar({
  onAsk,
  disabled = false,
  autoFocus = false,
  placeholder = "Ask about any Premier League player…",
  initialValue = "",
}: Props) {
  const [value, setValue] = useState(initialValue);
  const [matches, setMatches] = useState<PlayerSummary[]>([]);
  const [highlighted, setHighlighted] = useState(0);
  const [open, setOpen] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (autoFocus) {
      inputRef.current?.focus();
    }
  }, [autoFocus]);

  // Debounced player lookup on the trailing fragment of the question.
  useEffect(() => {
    const fragment = trailingFragment(value);

    if (fragment.length < 3) {
      setMatches([]);
      return;
    }

    const timer = window.setTimeout(() => {
      api
        .players(fragment)
        .then((results) => {
          setMatches(results.slice(0, 5));
          setHighlighted(0);
        })
        .catch(() => setMatches([]));
    }, 180);

    return () => window.clearTimeout(timer);
  }, [value]);

  // Dismiss the typeahead when focus leaves the component.
  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const showSuggestions = open && matches.length > 0;

  function complete(name: string) {
    const fragment = trailingFragment(value);
    const next = value.slice(0, value.length - fragment.length) + name + " ";

    setValue(next);
    setOpen(false);
    inputRef.current?.focus();
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();

    const question = value.trim();

    if (question && !disabled) {
      setOpen(false);
      onAsk(question);
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!showSuggestions) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlighted((index) => (index + 1) % matches.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlighted((index) => (index - 1 + matches.length) % matches.length);
    } else if (event.key === "Tab") {
      event.preventDefault();
      complete(matches[highlighted].name);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <form className="ask" onSubmit={submit} ref={containerRef}>
      <div className="ask__field">
        <input
          ref={inputRef}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={500}
          aria-label="Your question"
          autoComplete="off"
        />
        <button
          className="button button--primary"
          type="submit"
          disabled={disabled || !value.trim()}
        >
          {disabled ? "Working…" : "Ask"}
        </button>
      </div>

      {showSuggestions && (
        <div className="ask__suggestions" role="listbox">
          {matches.map((player, index) => (
            <button
              key={player.name}
              type="button"
              className="ask__suggestion"
              data-active={index === highlighted}
              onMouseEnter={() => setHighlighted(index)}
              onClick={() => complete(player.name)}
            >
              <span>{player.name}</span>
              <span>
                {player.club} · {player.position_label}
              </span>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
