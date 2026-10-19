// The reports grouped by field (#173, #254, #401) and the corrections (#256, #284), as read in build
// steps 1 and 2: a post stands under every field one of its reports names, with the two derived
// marks (3.8 (c)). Correct, restore and leave out are steps 4 and 5; until then a post opens its
// detail.
import { useState } from 'react'
import { adminApi } from '../../admin/api'
import type { ReportStatus } from '../../admin/types'
import { MARK_WORDS, valueWords } from '../../admin/words'
import { israelTime } from '../../format'
import { PostRow, useLoad, Waiting, when } from './ui'

const TABS: { status: ReportStatus; label: string }[] = [
  { status: 'open', label: 'פתוחים' },
  { status: 'left_out', label: 'הושארו בחוץ' },
  { status: 'restored', label: 'שוחזרו' },
]

const EMPTY: Record<ReportStatus, string> = {
  open: 'אין דיווחים פתוחים.',
  left_out: 'אין מודעות שהושארו בחוץ.',
  restored: 'עוד לא שוחזרה מודעה שדווחה.',
}

export function Reports({ now }: { now: Date }) {
  const [status, setStatus] = useState<ReportStatus>('open')
  const [load] = useLoad((signal) => adminApi.reports(status, signal), status)
  return (
    <>
      <p className="adm-lead">
        דיווחים של משתמשים על סיווג שגוי, לפי השדה שדווח. מודעה שדווחה על כמה שדות מופיעה תחת כל אחד מהם.
      </p>
      <div className="tabs" role="tablist" aria-label="מצב הדיווח">
        {TABS.map((tab) => (
          <button
            key={tab.status}
            type="button"
            role="tab"
            aria-selected={status === tab.status}
            className={`tab${status === tab.status ? ' is-on' : ''}`}
            onClick={() => setStatus(tab.status)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <Waiting load={load}>
        {(answer) =>
          answer.groups.length === 0 ? (
            <p className="adm-empty">{EMPTY[status]}</p>
          ) : (
            <>
              <p className="adm-count">
                {answer.count === 1 ? 'דיווח אחד' : `${answer.count} דיווחים`} על{' '}
                {answer.posts === 1 ? 'מודעה אחת' : `${answer.posts} מודעות`}
              </p>
              {answer.groups.map((group) => (
                <section key={group.field} className="fieldgroup" aria-labelledby={`g-${group.field}`}>
                  <h2 id={`g-${group.field}`}>
                    {group.label} <span className="rcount">{group.posts.length}</span>
                  </h2>
                  <ul className="arows">
                    {group.posts.map((entry) =>
                      entry.post ? (
                        <PostRow key={entry.listing_id} row={entry.post} now={now}>
                          <div className="arow-extra">
                            {entry.marks.map((mark) => (
                              <p key={mark} className="apost-mark">
                                {MARK_WORDS[mark]}
                              </p>
                            ))}
                            {entry.reports.map((report) => (
                              <p key={report.report_id} className="arow-report">
                                <bdi dir="ltr">{report.reporter}</bdi>, {when(report.reported_at, now)}:{' '}
                                {report.fields.map((f) => f.label).join(', ')}
                                {report.note && (
                                  <span className="report-note" dir="auto">
                                    {report.note}
                                  </span>
                                )}
                              </p>
                            ))}
                          </div>
                        </PostRow>
                      ) : (
                        <li key={entry.listing_id} className="arow arow-gone">
                          המודעה כבר לא שמורה.
                        </li>
                      ),
                    )}
                  </ul>
                </section>
              ))}
            </>
          )
        }
      </Waiting>
    </>
  )
}

export function Corrections({ names, now }: { names: ReadonlyMap<number, string>; now: Date }) {
  const [inForce, setInForce] = useState(true)
  const [load] = useLoad((signal) => adminApi.corrections(inForce, signal), String(inForce))
  return (
    <>
      <p className="adm-lead">
        תיקון שלך גובר על תשובת המודל בכל מקום שמשתמש קורא את המודעה, עד שתסיר אותו. תשובת המודל נשמרת לידו.
      </p>
      <div className="tabs" role="tablist" aria-label="תיקונים">
        {[true, false].map((value) => (
          <button
            key={String(value)}
            type="button"
            role="tab"
            aria-selected={inForce === value}
            className={`tab${inForce === value ? ' is-on' : ''}`}
            onClick={() => setInForce(value)}
          >
            {value ? 'בתוקף' : 'הוסרו'}
          </button>
        ))}
      </div>
      <Waiting load={load}>
        {(answer) =>
          answer.corrections.length === 0 ? (
            <p className="adm-empty">{inForce ? 'אין תיקונים בתוקף.' : 'לא הוסר אף תיקון.'}</p>
          ) : (
            <ul className="arows">
              {answer.corrections.map((c) =>
                c.post ? (
                  <PostRow key={c.correction_id} row={c.post} now={now}>
                    <p className="arow-extra arow-correction">
                      <strong>{c.label}</strong>: {valueWords(c.model_value, names, c.field)} ←{' '}
                      {valueWords(c.corrected_value, names, c.field)}
                      <span className="facts-sub">
                        <bdi dir="ltr">{c.corrected_by}</bdi>, {israelTime(c.corrected_at)}
                        {c.removed_at && `, הוסר ${israelTime(c.removed_at)}`}
                      </span>
                    </p>
                  </PostRow>
                ) : (
                  <li key={c.correction_id} className="arow arow-gone">
                    המודעה כבר לא שמורה (נמחקה בשמירת הנתונים). <strong>{c.label}</strong>:{' '}
                    {valueWords(c.model_value, names, c.field)} ← {valueWords(c.corrected_value, names, c.field)}
                  </li>
                ),
              )}
            </ul>
          )
        }
      </Waiting>
    </>
  )
}
