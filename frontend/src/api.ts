// The site's API, on the same origin (PHASE_3.md 3.7 (g)). Nothing else is ever fetched: the
// Content-Security-Policy allows only the site itself (invariant 15). The session is an HttpOnly
// cookie the page never reads (3.7 (g)); every write is JSON and carries `Origin`, which the server
// checks (#330 point 19). The site's `Referrer-Policy: no-referrer` would make a browser send
// `Origin: null` on a same-origin write, so each request asks for the "same-origin" policy: the
// `Origin` is then the site's own, and no referrer ever leaves for another host.
import type { Bar } from './bar'
import type { CardsResponse, PostData, Reference, SavedProfile, SessionUser } from './types'

export class ApiError extends Error {
  readonly status: number
  /** The server's refusal: a 3.5 reason name ("wrong", "delayed", …). */
  readonly refusal: string | null
  readonly retryAfter: number | null
  /** A 422's rule, or another error's detail. */
  readonly detail: unknown

  constructor(status: number, body: Record<string, unknown> | null) {
    super(`HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.refusal = typeof body?.refusal === 'string' ? body.refusal : null
    this.retryAfter = typeof body?.retry_after_seconds === 'number' ? body.retry_after_seconds : null
    this.detail = body?.detail ?? null
  }
}

async function call<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      method,
      credentials: 'same-origin',
      referrerPolicy: 'same-origin',
      signal,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, null)
  }
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (!response.ok) throw new ApiError(response.status, payload as Record<string, unknown> | null)
  return payload as T
}

export const api = {
  reference: (signal?: AbortSignal) => call<Reference>('GET', '/api/reference', undefined, signal),
  /** The cards for what the bar holds (#314, #315): a read; the bar is never saved. */
  cards: (bar: Bar, signal?: AbortSignal) => call<CardsResponse>('POST', '/api/cards', bar, signal),
  post: (id: string, signal?: AbortSignal) =>
    call<PostData>('GET', `/api/posts/${encodeURIComponent(id)}`, undefined, signal),
  session: () => call<{ user: SessionUser | null }>('GET', '/api/session'),
  signIn: (username: string, password: string) =>
    call<{ user: SessionUser }>('POST', '/api/sign-in', { username, password }),
  signUp: (key: string, username: string, password: string) =>
    call<{ user: SessionUser }>('POST', '/api/sign-up', { key, username, password }),
  signOut: () => call<{ user: null }>('POST', '/api/sign-out', {}),
  password: (current: string, next: string) =>
    call<{ user: SessionUser }>('POST', '/api/password', { current, new: next }),
  profile: () => call<SavedProfile>('GET', '/api/profile'),
  /** The preferences page's save: the only place preferences are saved (#335). */
  saveProfile: (bar: Bar) => call<SavedProfile>('PUT', '/api/profile', bar),
}
