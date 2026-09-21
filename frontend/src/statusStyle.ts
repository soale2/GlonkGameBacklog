import type { BacklogStatus } from './api/types'

export const STATUS_LABELS: Record<BacklogStatus, string> = {
  wishlist: 'Wishlist',
  backlog: 'Backlog',
  playing: 'Playing',
  completed: 'Completed',
  dropped: 'Dropped',
}

export const STATUS_COLOR_VAR: Record<BacklogStatus, string> = {
  wishlist: 'var(--status-wishlist)',
  backlog: 'var(--status-backlog)',
  playing: 'var(--status-playing)',
  completed: 'var(--status-completed)',
  dropped: 'var(--status-dropped)',
}
