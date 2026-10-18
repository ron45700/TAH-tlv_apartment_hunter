// Linking Telegram from the preferences page (PHASE_4.md 4.4, point 5 A; DECISIONS.md #453). The
// page asks the server for a one-time code and shows it once: as a link that opens the bot with the
// code (t.me), and by itself to type to the bot. The code is valid for 15 minutes; while it is shown
// the page asks every few seconds whether the bot has linked the account. Unlinking stops the alerts.
// The link is a plain navigation the user makes: the page itself fetches nothing but the site.
import { useEffect, useState } from 'react'
import { ApiError, api } from '../api'
import { israelTime } from '../format'
import type { TelegramCode, TelegramState } from '../types'

const POLL_MS = 4000

type View =
  | { state: 'loading' }
  | { state: 'failed' }
  | { state: 'linked'; since: string }
  | { state: 'unlinked' }
  | { state: 'code'; code: TelegramCode }

function viewOf(found: TelegramState): View {
  return found.linked && found.linked_at ? { state: 'linked', since: found.linked_at } : { state: 'unlinked' }
}

export function TelegramLink() {
  const [view, setView] = useState<View>({ state: 'loading' })
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  useEffect(() => {
    api
      .telegram()
      .then((found) => setView(viewOf(found)))
      .catch(() => setView({ state: 'failed' }))
  }, [])

  // While a code is shown: has the bot linked the account yet? Stops when the code expires.
  useEffect(() => {
    if (view.state !== 'code') return
    const expires = new Date(view.code.expires_at).getTime()
    const timer = window.setInterval(() => {
      if (Date.now() > expires) {
        window.clearInterval(timer)
        setView({ state: 'unlinked' })
        setProblem('הקוד פג. צרו קוד חדש.')
        return
      }
      api
        .telegram()
        .then((found) => {
          if (found.linked) setView(viewOf(found))
        })
        .catch(() => undefined)
    }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [view])

  const makeCode = async () => {
    setBusy(true)
    setProblem(null)
    try {
      setView({ state: 'code', code: await api.telegramLink() })
    } catch (error) {
      setProblem(error instanceof ApiError && error.status === 401 ? 'יש להתחבר מחדש.' : 'הקוד לא נוצר. נסו שוב.')
    } finally {
      setBusy(false)
    }
  }

  const unlink = async () => {
    setBusy(true)
    setProblem(null)
    try {
      setView(viewOf(await api.telegramUnlink()))
    } catch {
      setProblem('הקישור לא בוטל. נסו שוב.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="pcard telegram" aria-labelledby="telegram-title">
      <h2 id="telegram-title">התראות בטלגרם</h2>
      {view.state === 'loading' && <p className="pline">טוען…</p>}
      {view.state === 'failed' && <p className="pline">מצב הקישור לא נטען.</p>}
      {view.state === 'linked' && (
        <>
          <p className="pline">
            מקושר מאז {israelTime(view.since)}. התראה על כל מודעה חדשה שמתאימה להעדפות תגיע לטלגרם.
          </p>
          <button type="button" className="barbtn" disabled={busy} onClick={unlink}>
            ביטול הקישור
          </button>
        </>
      )}
      {view.state === 'unlinked' && (
        <>
          <p className="pline">קבלו התראה בטלגרם על כל מודעה חדשה שמתאימה להעדפות.</p>
          <button type="button" className="mainbtn" disabled={busy} onClick={makeCode}>
            קישור לטלגרם
          </button>
        </>
      )}
      {view.state === 'code' && (
        <>
          <a className="mainbtn tg-open" href={view.code.link} target="_blank" rel="noopener noreferrer">
            פתיחת הבוט בטלגרם
          </a>
          <p className="pline">בטלגרם לוחצים "התחל" (Start). אפשר גם לשלוח לבוט את הקוד:</p>
          <p className="tg-code" dir="ltr">
            <code>{view.code.code}</code>
          </p>
          <p className="pline" role="status">
            הקוד בתוקף 15 דקות. הדף יתעדכן כשהקישור יושלם.
          </p>
        </>
      )}
      {problem && (
        <p className="savestate is-failed" role="alert">
          {problem}
        </p>
      )}
    </section>
  )
}
