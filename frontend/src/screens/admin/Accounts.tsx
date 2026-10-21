// Keys ("קודי הזמנה", the sign-up form's own word) and users (3.8 (c); build step 3): issue a key with a label and see it once (#266), cancel an
// unused one (#243); reset a user's password to a temporary one (#262, #263), disable and enable a
// user (#265). The admin's own row takes none of them (R8). Written to the store the site serves
// (3.9, #424 point 88).
import { useState, type FormEvent } from 'react'
import { ApiError } from '../../api'
import { adminApi } from '../../admin/api'
import type { AdminUser, Key } from '../../admin/types'
import { israelTime } from '../../format'
import { Announce, useLoad, Waiting } from './ui'

const REFUSALS: Record<string, string> = {
  label_empty: 'כתבו למי הקוד, כדי לזהות אותו ברשימה.',
  key_used: 'הקוד כבר שימש לפתיחת חשבון, ואי אפשר לבטל אותו.',
  unknown_key: 'הקוד לא נמצא. רעננו את הדף.',
  password_too_short: 'סיסמה זמנית צריכה לפחות 8 תווים.',
  admin_row: 'את הסיסמה שלך מחליפים בדף ההעדפות.',
  admin_cannot_be_disabled: 'אי אפשר להשבית את חשבון המנהל.',
  unknown_user: 'המשתמש לא נמצא. רעננו את הדף.',
  changed: 'הרשומה השתנתה בינתיים. רעננו את הדף ונסו שוב.',
}

function problem(error: unknown): string {
  if (error instanceof ApiError && error.refusal) return REFUSALS[error.refusal] ?? 'הפעולה נדחתה.'
  if (error instanceof ApiError && error.status === 422) return 'הערך לא תקין.'
  return 'הפעולה לא נשמרה. בדקו את החיבור ונסו שוב.'
}

const KEY_STATE: Record<Key['state'], string> = { usable: 'פנוי', used: 'שומש', cancelled: 'בוטל' }

