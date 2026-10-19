// The site's API, on the same origin (PHASE_3.md 3.7 (g)). Nothing else is ever fetched: the
// Content-Security-Policy allows only the site itself (invariant 15). The session is an HttpOnly
// cookie the page never reads (3.7 (g)); every write is JSON and carries `Origin`, which the server
// checks (#330 point 19). The site's `Referrer-Policy: no-referrer` would make a browser send
// `Origin: null` on a same-origin write, so each request asks for the "same-origin" policy: the
// `Origin` is then the site's own, and no referrer ever leaves for another host.
import type { Bar } from './bar'
import type {
  CardsPage,
  CardsResponse,
  FlagAnswer,
  PostData,
  Reference,
  SavedProfile,
  SessionUser,
  TelegramCode,
  TelegramState,
} from './types'

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

/** The one request every page makes (the admin's pages too, admin/api.ts). */
export async function call<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
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
  /** The cards for what the bar holds (#314, #315): a read; the bar is never saved. `first`: how
   * many come whole with the order (#376); 0, the count alone (#378). */
  cards: (bar: Bar, first: number, signal?: AbortSignal, showHidden = false) =>
    call<CardsResponse>('POST', '/api/cards', { ...bar, first, show_hidden: showHidden }, signal),
  /** A later page of a load: the cards of these ids, against the same bar (#376). */
  cardsById: (bar: Bar, ids: string[], signal?: AbortSignal, showHidden = false) =>
    call<CardsPage>('POST', '/api/cards/by-id', { bar, ids, show_hidden: showHidden }, signal),
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
  // Phase 4: linking Telegram from the preferences page (#453).
  telegram: () => call<TelegramState>('GET', '/api/telegram'),
  /** A one-time code, shown once: the deep link to the bot, and the code to type. */
  telegramLink: () => call<TelegramCode>('POST', '/api/telegram/link', {}),
  telegramUnlink: () => call<TelegramState>('DELETE', '/api/telegram', {}),
  // Build step 6 (3.7 (i)): a post no longer in a current card answers 409, refusal "gone".
  /** Opening a post marks its card viewed (#253). */
  markViewed: (id: string) => call<{ viewed: true }>('POST', `/api/viewed/${encodeURIComponent(id)}`, {}),
  unmarkViewed: (id: string) => call<{ viewed: false }>('DELETE', `/api/viewed/${encodeURIComponent(id)}`, {}),
  /** "הסתר" (#464, #468): the card's shown post; "בטל הסתרה": every post of the card. */
  hide: (id: string) => call<{ hidden: true }>('POST', `/api/hidden/${encodeURIComponent(id)}`, {}),
  unhide: (id: string) => call<{ hidden: false }>('DELETE', `/api/hidden/${encodeURIComponent(id)}`, {}),
  /** "המודעה משקרת": every publication of the card (#300). */
  flag: (id: string) => call<FlagAnswer>('POST', `/api/flag/${encodeURIComponent(id)}`, {}),
  /** "סיווג שגוי": the shown post only (#300); `removed` false when the admin will handle it. */
  report: (id: string, fields: string[], note: string | null) =>
    call<{ removed: boolean }>('POST', `/api/report/${encodeURIComponent(id)}`, { fields, note }),
}
