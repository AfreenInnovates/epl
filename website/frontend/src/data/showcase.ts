/**
 * Everything the landing page shows that is not fetched at runtime.
 *
 * The leaderboards below are counted from data/raw/epl_player_stats_24_25.csv —
 * the same file the embeddings are built from — so the home page and the
 * assistant never disagree. Crests and player portraits are hot-linked from
 * the Premier League's public image CDN; photography is from Unsplash.
 */

export interface Club {
  /** Name exactly as it appears in the dataset. */
  name: string;
  /** What fits on a card. */
  short: string;
  /** Premier League badge code, e.g. 3 -> /badges/50/t3.png */
  badge: number;
}

export const CLUBS: Club[] = [
  { name: "Arsenal", short: "Arsenal", badge: 3 },
  { name: "Aston Villa", short: "Aston Villa", badge: 7 },
  { name: "Bournemouth", short: "Bournemouth", badge: 91 },
  { name: "Brentford", short: "Brentford", badge: 94 },
  { name: "Brighton & Hove Albion", short: "Brighton", badge: 36 },
  { name: "Chelsea", short: "Chelsea", badge: 8 },
  { name: "Crystal Palace", short: "Crystal Palace", badge: 31 },
  { name: "Everton", short: "Everton", badge: 11 },
  { name: "Fulham", short: "Fulham", badge: 54 },
  { name: "Ipswich Town", short: "Ipswich", badge: 40 },
  { name: "Leicester City", short: "Leicester", badge: 13 },
  { name: "Liverpool", short: "Liverpool", badge: 14 },
  { name: "Manchester City", short: "Man City", badge: 43 },
  { name: "Manchester United", short: "Man Utd", badge: 1 },
  { name: "Newcastle United", short: "Newcastle", badge: 4 },
  { name: "Nottingham Forest", short: "Forest", badge: 17 },
  { name: "Southampton", short: "Southampton", badge: 20 },
  { name: "Tottenham Hotspur", short: "Spurs", badge: 6 },
  { name: "West Ham United", short: "West Ham", badge: 21 },
  { name: "Wolverhampton Wanderers", short: "Wolves", badge: 39 },
];

const BADGE_BY_CLUB = new Map(CLUBS.map((club) => [club.name, club.badge]));
const CLUB_BY_NAME = new Map(CLUBS.map((club) => [club.name, club]));

export function crest(club: string, size: 25 | 50 | 70 = 50): string {
  const badge = BADGE_BY_CLUB.get(club);

  return badge
    ? `https://resources.premierleague.com/premierleague/badges/${size}/t${badge}.png`
    : "";
}

export function clubShort(club: string): string {
  return CLUB_BY_NAME.get(club)?.short ?? club;
}

/** Premier League portrait CDN. Ids resolved from the league's own player search. */
export function portrait(optaId: string): string {
  return `https://resources.premierleague.com/premierleague/photos/players/110x140/${optaId}.png`;
}

export interface Leader {
  player: string;
  club: string;
  opta: string;
  value: number;
  /** Per 90 minutes — the rate the assistant actually reasons about. */
  per90: number;
}

/** Goals, 2024/25, counted from the dataset. */
export const TOP_SCORERS: Leader[] = [
  { player: "Mohamed Salah", club: "Liverpool", opta: "p118748", value: 29, per90: 0.77 },
  { player: "Alexander Isak", club: "Newcastle United", opta: "p219168", value: 23, per90: 0.75 },
  { player: "Erling Haaland", club: "Manchester City", opta: "p223094", value: 22, per90: 0.72 },
  { player: "Bryan Mbeumo", club: "Brentford", opta: "p446008", value: 20, per90: 0.53 },
  { player: "Chris Wood", club: "Nottingham Forest", opta: "p60689", value: 20, per90: 0.6 },
  { player: "Yoane Wissa", club: "Brentford", opta: "p216646", value: 19, per90: 0.58 },
  { player: "Ollie Watkins", club: "Aston Villa", opta: "p178301", value: 16, per90: 0.55 },
  { player: "Cole Palmer", club: "Chelsea", opta: "p244851", value: 15, per90: 0.42 },
];

