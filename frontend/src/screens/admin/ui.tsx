// The admin's shared pieces (3.8 (c)): the reason chip, a post's row, a load that waits out the
// site's first grouping (#380), and a link inside the site.
import { useEffect, useState, type MouseEvent, type ReactNode } from 'react'
import { ApiError } from '../../api'
import type { Row } from '../../admin/types'
import { REASON_FAMILY } from '../../admin/words'
import { formatPrice, israelTime, relativeTime } from '../../format'
import { adminPath, navigate } from '../../route'

const LOADING_RETRY_MS = 2000

export function go(path: string) {
  return (event: MouseEvent) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
    event.preventDefault()
    navigate(path)
  }
}

export function Link({
  to,
  className,
  current = false,
  children,
}: {
  to: string
  className?: string
  current?: boolean
  children: ReactNode
}) {
  return (
    <a href={to} className={className} onClick={go(to)} aria-current={current ? 'page' : undefined}>
      {children}
    </a>
  )
}

export type Load<T> = { state: 'loading' } | { state: 'failed'; status: number } | { state: 'ready'; data: T }

/** A read that waits out "loading" (#380): asked again every 2 s. `again` reloads by hand. */
export function useLoad<T>(fetcher: (signal: AbortSignal) => Promise<T>, key: string): [Load<T>, () => void] {
  const [load, setLoad] = useState<Load<T>>({ state: 'loading' })
  const [tries, setTries] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let retry = 0
    fetcher(controller.signal)
      .then((data) => setLoad({ state: 'ready', data }))
      .catch((error) => {
        if (error instanceof DOMException) return
        if (error instanceof ApiError && error.refusal === 'loading') {
          retry = window.setTimeout(() => setTries((n) => n + 1), LOADING_RETRY_MS)
        } else setLoad({ state: 'failed', status: error instanceof ApiError ? error.status : 0 })
      })
    return () => {
      window.clearTimeout(retry)
      controller.abort()
    }
  }, [key, tries]) // the fetcher follows `key`
  return [load, () => setTries((n) => n + 1)]
}

export function Waiting<T>({ load, children }: { load: Load<T>; children: (data: T) => ReactNode }) {
  if (load.state === 'loading') return <p className="adm-empty">טוען…</p>
  if (load.state === 'failed') {
    return (
      <p className="adm-empty">
        {load.status === 403 ? 'הדף הזה למנהל בלבד.' : 'הטעינה נכשלה. בדקו שהאתר פועל ורעננו את הדף.'}
      </p>
    )
  }
  return <>{children(load.data)}</>
}

export function ReasonChip({ row }: { row: Pick<Row, 'reason' | 'reason_words' | 'state' | 'state_words'> }) {
  if (!row.reason) return <span className="rchip rchip-state">{row.state_words}</span>
  return <span className={`rchip rchip-${REASON_FAMILY[row.reason]}`}>{row.reason_words}</span>
}

export function when(iso: string | null, now: Date): string {
  return iso ? `${relativeTime(iso, now)} (${israelTime(iso)})` : '—'
}

/** One post in a list: its first photo, its first lines, its reason and what the admin needs at a
 * glance. The whole row opens the post's detail. */
export function PostRow({ row, now, children }: { row: Row; now: Date; children?: ReactNode }) {
  const price = row.listing ? formatPrice(row.listing.price) : null
  const to = adminPath('post', row.id)
  return (
    <li className="arow">
      <a className="arow-open" href={to} onClick={go(to)}>
        <span className="arow-thumb" aria-hidden="true">
          {row.photo ? <img src={row.photo} alt="" loading="lazy" /> : <span className="arow-nophoto">אין תמונה</span>}
        </span>
        <span className="arow-body">
          <span className="arow-head">
            <ReasonChip row={row} />
            {row.city && <span className="arow-city">{row.city}</span>}
            {price && <span className="arow-price">{price}</span>}
            <span className="arow-time">{relativeTime(row.last_published_at, now)}</span>
          </span>
          <span className="arow-text" dir="auto">
            {(row.text ?? '').trim() || 'אין טקסט'}
          </span>
          {(row.publications > 1 || row.failures > 0 || row.corrected.length > 0) && (
            <span className="arow-meta">
              {row.publications > 1 && <span>פורסמה {row.publications} פעמים</span>}
              {row.failures > 0 && (
                <span className="arow-fail">
                  נכשלה בסיווג {row.failures === 1 ? 'פעם אחת' : `${row.failures} פעמים`}
                  {row.last_error ? `: ${row.last_error}` : ''}
                </span>
              )}
              {row.corrected.length > 0 && <span>תוקנה ביד</span>}
            </span>
          )}
        </span>
      </a>
      {children}
    </li>
  )
}
