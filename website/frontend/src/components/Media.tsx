import { useState } from "react";

import { clubShort, crest, portrait } from "../data/showcase";

interface CrestProps {
  club: string;
  size?: 25 | 50 | 70;
  className?: string;
}

/** A club badge from the league's public CDN, with the club name as alt text. */
export function Crest({ club, size = 50, className = "crest" }: CrestProps) {
  return (
    <img
      className={className}
      src={crest(club, size)}
      alt={`${clubShort(club)} badge`}
      loading="lazy"
      width={size}
      height={size}
    />
  );
}

interface AvatarProps {
  opta: string;
  club: string;
  name: string;
}

/**
 * A player portrait. Portraits are hot-linked, so any one of them can go
 * missing without warning — the club badge stands in rather than a broken
 * image box.
 */
export function PlayerAvatar({ opta, club, name }: AvatarProps) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <span className="avatar avatar--fallback">
        <Crest club={club} size={50} className="avatar__crest" />
      </span>
    );
  }

  return (
    <span className="avatar">
      <img src={portrait(opta)} alt={name} loading="lazy" onError={() => setFailed(true)} />
    </span>
  );
}
