export type BacklogStatus = 'wishlist' | 'backlog' | 'playing' | 'completed' | 'dropped'

export interface Game {
  id: number
  title: string
  cover_url: string | null
  release_date: string | null
  genres: string | null
}

export interface EntryUser {
  id: number
  username: string
  avatar_url: string | null
}

export interface BacklogEntry {
  id: number
  status: BacklogStatus
  rating: number | null
  notes: string | null
  hours_played: number | null
  user: EntryUser
  game: Game
}

export interface ActivityEvent {
  id: number
  event_type: 'added' | 'status_changed' | 'removed'
  from_status: BacklogStatus | null
  to_status: BacklogStatus | null
  created_at: string
  user: { username: string; avatar_url: string | null }
  game: { id: number; title: string; cover_url: string | null }
}

export interface Recommendation {
  id: number
  note: string | null
  source: 'web' | 'bot'
  created_at: string
  recommended_by: EntryUser
  game: Game
}

export interface Workspace {
  id: number
  name: string
}

export interface Me {
  id: number
  discord_id: string
  username: string
  avatar_url: string | null
  workspaces: Workspace[]
}

export const BACKLOG_STATUSES: BacklogStatus[] = [
  'wishlist',
  'backlog',
  'playing',
  'completed',
  'dropped',
]
