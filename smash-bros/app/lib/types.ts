/**
 * Types des réponses de l'API (champs utilisés par le frontend uniquement)
 * et des objets dérivés passés aux modales.
 */

export interface User {
  id: number;
  username: string;
  display_name: string;
  avatar_url?: string | null;
  is_admin: boolean;
  intra_id: number | null;
  balance: number;
}

export interface UserStats {
  wins: number;
  losses: number;
  tournaments: number;
  rank: number | null;
  avatar_url?: string | null;
}

export interface Settings {
  duel_gage_win_reward?: number;
}

/** Gage tel que renvoyé par /api/shop/gages et /api/admin/gages */
export interface Gage {
  id: number;
  name: string;
  description: string;
  price: number;
  reward?: number | null;
  image_url?: string | null;
  is_archived?: boolean;
}

export interface InventoryEntry {
  id: number;
  gage: Gage | null;
}

/** Article affiché dans la boutique */
export interface ShopItem {
  id: number;
  name: string;
  gage: string;
  price: number;
  gain: number;
  image?: string | null;
}

/** Article de l'inventaire, regroupé par gage */
export interface InventoryItem extends ShopItem {
  qty: number;
  inventoryItemIds: number[];
}

export interface Sprite {
  [key: string]: unknown;
}

export interface Fighter {
  image: string;
  color?: string;
  [key: string]: unknown;
}

export interface LeaderboardEntry {
  [key: string]: unknown;
}

export interface Participant {
  user_id: number;
  username?: string;
  display_name?: string | null;
}

export interface MatchGage {
  imposer_id: number;
  status: string;
}

export interface Match {
  code: string;
  status: string;
  betting_open?: boolean;
  started_at?: string | null;
  winner_id?: number | null;
  player1_id?: number | null;
  player2_id?: number | null;
  gages?: MatchGage[];
}

export type TournamentRule = string | { label: string; value: string };

/** Tournoi tel que renvoyé par /api/tournaments?full=true */
export interface RawTournament {
  id: number;
  name: string;
  status?: string;
  rewards?: {
    champion?: number;
    match_won?: number;
  };
  created_at: string;
  date_label?: string | null;
  max_players?: number | null;
  rules?: TournamentRule[];
  matches?: Match[];
  participants?: Participant[];
}

/** Tournoi normalisé pour les modales */
export interface Tournament extends Omit<RawTournament, "rules" | "matches"> {
  date: string;
  max_players: number;
  rules: string[];
  matches: Match[];
}

export interface DuelUser {
  id: number;
  username: string;
  display_name?: string | null;
}

export type DuelStatus =
  | "pending"
  | "accepted"
  | "refused"
  | "validated"
  | "in_progress"
  | "completed"
  | "cancelled";

export interface Duel {
  id: number;
  status: DuelStatus;
  challenger: DuelUser;
  opponent: DuelUser;
  challenger_score: number | null;
  opponent_score: number | null;
  winner_id: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  betting_open: boolean;
}

/** Match (tournoi ou duel) sur lequel un objet de l'inventaire peut être équipé */
export interface PlayableMatch {
  id: string;
  kind: "tournament" | "duel";
  tournamentId?: number;
  matchCode?: string;
  duelId?: number;
  targetId?: number | null;
  opponent: string;
  info: string;
  disabled?: boolean;
}

/** Données du formulaire de création de tournoi */
export interface TournamentFormData {
  name: string;
  id?: number;
  reward?: string | number;
  matchReward?: string | number;
  date?: string;
  time?: string;
  maxPlayers?: string | number;
  losers_bracket?: string;
  format?: string;
  lives?: string | number;
  time_limit?: string;
  items?: string;
}

export type GagePayload = Record<string, unknown>;
