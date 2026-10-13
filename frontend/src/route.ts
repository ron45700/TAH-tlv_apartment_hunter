// The page's addresses (PHASE_3.md 3.7 (f), (k): no router library). The opened post has its own
// address, /post/<id>, so the browser's back closes it. The other screens arrive with steps 4 and 5.
import { useEffect, useState } from 'react'

export type Route = { name: 'list' } | { name: 'post'; id: string }

export function parseRoute(pathname: string): Route {
  const match = /^\/post\/([^/]+)\/?$/.exec(pathname)
  return match ? { name: 'post', id: decodeURIComponent(match[1]) } : { name: 'list' }
}

export function postPath(id: string): string {
  return `/post/${encodeURIComponent(id)}`
}

const listeners = new Set<() => void>()

export function navigate(path: string): void {
  if (path === location.pathname) return
  history.pushState(null, '', path)
  listeners.forEach((listener) => listener())
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(location.pathname))
  useEffect(() => {
    const update = () => setRoute(parseRoute(location.pathname))
    listeners.add(update)
    window.addEventListener('popstate', update)
    return () => {
      listeners.delete(update)
      window.removeEventListener('popstate', update)
    }
  }, [])
  return route
}