export function Keys({ onChanged }: { onChanged: () => void }) {
  const [load, reload] = useLoad(() => adminApi.keys(), 'keys')
  const [label, setLabel] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [issued, setIssued] = useState<{ label: string; key: string } | null>(null)
  const [copied, setCopied] = useState(false)

  const issue = (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    adminApi
      .issueKey(label)
      .then((answer) => {
        setIssued({ label: answer.label, key: answer.key })
        setCopied(false)
        setLabel('')
        reload()
        onChanged()
      })
      .catch((e) => setError(problem(e)))
      .finally(() => setBusy(false))
  }

  const cancel = (key: Key) => {
    if (!window.confirm(`לבטל את קוד ההזמנה "${key.label}"? קוד שבוטל לא חוזר.`)) return
    setError(null)
    adminApi
      .cancelKey(key.key_id)
      .then(() => {
        reload()
        onChanged()
      })
      .catch((e) => setError(problem(e)))
  }

  const copy = () => {
    if (!issued || !navigator.clipboard) return
    navigator.clipboard
      .writeText(issued.key)
      .then(() => setCopied(true))
      .catch(() => setCopied(false))
  }

  return (
    <>
      <p className="adm-lead">
        קוד הזמנה פותח חשבון אחד. כתבו למי הוא, צרו אותו ושלחו אותו. הקוד מוצג פעם אחת בלבד: האתר שומר רק טביעה שלו.
      </p>
      <form className="apanel issue" onSubmit={issue}>
        <label htmlFor="key-label">למי הקוד</label>
        <div className="issue-row">
          <input
            id="key-label"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="למשל: דנה, השותפה של נועה"
            maxLength={80}
            autoComplete="off"
          />
          <button type="submit" className="mainbtn" disabled={busy || !label.trim()}>
            יצירת קוד הזמנה
          </button>
        </div>
        <p className="formerror" role="alert">
          {error}
        </p>
      </form>
      {issued && (
        <section className="keyonce" aria-labelledby="key-once">
          <h2 id="key-once">קוד ההזמנה של {issued.label}</h2>
          <p>העתיקו אותו עכשיו. אחרי שתעזבו את הדף אי אפשר לראות אותו שוב.</p>
          <div className="keyonce-row">
            <code dir="ltr">{issued.key}</code>
            <button type="button" className="barbtn" onClick={copy}>
              {copied ? 'הועתק' : 'העתקה'}
            </button>
          </div>
          <p className="facts-sub">ההרשמה: בדף "הירשם", בשדה "קוד הזמנה".</p>
        </section>
      )}
      <Waiting load={load}>
        {({ keys }) =>
          keys.length === 0 ? (
            <p className="adm-empty">עוד לא נוצר קוד הזמנה.</p>
          ) : (
            <div className="ftable-wrap">
              <table className="ftable">
                <thead>
                  <tr>
                    <th scope="col">למי</th>
                    <th scope="col">מצב</th>
                    <th scope="col">נוצר</th>
                    <th scope="col">
                      <span className="sr-only">פעולה</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => (
                    <tr key={key.key_id}>
                      <th scope="row">{key.label}</th>
                      <td>
                        <span className={`kstate kstate-${key.state}`}>{KEY_STATE[key.state]}</span>
                        {key.used_by && (
                          <span className="facts-sub">
                            <bdi dir="ltr">{key.used_by}</bdi>
                            {key.used_at && `, ${israelTime(key.used_at)}`}
                          </span>
                        )}
                        {key.cancelled_at && <span className="facts-sub">{israelTime(key.cancelled_at)}</span>}
                      </td>
                      <td>{israelTime(key.created_at)}</td>
                      <td>
                        {key.state === 'usable' && (
                          <button
                            type="button"
                            className="linkbtn danger"
                            aria-label={`ביטול קוד ההזמנה של ${key.label}`}
                            onClick={() => cancel(key)}
                          >
                            ביטול
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Waiting>
    </>
  )
}

export function Users({ onChanged }: { onChanged: () => void }) {
  const [load, reload] = useLoad(() => adminApi.users(), 'users')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [resetting, setResetting] = useState<string | null>(null)

  const run = (action: () => Promise<AdminUser>, done: string) => {
    setError(null)
    setNotice(null)
    action()
      .then(() => {
        setNotice(done)
        reload()
        onChanged()
      })
      .catch((e) => setError(problem(e)))
  }

  return (
    <>
      <p className="adm-lead">
        משתמשים לא נמחקים. השבתה מנתקת את החשבון מכל המכשירים ושומרת את ההעדפות. איפוס נותן סיסמה זמנית, שתוחלף בכניסה
        הבאה.
      </p>
      <Announce message={error ? { ok: false, text: error } : notice ? { ok: true, text: notice } : null} />
      <Waiting load={load}>
        {({ users }) => (
          <ul className="ulist">
            {users.map((user) => (
              <li key={user.username} className={`urow${user.disabled_at ? ' is-disabled' : ''}`}>
                <div className="urow-who">
                  <span className="urow-name" dir="ltr">
                    {user.username}
                  </span>
                  {user.is_admin && <span className="tag">מנהל</span>}
                  {user.disabled_at && <span className="kstate kstate-cancelled">מושבת</span>}
                  {user.must_change_password && <span className="kstate kstate-used">צריך להחליף סיסמה</span>}
                </div>
                <p className="urow-facts">
                  החשבון נוצר {israelTime(user.created_at)}
                  {user.key_label && `, בקוד ההזמנה "${user.key_label}"`}
                  {user.failed_sign_ins > 0 && `, ${user.failed_sign_ins} כניסות שנכשלו ברצף`}
                </p>
                {!user.is_admin && (
                  <div className="urow-actions">
                    <button
                      type="button"
                      className="barbtn"
                      aria-expanded={resetting === user.username}
                      aria-label={`איפוס סיסמה ל־${user.username}`}
                      onClick={() => setResetting(resetting === user.username ? null : user.username)}
                    >
                      איפוס סיסמה
                    </button>
                    {user.disabled_at ? (
                      <button
                        type="button"
                        className="barbtn"
                        aria-label={`הפעלה של ${user.username}`}
                        onClick={() => run(() => adminApi.enable(user.username), `החשבון של ${user.username} פעיל שוב.`)}
                      >
                        הפעלה
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="barbtn danger"
                        aria-label={`השבתה של ${user.username}`}
                        onClick={() =>
                          window.confirm(`להשבית את ${user.username}? כל החיבורים של החשבון יתנתקו.`) &&
                          run(() => adminApi.disable(user.username), `החשבון של ${user.username} הושבת.`)
                        }
                      >
                        השבתה
                      </button>
                    )}
                  </div>
                )}
                {resetting === user.username && (
                  <ResetForm
                    username={user.username}
                    onCancel={() => setResetting(null)}
                    onDone={() => {
                      setResetting(null)
                      setNotice(
                        `הסיסמה של ${user.username} אופסה. מסרו את הסיסמה הזמנית; בכניסה הבאה תתבקש בחירת סיסמה חדשה.`,
                      )
                      reload()
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </Waiting>
    </>
  )
}

function ResetForm({ username, onCancel, onDone }: { username: string; onCancel: () => void; onDone: () => void }) {
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submit = (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    adminApi
      .resetPassword(username, password)
      .then(onDone)
      .catch((e) => setError(problem(e)))
      .finally(() => setBusy(false))
  }
  const id = `temp-${username}`
  return (
    <form className="resetform" onSubmit={submit}>
      <label htmlFor={id}>סיסמה זמנית ל־{username}</label>
      <div className="issue-row">
        <input
          id={id}
          type="text"
          dir="ltr"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          autoComplete="off"
        />
        <button type="submit" className="mainbtn" disabled={busy || password.length < 8}>
          איפוס
        </button>
        <button type="button" className="linkbtn" onClick={onCancel}>
          ביטול
        </button>
      </div>
      <p className="tfield-hint">לפחות 8 תווים. כל החיבורים של החשבון יתנתקו.</p>
      <p className="formerror" role="alert">
        {error}
      </p>
    </form>
  )
}
