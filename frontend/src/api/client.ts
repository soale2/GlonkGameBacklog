import type { ActivityEvent, BacklogEntry, BacklogStatus, Game, Me, Recommendation } from './types'

const GENERIC_ERROR_MESSAGE = 'Something went wrong. Please try again.'

/** Reads the API's { "detail": "..." } error body, if present, so the UI can show a
 * plain sentence instead of a raw HTTP status and JSON body. */
async function readErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // The response body was not JSON. Fall through to the generic message.
  }
  return GENERIC_ERROR_MESSAGE
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    throw new Error(await readErrorMessage(res))
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export async function fetchMe(): Promise<Me | null> {
  const res = await fetch('/api/me', { credentials: 'include' })
  if (res.status === 401) return null
  if (!res.ok) throw new Error(GENERIC_ERROR_MESSAGE)
  return res.json()
}

export function searchGames(query: string): Promise<{ enriched: boolean; results: Game[] }> {
  return request(`/api/games/search?q=${encodeURIComponent(query)}`)
}

export function listBacklog(workspaceId: number): Promise<BacklogEntry[]> {
  return request(`/api/workspaces/${workspaceId}/backlog`)
}

export function addBacklogEntry(
  workspaceId: number,
  payload: { game_id?: number; title?: string; status: BacklogStatus },
): Promise<BacklogEntry> {
  return request(`/api/workspaces/${workspaceId}/backlog`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateBacklogEntry(
  workspaceId: number,
  entryId: number,
  payload: Partial<Pick<BacklogEntry, 'status' | 'rating' | 'notes' | 'hours_played'>>,
): Promise<BacklogEntry> {
  return request(`/api/workspaces/${workspaceId}/backlog/${entryId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteBacklogEntry(workspaceId: number, entryId: number): Promise<void> {
  return request(`/api/workspaces/${workspaceId}/backlog/${entryId}`, { method: 'DELETE' })
}

export function listActivity(workspaceId: number): Promise<ActivityEvent[]> {
  return request(`/api/workspaces/${workspaceId}/activity`)
}

export function listRecommendations(workspaceId: number): Promise<Recommendation[]> {
  return request(`/api/workspaces/${workspaceId}/recommendations`)
}

export function addRecommendation(
  workspaceId: number,
  payload: { game_id?: number; title?: string; note?: string },
): Promise<Recommendation> {
  return request(`/api/workspaces/${workspaceId}/recommendations`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteRecommendation(workspaceId: number, recommendationId: number): Promise<void> {
  return request(`/api/workspaces/${workspaceId}/recommendations/${recommendationId}`, {
    method: 'DELETE',
  })
}

export function acceptRecommendation(
  workspaceId: number,
  recommendationId: number,
): Promise<{ id: number; status: BacklogStatus }> {
  return request(`/api/workspaces/${workspaceId}/recommendations/${recommendationId}/accept`, {
    method: 'POST',
  })
}