/** Assists, 2024/25, same source. */
export const TOP_CREATORS: Leader[] = [
  { player: "Mohamed Salah", club: "Liverpool", opta: "p118748", value: 18, per90: 0.48 },
  { player: "Jacob Murphy", club: "Newcastle United", opta: "p114243", value: 12, per90: 0.47 },
  { player: "Anthony Elanga", club: "Nottingham Forest", opta: "p449434", value: 11, per90: 0.42 },
  { player: "Bukayo Saka", club: "Arsenal", opta: "p223340", value: 10, per90: 0.62 },
  { player: "Morgan Rogers", club: "Aston Villa", opta: "p244850", value: 10, per90: 0.31 },
  { player: "Mikkel Damsgaard", club: "Brentford", opta: "p440089", value: 10, per90: 0.38 },
  { player: "Antonee Robinson", club: "Fulham", opta: "p169528", value: 10, per90: 0.3 },
  { player: "Bruno Fernandes", club: "Manchester United", opta: "p141746", value: 10, per90: 0.28 },
];

export interface ClubRow {
  club: string;
  squad: number;
  goals: number;
  assists: number;
}

/**
 * Squad output, not a league table — this dataset holds no results, so there
 * are no points to show. Clubs are ranked by the goals their players scored.
 */
export const CLUB_TABLE: ClubRow[] = [
  { club: "Liverpool", squad: 24, goals: 72, assists: 60 },
  { club: "Manchester City", squad: 31, goals: 71, assists: 31 },
  { club: "Arsenal", squad: 25, goals: 67, assists: 50 },
  { club: "Newcastle United", squad: 23, goals: 66, assists: 37 },
  { club: "Brighton & Hove Albion", squad: 30, goals: 63, assists: 24 },
  { club: "Chelsea", squad: 28, goals: 63, assists: 32 },
  { club: "Aston Villa", squad: 27, goals: 61, assists: 46 },
  { club: "Nottingham Forest", squad: 23, goals: 57, assists: 39 },
  { club: "Brentford", squad: 28, goals: 54, assists: 33 },
  { club: "Crystal Palace", squad: 26, goals: 51, assists: 37 },
  { club: "Tottenham Hotspur", squad: 31, goals: 50, assists: 36 },
  { club: "Everton", squad: 26, goals: 41, assists: 17 },
  { club: "Fulham", squad: 26, goals: 41, assists: 37 },
  { club: "Wolverhampton Wanderers", squad: 32, goals: 39, assists: 34 },
  { club: "Manchester United", squad: 30, goals: 38, assists: 27 },
  { club: "West Ham United", squad: 28, goals: 31, assists: 25 },
  { club: "Leicester City", squad: 31, goals: 28, assists: 21 },
  { club: "Bournemouth", squad: 29, goals: 24, assists: 28 },
  { club: "Ipswich Town", squad: 30, goals: 23, assists: 20 },
  { club: "Southampton", squad: 34, goals: 23, assists: 10 },
];

export interface Matchup {
  left: { player: string; club: string; opta: string };
  right: { player: string; club: string; opta: string };
  tag: string;
  question: string;
}

/**
 * The fixture strip of a football site, rebuilt as comparisons. Each card is a
 * question for the assistant, not a claim that the two players are alike.
 */
