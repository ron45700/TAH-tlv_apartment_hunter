// The site's API, on the same origin (PHASE_3.md 3.7 (g)). Nothing else is ever fetched: the
// Content-Security-Policy allows only the site itself (invariant 15).
import type { CardsResponse, PostData } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, { credentials: 'same-origin', signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'network error')
  }
  if (!response.ok) throw new ApiError(response.status, response.statusText)
  return (await response.json()) as T
}

export const api = {
  /** A guest's list: the empty bar (#315). The bar's POST arrives with step 4. */
  cards: (signal?: AbortSignal) => get<CardsResponse>('/api/cards', signal),
  post: (id: string, signal?: AbortSignal) =>
    get<PostData>(`/api/posts/${encodeURIComponent(id)}`, signal),
}
