// The page's addresses (PHASE_3.md 3.7 (f), (k): no router library): the list, /post/<id> (its own
// address, so the browser's back closes it), and the screens of build step 5: /sign-in, /sign-up,
// /password and /preferences.
//
// A screen with unsaved changes (the preferences page) sets a guard: a link inside the site, the
// browser's back and forward, a reload and closing the tab all ask first (3.7 (e)(iii)).
import { useEffect, useState } from 'react'

export type Route =
  | { name: 'list' }
  | { name: 'post'; id: string }
  | { name: 'sign-in' }
  | { name: 'sign-up' }
  | { name: 'password' }
  | { name: 'preferences' }

const SCREENS = ['sign-in', 'sign-up', 'password', 'preferences'] as const

export function parseRoute(pathname: string): Route {
  const match = /^\/post\/([^/]+)\/?$/.exec(pathname)
  if (match) return { name: 'post', id: decodeURIComponent(match[1]) }
  const screen = SCREENS.find((name) => pathname.replace(/\/$/, '') === `/${name}`)
  return screen ? { name: screen } : { name: 'list' }
}

export function postPath(id: string): string {
  return `/post/${encodeURIComponent(id)}`
}

const listeners = new Set<() => void>()
let guard: (() => boolean) | null = null
let shownPath = typeof location === 'undefined' ? '/' : location.pathname

/** While set, leaving asks first; `fn` answers whether there is something to lose. */
export function setLeaveGuard(fn: (() => boolean) | null): void {
  guard = fn
}

export const LEAVE_QUESTION = 'יש שינויים שלא נשמרו. לצאת בלי לשמור?'

function mayLeave(): boolean {
  return !guard || !guard() || window.confirm(LEAVE_QUESTION)
}

function changed(): void {
  shownPath = location.pathname
  listeners.forEach((listener) => listener())
}

export function navigate(path: string, { replace = false }: { replace?: boolean } = {}): void {
  if (path === location.pathname) return
  if (!mayLeave()) return
  guard = null
  if (replace) history.replaceState(null, '', path)
  else history.pushState(null, '', path)
  changed()
}

if (typeof window !== 'undefined') {
  window.addEventListener('popstate', () => {
    if (guard && guard() && !window.confirm(LEAVE_QUESTION)) {
      history.pushState(null, '', shownPath) // stay: the address back to the screen shown
      return
    }
    guard = null
    changed()
  })
  window.addEventListener('beforeunload', (event) => {
    if (guard && guard()) event.preventDefault()
  })
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(location.pathname))
  useEffect(() => {
    const update = () => setRoute(parseRoute(location.pathname))
    listeners.add(update)
    return () => {
      listeners.delete(update)
    }
  }, [])
  return route
}
