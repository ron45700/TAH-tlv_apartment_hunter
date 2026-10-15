// The admin's opened post (3.8 (c), "Post detail"), read fresh from the store: the photos, the text
// as stored, the record (state, reason, the flag, the failures), what a restore would leave now
// (#406), the city's ruling and its source (#214, #296), the model's answer beside the value users
// see field by field (#256), the reports, the corrections, the publications and the phones.
//
// Build steps 4 and 5, the writes, each sending the `version` the page showed (#391): restore (the
// reports first, then the record, #392), leave out (#286), remove from the list (#402), retry
// (#139), correct a field from a report (#395) and remove a correction (#394). A write answers the
// post's fresh detail; "changed" reloads it and says so: nothing is retried behind the admin's back.
import { useEffect, useState } from 'react'
import { ApiError } from '../../api'
import { adminApi } from '../../admin/api'
import type { Correction, Detail } from '../../admin/types'
import { MARK_WORDS, SOURCE_WORDS, valueWords } from '../../admin/words'
import { Carousel } from '../../components/Carousel'
import { israelTime, phoneLabel } from '../../format'
import type { AreaGroup } from '../../types'
import { ReasonChip, useLoad, Waiting, when } from './ui'
import { ValueForm } from './ValueForm'

const STATUS_WORDS = { open: 'פתוח', left_out: 'הושאר בחוץ', restored: 'שוחזר' } as const

const REFUSALS: Record<string, string> = {
  changed: 'המודעה השתנתה מאז שנטענה, והדף נטען מחדש. בדקו ונסו שוב.',
  not_restorable: 'אין במודעה סימון או דיווח לשחזר.',
  no_open_report: 'אין דיווח פתוח להשאיר בחוץ.',
  not_applicable: 'המודעה כבר לא ברשימה של המשתמשים.',
  not_retryable: 'אין סיווג שנכשל לנסות שוב.',
  no_report: 'תיקון נעשה מתוך דיווח, ואין דיווח פתוח או מושאר בחוץ על המודעה.',
  not_in_force: 'התיקון כבר הוסר.',
  not_classified: 'המודעה עוד לא סווגה, אין מה לתקן.',
}

/** A field whose correction can make an active post's state wrong when removed (#394). */
const STATE_FIELDS = new Set(['post_nature', 'other_city'])

interface Props {
  id: string
  names: ReadonlyMap<number, string>
  groups: AreaGroup[]
  now: Date
}

export function AdminPost({ id, names, groups, now }: Props) {
  const [load, reload] = useLoad((signal) => adminApi.post(id, signal), id)
  return (
    <Waiting load={load}>
      {(post) => <PostDetail key={post.id} loaded={post} reload={reload} names={names} groups={groups} now={now} />}
    </Waiting>
  )
}

type Notice = { kind: 'ok' | 'error'; text: string } | null

