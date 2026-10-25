// The schedule (Phase 5, PHASE_5.md points 8 and 11; DECISIONS.md #61, #471): the interval and the
// quiet hours, "run now", what runs and what ran. The site has no Apify key: it only writes the
// settings and the request; the scheduler reads them every few seconds and starts the runs.
// Yad2 (PHASE_6.md §6.7; #515, #527-#529): its own interval and daytime hours, off until saved on.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../../api'
import { adminApi } from '../../admin/api'
import type { RunRow, ScheduleAnswer } from '../../admin/types'
import { israelTime, relativeTime } from '../../format'
import { Announce, useLoad, Waiting, type Message } from './ui'

const REFRESH_MS = 15000

const REFUSALS: Record<string, string> = {
  changed: 'ההגדרות השתנו בינתיים. רעננו את הדף ונסו שוב.',
  invalid_schedule: 'המרווח הוא בין 5 ל-1440 דקות, והשעות בצורה שעה:דקות. ביד2 שעת ההתחלה לפני שעת הסיום.',
  run_in_progress: 'ריצה כבר רצה עכשיו. אפשר לבקש עוד אחת כשהיא תסתיים.',
  already_asked: 'כבר ביקשת ריצה. המתזמן יתחיל אותה בתוך שניות.',
}

const STATUS: Record<RunRow['status'], string> = { running: 'רצה', succeeded: 'הצליחה', failed: 'נכשלה' }
const TRIGGER: Record<RunRow['trigger'], string> = { scheduled: 'מתוזמנת', manual: 'ידנית' }
const SOURCE: Record<RunRow['source'], string> = { facebook: 'פייסבוק', yad2: 'יד2' }

function problem(error: unknown): string {
  if (error instanceof ApiError && error.refusal) return REFUSALS[error.refusal] ?? 'הפעולה נדחתה.'
  return 'הפעולה לא נשמרה. בדקו את החיבור ונסו שוב.'
}

export function Schedule({ now }: { now: Date }) {
  const [tick, setTick] = useState(0)
  const [load, reload] = useLoad((signal) => adminApi.schedule(signal), `schedule:${tick}`)
  useEffect(() => {
    const timer = window.setInterval(() => setTick((n) => n + 1), REFRESH_MS)
    return () => window.clearInterval(timer)
  }, [])
  return <Waiting load={load}>{(answer) => <Desk answer={answer} now={now} reload={reload} />}</Waiting>
}