export const MATCHUPS: Matchup[] = [
  {
    left: { player: "Mohamed Salah", club: "Liverpool", opta: "p118748" },
    right: { player: "Bukayo Saka", club: "Arsenal", opta: "p223340" },
    tag: "Right wing",
    question: "Compare Mohamed Salah and Bukayo Saka on the ball",
  },
  {
    left: { player: "Erling Haaland", club: "Manchester City", opta: "p223094" },
    right: { player: "Alexander Isak", club: "Newcastle United", opta: "p219168" },
    tag: "Centre forward",
    question: "Compare Erling Haaland and Alexander Isak",
  },
  {
    left: { player: "Cole Palmer", club: "Chelsea", opta: "p244851" },
    right: { player: "Bruno Fernandes", club: "Manchester United", opta: "p141746" },
    tag: "Playmaker",
    question: "Compare Cole Palmer and Bruno Fernandes",
  },
  {
    left: { player: "Chris Wood", club: "Nottingham Forest", opta: "p60689" },
    right: { player: "Ollie Watkins", club: "Aston Villa", opta: "p178301" },
    tag: "Penalty box",
    question: "Compare Chris Wood and Ollie Watkins",
  },
  {
    left: { player: "Bryan Mbeumo", club: "Brentford", opta: "p446008" },
    right: { player: "Yoane Wissa", club: "Brentford", opta: "p216646" },
    tag: "Same front line",
    question: "Compare Bryan Mbeumo and Yoane Wissa",
  },
  {
    left: { player: "Jacob Murphy", club: "Newcastle United", opta: "p114243" },
    right: { player: "Anthony Elanga", club: "Nottingham Forest", opta: "p449434" },
    tag: "Wide creators",
    question: "Compare Jacob Murphy and Anthony Elanga",
  },
];

export interface Slide {
  eyebrow: string;
  title: string;
  lede: string;
}

export const HERO_SLIDES: Slide[] = [
  {
    eyebrow: "The 2024/25 season, one row per player",
    title: "This is\nPremier League intelligence",
    lede: "Ask what the numbers actually say about a player. Similarity from three learned embeddings, season statistics read straight from the table, and every step shown.",
  },
  {
    eyebrow: "Similarity search",
    title: "Who plays\nlike Bukayo Saka?",
    lede: "Three independent representations each return their nearest neighbours. Candidates all three agree on rank above the ones only a single model liked.",
  },
  {
    eyebrow: "Per 90 minutes",
    title: "Rates, not\nseason totals",
    lede: "Every counting statistic is divided by minutes played, so a substitute and an ever-present are compared on what they do rather than how often they played.",
  },
  {
    eyebrow: "Shown, not asserted",
    title: "It shows\nits working",
    lede: "The tool being called, the full candidate shortlist, the figures behind every claim, and a plain list of what this data cannot answer.",
  },
];

export interface Feature {
  kicker: string;
  title: string;
  href: string;
  image: string;
}

/** Unsplash, free to use, hot-linked at a fixed crop. */
const unsplash = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=760&h=460&q=70`;

export const FEATURES: Feature[] = [
  {
    kicker: "Method",
    title: "How one question becomes four visible steps",
    href: "#how-it-works",
    image: unsplash("photo-1522778119026-d647f0596c20"),
  },
  {
    kicker: "Reading the output",
    title: "Why every figure is a rate per 90 minutes",
    href: "#per-90",
    image: unsplash("photo-1552667466-07770ae110d0"),
  },
  {
    kicker: "Under the hood",
    title: "Three embeddings, and why no single one is trusted",
    href: "#models",
    image: unsplash("photo-1543326727-cf6c39e8f84c"),
  },
  {
    kicker: "The pipeline",
    title: "From 562 rows of CSV to a similarity index",
    href: "#pipeline",
    image: unsplash("photo-1560272564-c83b66b1ad12"),
  },
];

export interface Prompt {
  question: string;
  label: string;
  opta: string;
  club: string;
}

export const PROMPTS: Prompt[] = [
  {
    question: "Who plays like Bukayo Saka, and why?",
    label: "Similarity · Arsenal",
    opta: "p223340",
    club: "Arsenal",
  },
  {
    question: "Which defenders are most similar to Virgil van Dijk?",
    label: "Similarity · Liverpool",
    opta: "p97032",
    club: "Liverpool",
  },
  {
    question: "Do all three models agree on who resembles Cole Palmer?",
    label: "Model agreement · Chelsea",
    opta: "p244851",
    club: "Chelsea",
  },
];