function PostDetail({
  loaded,
  reload,
  names,
  groups,
  now,
}: {
  loaded: Detail
  reload: () => void
  names: ReadonlyMap<number, string>
  groups: AreaGroup[]
  now: Date
}) {
  const [post, setPost] = useState(loaded)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [correcting, setCorrecting] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  useEffect(() => setPost(loaded), [loaded])

  const life = post.lifecycle
  const resolvable = post.reports.filter((r) => r.status === 'open' || r.status === 'left_out')
  const open = post.reports.filter((r) => r.status === 'open')
  const restorable = life.flag !== null || resolvable.length > 0
  const reportFor = resolvable[0] ?? null
  const reported = [...new Set(resolvable.flatMap((r) => r.fields.map((f) => f.field)))]

  /** The post read again in place, so the notice of the write stays on the page. */
  const refresh = () =>
    adminApi
      .post(post.id)
      .then(setPost)
      .catch(() => reload())

  /** A write: the answer is the post's fresh detail (or none: then it is read again); "changed"
   * reads it again and says so. */
  const run = (write: () => Promise<Detail | null>, done: string, onError?: (text: string) => void) => {
    setBusy(true)
    setNotice(null)
    write()
      .then((fresh) => {
        if (fresh) setPost(fresh)
        else void refresh()
        setNotice({ kind: 'ok', text: done })
        setCorrecting(null)
      })
      .catch((error) => {
        const text = problem(error)
        if (onError && error instanceof ApiError && error.status === 422) onError(text)
        else setNotice({ kind: 'error', text })
        if (error instanceof ApiError && error.refusal === 'changed') void refresh()
      })
      .finally(() => setBusy(false))
  }

  const restore = () => {
    const after = post.restore_preview
    const question = after
      ? `לשחזר? המודעה תחזור ל"${after.reason_words ?? after.state_words}", והדיווחים יסומנו כמשוחזרים.`
      : 'לשחזר? הדיווחים יסומנו כמשוחזרים; המודעה עצמה נשארת כפי שהיא.'
    if (!window.confirm(question)) return
    run(async () => {
      const { results } = await adminApi.restore([{ listing_id: post.id, version: post.version }])
      if (results[0]?.outcome === 'changed') throw new ApiError(409, { refusal: 'changed' })
      if (results[0]?.outcome === 'not_restorable') throw new ApiError(409, { refusal: 'not_restorable' })
      return null
    }, 'המודעה שוחזרה. אם היא פעילה, היא תופיע ברשימה של המשתמשים בעוד כמה שניות.')
  }

  const leaveOut = () => {
    if (!window.confirm('להשאיר בחוץ? המודעה נשארת דחויה ונשמרת; אפשר לשחזר אותה גם אחר כך.')) return
    run(() => adminApi.leaveOut(post.id, post.version), 'המודעה הושארה בחוץ.')
  }

  const removeCorrection = (correction: Correction) => {
    const warn =
      STATE_FIELDS.has(correction.field) && life.state === 'active'
        ? ' המודעה פעילה: מצבה לא יחושב מחדש, והמשתמשים יראו שוב את תשובת המודל.'
        : ''
    if (!window.confirm(`להסיר את התיקון של "${correction.label}"?${warn}`)) return
    run(() => adminApi.removeCorrection(correction.correction_id, post.version), 'התיקון הוסר.')
  }

  const correct = (field: string, value: unknown) => {
    if (!reportFor) return
    setFormError(null)
    run(
      () => adminApi.correct(post.id, field, value, reportFor.report_id, post.version),
      'התיקון נשמר. המודעה נשארת כפי שהיא עד שתשחזרו אותה.',
      setFormError,
    )
  }

  const editing = correcting ? post.fields.find((f) => f.field === correcting) : undefined

  return (
    <div className="apost">
      <div className="apost-main">
        <section className="apanel apost-state" aria-label="מצב המודעה">
          <div className="apost-statehead">
            <ReasonChip row={life} />
            {life.reason && <span className="apost-statewords">{life.state_words}</span>}
            <a className="apost-fb" href={post.permalink} target="_blank" rel="noopener noreferrer">
              המודעה בפייסבוק
            </a>
          </div>
          <dl className="facts">
            <dt>פורסמה</dt>
            <dd>{when(post.posted_at, now)}</dd>
            <dt>פרסום אחרון</dt>
            <dd>{when(life.last_published_at, now)}</dd>
            {life.flag && (
              <>
                <dt>{life.reason === 'misclassified' ? 'דווחה על ידי' : 'סומנה על ידי'}</dt>
                <dd>
                  <bdi dir="ltr">{life.flag.by}</bdi>, {when(life.flag.at, now)}
                  {life.flag.note && (
                    <span className="facts-note" dir="auto">
                      {life.flag.note}
                    </span>
                  )}
                </dd>
              </>
            )}
            {life.failures > 0 && (
              <>
                <dt>כשלונות סיווג</dt>
                <dd>
                  {life.failures}
                  {life.last_error ? `, האחרון: ${life.last_error}` : ''}
                </dd>
              </>
            )}
            {post.city?.name && (
              <>
                <dt>עיר</dt>
                <dd>
                  {post.city.name}
                  {post.city.source && <span className="facts-sub">{SOURCE_WORDS[post.city.source]}</span>}
                </dd>
              </>
            )}
            {post.classified && (
              <>
                <dt>סווגה</dt>
                <dd>
                  גרסת הנחיות {post.classified.prompt_version}, {israelTime(post.classified.classified_at)}
                </dd>
              </>
            )}
          </dl>
          {post.restore_preview && (
            <p className="apost-preview">
              שחזור יחזיר אותה ל: <strong>{post.restore_preview.reason_words ?? post.restore_preview.state_words}</strong>
              {post.restore_preview.reason && ` (${post.restore_preview.state_words})`}
            </p>
          )}
          {post.marks.map((mark) => (
            <p key={mark} className="apost-mark">
              {MARK_WORDS[mark]}
            </p>
          ))}
          <div className="apost-actions">
            {post.marks.includes('not_removed') && (
              <button
                type="button"
                className="mainbtn"
                disabled={busy}
                onClick={() =>
                  run(() => adminApi.applyReports(post.id, post.version), 'המודעה הוסרה מהרשימה של המשתמשים.')
                }
              >
                הסרה מהרשימה
              </button>
            )}
            {restorable && (
              <button type="button" className="mainbtn" disabled={busy} onClick={restore}>
                {post.marks.includes('restore_unfinished') ? 'השלמת השחזור' : 'שחזור'}
              </button>
            )}
            {open.length > 0 && life.state !== 'active' && (
              <button type="button" className="barbtn" disabled={busy} onClick={leaveOut}>
                השארה בחוץ
              </button>
            )}
            {life.state === 'pending' && life.failures > 0 && (
              <button
                type="button"
                className="mainbtn"
                disabled={busy}
                onClick={() =>
                  run(() => adminApi.retry(post.id, post.version), 'הסיווג ינוסה שוב בהרצה הבאה של classify_pending.')
                }
              >
                ניסיון סיווג חוזר
              </button>
            )}
          </div>
          {notice && (
            <p className={notice.kind === 'ok' ? 'formok' : 'formerror'} role={notice.kind === 'ok' ? 'status' : 'alert'}>
              {notice.text}
            </p>
          )}
        </section>

        {post.reports.length > 0 && (
          <section className="apanel" aria-labelledby="reports-head">
            <h2 id="reports-head">דיווחים על סיווג שגוי</h2>
            <ul className="reports">
              {post.reports.map((report) => (
                <li key={report.report_id} className="report">
                  <p className="report-head">
                    <bdi dir="ltr">{report.reporter}</bdi>, {when(report.reported_at, now)}
                    <span className={`report-status report-${report.status}`}>{STATUS_WORDS[report.status]}</span>
                  </p>
                  <p className="report-fields">{report.fields.map((f) => f.label).join(', ')}</p>
                  {report.note && (
                    <p className="report-note" dir="auto">
                      {report.note}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {post.fields.length > 0 && (
          <section className="apanel" aria-labelledby="fields-head">
            <h2 id="fields-head">הסיווג, שדה אחרי שדה</h2>
            <p className="apanel-lead">
              {reportFor
                ? 'תשובת המודל כפי שנשמרה, ומה שהמשתמשים רואים אחרי התיקונים שלך. השדות שדווחו מסומנים; אפשר לתקן כל שדה.'
                : 'תשובת המודל כפי שנשמרה, ומה שהמשתמשים רואים אחרי התיקונים שלך. תיקון נעשה מתוך דיווח.'}
            </p>
            {editing && (
              <ValueForm
                key={editing.field}
                field={editing.field}
                label={editing.label}
                value={editing.seen}
                phones={post.phones.map((p) => p.phone)}
                groups={groups}
                names={names}
                busy={busy}
                error={formError}
                onSubmit={(value) => correct(editing.field, value)}
                onCancel={() => {
                  setCorrecting(null)
                  setFormError(null)
                }}
              />
            )}
            <div className="ftable-wrap">
              <table className="ftable">
                <thead>
                  <tr>
                    <th scope="col">שדה</th>
                    <th scope="col">המודל</th>
                    <th scope="col">מה שרואים</th>
                    {reportFor && (
                      <th scope="col">
                        <span className="sr-only">תיקון</span>
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {post.fields.map((row) => (
                    <tr
                      key={row.field}
                      className={[row.corrected ? 'is-corrected' : '', reported.includes(row.field) ? 'is-reported' : '']
                        .join(' ')
                        .trim() || undefined}
                    >
                      <th scope="row">
                        {row.label}
                        {reported.includes(row.field) && <span className="tag tag-reported">דווח</span>}
                      </th>
                      <td dir="auto">{valueWords(row.model, names, row.field)}</td>
                      <td dir="auto">
                        {row.corrected ? (
                          <>
                            {valueWords(row.seen, names, row.field)} <span className="tag">תוקן ביד</span>
                          </>
                        ) : (
                          <span className="same">כמו המודל</span>
                        )}
                      </td>
                      {reportFor && (
                        <td>
                          <button
                            type="button"
                            className="linkbtn"
                            aria-label={`תיקון ${row.label}`}
                            disabled={busy}
                            onClick={() => {
                              setFormError(null)
                              setCorrecting(row.field)
                            }}
                          >
                            תיקון
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {post.corrections.length > 0 && (
          <section className="apanel" aria-labelledby="corr-head">
            <h2 id="corr-head">תיקונים</h2>
            <ul className="corrlist">
              {post.corrections.map((c) => (
                <li key={c.correction_id} className={c.removed_at ? 'is-removed' : undefined}>
                  <span className="corr-text">
                    <strong>{c.label}</strong>: {valueWords(c.model_value, names, c.field)} ←{' '}
                    {valueWords(c.corrected_value, names, c.field)}
                  </span>
                  <span className="facts-sub">
                    {c.removed_at ? `הוסר ${israelTime(c.removed_at)}` : `בתוקף מ־${israelTime(c.corrected_at)}`}
                  </span>
                  {!c.removed_at && (
                    <button
                      type="button"
                      className="linkbtn danger"
                      aria-label={`הסרת התיקון של ${c.label}`}
                      disabled={busy}
                      onClick={() => removeCorrection(c)}
                    >
                      הסרה
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="apanel" aria-labelledby="text-head">
          <h2 id="text-head">הטקסט</h2>
          <p className="apost-text" dir="auto">
            {post.text?.trim() || 'אין טקסט'}
          </p>
        </section>
      </div>

      <aside className="apost-side">
        <div className="apanel apost-photos">
          <Carousel photos={post.photos} videos={post.videos} variant="open" eager />
        </div>
        {post.phones.length > 0 && (
          <section className="apanel" aria-labelledby="phones-head">
            <h2 id="phones-head">טלפונים</h2>
            <ul className="plainlist">
              {post.phones.map((p) => (
                <li key={p.phone} dir="auto">
                  {phoneLabel(p.phone, p.name)}
                </li>
              ))}
            </ul>
          </section>
        )}
        <section className="apanel" aria-labelledby="pubs-head">
          <h2 id="pubs-head">{post.publications.length === 1 ? 'פרסום אחד' : `${post.publications.length} פרסומים`}</h2>
          <ul className="plainlist">
            {post.publications.map((p) => (
              <li key={p.id}>
                {israelTime(p.posted_at)}
                {p.id === post.id && <span className="facts-sub">המודעה הזו</span>}
              </li>
            ))}
          </ul>
        </section>
        {life.image_errors.length > 0 && <p className="apanel-lead">{life.image_errors.length} תמונות לא ירדו.</p>}
      </aside>
    </div>
  )
}

function problem(error: unknown): string {
  if (error instanceof ApiError && error.refusal === 'invalid_value') {
    const detail = typeof error.detail === 'string' ? error.detail : ''
    return `הערך לא תקין${detail ? `: ${detail}` : '.'}`
  }
  if (error instanceof ApiError && error.refusal) return REFUSALS[error.refusal] ?? 'הפעולה נדחתה.'
  return 'הפעולה לא נשמרה. בדקו את החיבור ונסו שוב.'
}