function Desk({ answer, now, reload }: { answer: ScheduleAnswer; now: Date; reload: () => void }) {
  const [interval, setIntervalMinutes] = useState(String(answer.interval_minutes))
  const [from, setFrom] = useState(answer.quiet_from)
  const [until, setUntil] = useState(answer.quiet_until)
  const yad2Shown = answer.yad2 ?? answer.yad2_defaults
  const [yad2On, setYad2On] = useState(answer.yad2 !== null)
  const [yad2Interval, setYad2Interval] = useState(String(yad2Shown.interval_minutes))
  const [yad2From, setYad2From] = useState(yad2Shown.hours_from)
  const [yad2Until, setYad2Until] = useState(yad2Shown.hours_until)
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [message, setMessage] = useState<Message | null>(null)
  const box = useRef<HTMLDivElement>(null)

  // A save elsewhere (another tab) brings the stored values back into the form.
  useEffect(() => {
    setIntervalMinutes(String(answer.interval_minutes))
    setFrom(answer.quiet_from)
    setUntil(answer.quiet_until)
    setYad2On(answer.yad2 !== null)
    setYad2Interval(String(yad2Shown.interval_minutes))
    setYad2From(yad2Shown.hours_from)
    setYad2Until(yad2Shown.hours_until)
  }, [answer.version]) // the stored values follow the version only

  const yad2Changed =
    yad2On !== (answer.yad2 !== null) ||
    (yad2On &&
      (yad2Interval !== String(yad2Shown.interval_minutes) ||
        yad2From !== yad2Shown.hours_from ||
        yad2Until !== yad2Shown.hours_until))
  const changed =
    interval !== String(answer.interval_minutes) ||
    from !== answer.quiet_from ||
    until !== answer.quiet_until ||
    yad2Changed

  const save = (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    adminApi
      .saveSchedule({
        interval_minutes: Number(interval),
        quiet_from: from,
        quiet_until: until,
        yad2_interval_minutes: yad2On ? Number(yad2Interval) : null,
        yad2_hours_from: yad2On ? yad2From : null,
        yad2_hours_until: yad2On ? yad2Until : null,
        version: answer.version,
      })
      .then(() => {
        setMessage({ ok: true, text: 'נשמר. המתזמן עובד לפי ההגדרות החדשות מהבדיקה הבאה שלו, בתוך שניות.' })
        reload()
      })
      .catch((error) => setMessage({ ok: false, text: problem(error) }))
      .finally(() => setBusy(false))
  }

  const runNow = () => {
    setBusy(true)
    setMessage(null)
    adminApi
      .runNow()
      .then(() => {
        setMessage({ ok: true, text: 'הבקשה נשלחה. המתזמן יתחיל ריצה בתוך שניות.' })
        setConfirming(false)
        reload()
      })
      .catch((error) => {
        setMessage({ ok: false, text: problem(error) })
        setConfirming(false)
      })
      .finally(() => {
        setBusy(false)
        box.current?.focus()
      })
  }

  const blocked = answer.running !== null || answer.run_now_waiting
  return (
    <>
      <p className="adm-lead">
        המתזמן מריץ איסוף ואחריו סיווג פעם בכל מרווח, מתחילת הריצה הקודמת, ולא מתחיל ריצה בשעות השקטות (שעון ישראל).
        ריצה ידנית מותרת גם בשעות השקטות. ליד2 מרווח ושעות משלו. אף פעם לא רצות שתי ריצות יחד, וכששתיהן
        בזמן, פייסבוק קודם.
      </p>
      <section className="apanel" aria-labelledby="sched-now">
        <h2 id="sched-now">עכשיו</h2>
        {answer.running ? (
          <p>
            ריצה {TRIGGER[answer.running.trigger]} רצה עכשיו, התחילה {relativeTime(answer.running.started_at, now)} (
            {israelTime(answer.running.started_at)}).
          </p>
        ) : answer.next_run ? (
          <p>
            הריצה הבאה: {israelTime(answer.next_run)}
            {answer.in_quiet_hours && ' (עכשיו שעות שקטות)'}.
          </p>
        ) : null}
        {!answer.running && answer.yad2_next_run && <p>ריצת יד2 הבאה: {israelTime(answer.yad2_next_run)}.</p>}
        {answer.run_now_waiting && <p>ריצה ידנית מחכה למתזמן ותתחיל בתוך שניות.</p>}
        {confirming ? (
          <div className="issue-row">
            <span>ריצה עולה כשניים-שלושה סנט (Apify ו-OpenAI). להריץ עכשיו?</span>
            <button type="button" className="mainbtn" onClick={runNow} disabled={busy}>
              כן, להריץ
            </button>
            <button type="button" className="linkbtn" onClick={() => setConfirming(false)} disabled={busy}>
              ביטול
            </button>
          </div>
        ) : (
          <>
            <button
              type="button"
              className="barbtn"
              onClick={() => setConfirming(true)}
              disabled={busy || blocked}
              aria-describedby={blocked ? 'sched-blocked' : undefined}
            >
              הרצה עכשיו
            </button>
            {blocked && (
              <p id="sched-blocked" className="facts-sub">
                {answer.running
                  ? 'ריצה רצה עכשיו. אפשר להפעיל שוב כשהיא תסתיים.'
                  : 'ריצה ידנית כבר מחכה למתזמן. אפשר להפעיל שוב כשהיא תסתיים.'}
              </p>
            )}
          </>
        )}
      </section>
      <form className="apanel schedform" onSubmit={save} aria-labelledby="sched-settings">
        <h2 id="sched-settings">הגדרות</h2>
        {!answer.stored && <p className="facts-sub">המתזמן עוד לא שמר הגדרות: אלה ברירות המחדל שלו.</p>}
        <label htmlFor="sched-interval">מרווח בין ריצות (דקות, 5 עד 1440)</label>
        <input
          id="sched-interval"
          type="number"
          inputMode="numeric"
          min={5}
          max={1440}
          value={interval}
          onChange={(event) => setIntervalMinutes(event.target.value)}
          required
        />
        <label htmlFor="sched-from">שעות שקטות: מ-</label>
        <input id="sched-from" type="time" value={from} onChange={(event) => setFrom(event.target.value)} required />
        <label htmlFor="sched-until">עד</label>
        <input id="sched-until" type="time" value={until} onChange={(event) => setUntil(event.target.value)} required />
        <p className="facts-sub">אותה שעה בשני השדות: בלי שעות שקטות.</p>
        <fieldset className="schedform-yad2">
          <legend>יד2</legend>
          <label className="checkrow">
            <input type="checkbox" checked={yad2On} onChange={(event) => setYad2On(event.target.checked)} />
            איסוף מיד2 פעיל
          </label>
          {yad2On && (
            <>
              <label htmlFor="sched-yad2-interval">מרווח בין ריצות יד2 (דקות, 5 עד 1440)</label>
              <input
                id="sched-yad2-interval"
                type="number"
                inputMode="numeric"
                min={5}
                max={1440}
                value={yad2Interval}
                onChange={(event) => setYad2Interval(event.target.value)}
                required
              />
              <label htmlFor="sched-yad2-from">ריצות יד2 מתחילות מ-</label>
              <input
                id="sched-yad2-from"
                type="time"
                value={yad2From}
                onChange={(event) => setYad2From(event.target.value)}
                required
              />
              <label htmlFor="sched-yad2-until">ועד לפני</label>
              <input
                id="sched-yad2-until"
                type="time"
                value={yad2Until}
                onChange={(event) => setYad2Until(event.target.value)}
                required
              />
              <p className="facts-sub">שעון ישראל, בתוך היום. השעות השקטות של פייסבוק לא חלות על יד2.</p>
            </>
          )}
        </fieldset>
        <button type="submit" className="mainbtn" disabled={busy || !changed}>
          שמירה
        </button>
        {answer.updated_at && (
          <p className="facts-sub">
            נשמר לאחרונה {israelTime(answer.updated_at)}
            {answer.updated_by && (
              <>
                {' '}
                על ידי <bdi dir="ltr">{answer.updated_by}</bdi>
              </>
            )}
          </p>
        )}
      </form>
      <Announce ref={box} message={message} />
      <h2 className="sched-runs">הריצות האחרונות</h2>
      {answer.runs.length === 0 ? (
        <p className="adm-empty">עוד לא נרשמה ריצה.</p>
      ) : (
        <div className="ftable-wrap">
          <table className="ftable">
            <thead>
              <tr>
                <th scope="col">התחילה</th>
                <th scope="col">מקור</th>
                <th scope="col">סוג</th>
                <th scope="col">מצב</th>
                <th scope="col">שורות</th>
                <th scope="col">עלות Apify</th>
              </tr>
            </thead>
            <tbody>
              {answer.runs.map((run) => (
                <tr key={run.run_id}>
                  <th scope="row">{israelTime(run.started_at)}</th>
                  <td>{SOURCE[run.source]}</td>
                  <td>{TRIGGER[run.trigger]}</td>
                  <td>
                    {STATUS[run.status]}
                    {run.failure_kind && (
                      <span className="facts-sub" dir="ltr">
                        {run.failure_kind}
                      </span>
                    )}
                  </td>
                  <td>{run.rows_fetched ?? '—'}</td>
                  <td>
                    {run.source === 'yad2'
                      ? '—'
                      : run.cost_usd === null
                        ? 'עוד לא סופית'
                        : `$${run.cost_usd.toFixed(4)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
