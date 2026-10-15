// The admin's opened post (3.8 (c), "Post detail"), read fresh from the store: the photos, the text
// as stored, the record (state, reason, the flag, the failures), what a restore would leave now
// (#406), the city's ruling and its source (#214, #296), the model's answer beside the value users
// see field by field (#256), the reports, the corrections, the publications and the phones. Build
// steps 1 and 2 read only: the restore, the leave-out and the corrections are steps 4 and 5.
import { adminApi } from '../../admin/api'
import type { Detail } from '../../admin/types'
import { MARK_WORDS, SOURCE_WORDS, valueWords } from '../../admin/words'
import { Carousel } from '../../components/Carousel'
import { israelTime, phoneLabel } from '../../format'
import { ReasonChip, useLoad, Waiting, when } from './ui'

const STATUS_WORDS = { open: 'פתוח', left_out: 'הושאר בחוץ', restored: 'שוחזר' } as const

interface Props {
  id: string
  names: ReadonlyMap<number, string>
  now: Date
}

export function AdminPost({ id, names, now }: Props) {
  const [load] = useLoad((signal) => adminApi.post(id, signal), id)
  return <Waiting load={load}>{(post) => <PostDetail post={post} names={names} now={now} />}</Waiting>
}

function PostDetail({ post, names, now }: { post: Detail; names: ReadonlyMap<number, string>; now: Date }) {
  const life = post.lifecycle
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
                <dt>סומנה על ידי</dt>
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
        </section>

        <section className="apanel" aria-labelledby="text-head">
          <h2 id="text-head">הטקסט</h2>
          <p className="apost-text" dir="auto">
            {post.text?.trim() || 'אין טקסט'}
          </p>
        </section>

        {post.fields.length > 0 && (
          <section className="apanel" aria-labelledby="fields-head">
            <h2 id="fields-head">הסיווג, שדה אחרי שדה</h2>
            <p className="apanel-lead">תשובת המודל כפי שנשמרה, ומה שהמשתמשים רואים אחרי התיקונים שלך.</p>
            <div className="ftable-wrap">
              <table className="ftable">
                <thead>
                  <tr>
                    <th scope="col">שדה</th>
                    <th scope="col">המודל</th>
                    <th scope="col">מה שרואים</th>
                  </tr>
                </thead>
                <tbody>
                  {post.fields.map((row) => (
                    <tr key={row.field} className={row.corrected ? 'is-corrected' : undefined}>
                      <th scope="row">{row.label}</th>
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

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

        {post.corrections.length > 0 && (
          <section className="apanel" aria-labelledby="corr-head">
            <h2 id="corr-head">תיקונים</h2>
            <ul className="corrlist">
              {post.corrections.map((c) => (
                <li key={c.correction_id} className={c.removed_at ? 'is-removed' : undefined}>
                  <strong>{c.label}</strong>: {valueWords(c.model_value, names, c.field)} ←{' '}
                  {valueWords(c.corrected_value, names, c.field)}
                  <span className="facts-sub">
                    {c.removed_at ? `הוסר ${israelTime(c.removed_at)}` : `בתוקף מ־${israelTime(c.corrected_at)}`}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
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
