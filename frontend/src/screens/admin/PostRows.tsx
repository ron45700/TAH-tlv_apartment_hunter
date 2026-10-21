// The admin's post lists (3.8 (c)): rejected (with the reason chips and their counts, #403), pending,
// archive and flags (by user and flag action, #393). Canonicals only (#75 B). They come in pages as
// the users' list does (#376): the whole order with the first rows, the rest as the admin scrolls.
import { useCallback, useEffect, useRef, useState } from 'react'
import { adminApi } from '../../admin/api'
import type { ListName, Reason, Row } from '../../admin/types'
import { REASON_FAMILY, REASON_NAMES, REASON_ORDER, flagActions, restoreLabel } from '../../admin/words'
import { ApiError } from '../../api'
import { PAGE, firstLoad, nextIds, withPage, withoutCard, type Loaded } from '../../paging'
import { Announce, PostRow, useLoad, Waiting, when, type Message } from './ui'

const RETRY_MS = 2000

const EMPTY: Record<ListName, string> = {
  rejected: 'אין מודעות שנדחו.',
  pending: 'אין מודעות שממתינות לסיווג.',
  archive: 'הארכיון ריק. מודעות עוברות לארכיון רק משלב 5.',
  flags: 'אף משתמש לא סימן מודעה כמשקרת.',
}

const LEADS: Record<ListName, string> = {
  rejected: 'כל מודעה שנדחתה, מכל סיבה. רק המודעה המקורית, בלי הפרסומים החוזרים שלה.',
  pending: 'מודעות שעוד לא סווגו. המתזמן מסווג אותן אחרי כל ריצת איסוף.',
  archive: 'מודעות שעברו לארכיון, עם הסיבה שהייתה להן.',
  flags: 'מודעות שמשתמשים סימנו כמשקרות, לפי המשתמש ולפי הסימון. סימון אחד על מודעה שפורסמה כמה פעמים חל על כל הפרסומים.',
}

export function PostRows({ list, now, onChanged }: { list: ListName; now: Date; onChanged: () => void }) {
  const [reason, setReason] = useState<Reason | null>(null)
  const [loaded, setLoaded] = useState<Loaded<Row> | null>(null)
  const [reasons, setReasons] = useState<Partial<Record<Reason, number>>>({})
  const [notice, setNotice] = useState<Message | null>(null)
  const announce = useRef<HTMLDivElement>(null)
  const [busy, setBusy] = useState(false)
  const [load] = useLoad((signal) => adminApi.rows(list, reason, PAGE, signal), `${list}:${reason ?? ''}`)

  useEffect(() => {
    setReason(null)
    setLoaded(null)
  }, [list])
  useEffect(() => {
    if (load.state !== 'ready') return
    setLoaded(firstLoad(load.data))
    if (load.data.reasons) setReasons(load.data.reasons)
  }, [load])

  const paging = useRef(false)
  const [retries, setRetries] = useState(0)
  const sentinel = useRef<HTMLDivElement>(null)
  const more = useCallback(() => {
    if (!loaded || paging.current) return
    const ids = nextIds(loaded)
    if (ids.length === 0) return
    paging.current = true
    const from = loaded.order
    adminApi
      .rowsById(list, reason, ids)
      .then((page) => setLoaded((current) => (current && current.order === from ? withPage(current, ids, page) : current)))
      .catch(() => window.setTimeout(() => setRetries((n) => n + 1), RETRY_MS))
      .finally(() => {
        paging.current = false
      })
  }, [loaded, list, reason])
  useEffect(() => {
    const target = sentinel.current
    if (!target || !loaded || loaded.next >= loaded.order.length) return
    const observer = new IntersectionObserver((entries) => entries.some((e) => e.isIntersecting) && more(), {
      rootMargin: '0px 0px 150% 0px',
    })
    observer.observe(target)
    return () => observer.disconnect()
  }, [loaded, more, retries])

  /** A flag action's posts restored together (#393), each by its own compare and set: the
   * restored rows leave the list in place; a post that changed meanwhile stays, and the page says so. */
  const restoreRows = (rows: Row[]) => {
    const words = rows.length === 1 ? 'את המודעה' : `את ${rows.length} הפרסומים`
    if (!window.confirm(`לשחזר ${words}? הסימון יוסר, והמצב יחושב מחדש מהסיווג.`)) return
    setBusy(true)
    setNotice(null)
    adminApi
      .restore(rows.map((row) => ({ listing_id: row.id, version: row.version })))
      .then(({ results }) => {
        const restored = results.filter((r) => r.outcome === 'restored').map((r) => r.listing_id)
        setLoaded((current) => restored.reduce((acc, id) => (acc ? withoutCard(acc, id) : acc), current))
        const left = results.length - restored.length
        setNotice(
          left === 0
            ? { ok: true, text: restored.length === 1 ? 'המודעה שוחזרה.' : `${restored.length} פרסומים שוחזרו.` }
            : { ok: false, text: `שוחזרו ${restored.length} מתוך ${results.length}: השאר השתנו בינתיים. רעננו את הדף ונסו שוב.` },
        )
        onChanged()
        requestAnimationFrame(() => announce.current?.focus()) // the button pressed is gone (#411)
      })
      .catch((error) =>
        setNotice({ ok: false, text: error instanceof ApiError ? 'השחזור נדחה.' : 'השחזור לא נשמר. בדקו את החיבור ונסו שוב.' }),
      )
      .finally(() => setBusy(false))
  }

  const total = Object.values(reasons).reduce((sum, n) => sum + (n ?? 0), 0)
  return (
    <>
      <p className="adm-lead">{LEADS[list]}</p>
      {list === 'rejected' && total > 0 && (
        <div className="reasonbar" role="group" aria-label="סינון לפי סיבה">
          <button type="button" className="rfilter" aria-pressed={reason === null} onClick={() => setReason(null)}>
            הכל <span className="rcount">{total}</span>
          </button>
          {REASON_ORDER.filter((name) => reasons[name]).map((name) => (
            <button
              key={name}
              type="button"
              className={`rfilter rfilter-${REASON_FAMILY[name]}`}
              aria-pressed={reason === name}
              onClick={() => setReason(name)}
            >
              {REASON_NAMES[name]} <span className="rcount">{reasons[name]}</span>
            </button>
          ))}
        </div>
      )}
      <Announce ref={announce} message={notice} />
      <Waiting load={load}>
        {() =>
          !loaded ? (
            <p className="adm-empty">טוען…</p>
          ) : loaded.count === 0 ? (
            <p className="adm-empty">{EMPTY[list]}</p>
          ) : (
            <>
              <p className="adm-count">{loaded.count === 1 ? 'מודעה אחת' : `${loaded.count} מודעות`}</p>
              {list === 'flags' ? (
                <Flags rows={loaded.cards} now={now} busy={busy} onRestore={restoreRows} />
              ) : (
                <Rows rows={loaded.cards} now={now} />
              )}
              {loaded.next < loaded.order.length && <div ref={sentinel} className="sentinel" aria-hidden="true" />}
            </>
          )
        }
      </Waiting>
    </>
  )
}

function Rows({ rows, now }: { rows: Row[]; now: Date }) {
  return (
    <ul className="arows">
      {rows.map((row) => (
        <PostRow key={row.id} row={row} now={now} />
      ))}
    </ul>
  )
}

function Flags({
  rows,
  now,
  busy,
  onRestore,
}: {
  rows: Row[]
  now: Date
  busy: boolean
  onRestore: (rows: Row[]) => void
}) {
  return (
    <>
      {flagActions(rows).map((action) => (
        <section key={action.key} className="flagaction">
          <h2>
            סימון של <bdi dir="ltr">{action.flag.by}</bdi>:{' '}
            {action.rows.length === 1 ? 'מודעה אחת' : `${action.rows.length} פרסומים של אותה מודעה`}
            <span className="flagaction-time">{when(action.flag.at, now)}</span>
          </h2>
          <button
            type="button"
            className="barbtn flagaction-restore"
            disabled={busy}
            aria-label={restoreLabel(action.rows).label}
            onClick={() => onRestore(action.rows)}
          >
            {restoreLabel(action.rows).text}
          </button>
          {action.flag.note && (
            <p className="flagaction-note" dir="auto">
              {action.flag.note}
            </p>
          )}
          <Rows rows={action.rows} now={now} />
        </section>
      ))}
    </>
  )
}
