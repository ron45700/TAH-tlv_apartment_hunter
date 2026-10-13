// Sign-in, sign-up with a key, and the password change (PHASE_3.md 3.7 (f)). Each refusal of 3.5 in
// words: a wrong username or password (one answer for both), the delay with its seconds, a disabled
// account. Sign-up has no "use my current filter" box (#336): a new user starts with #268's defaults.
// The forced change is the only screen reachable while it is due (Gate C, `Session`); the same form
// serves a change the user chooses (from the preferences page).
import { useEffect, useState, type FormEvent, type MouseEvent, type ReactNode } from 'react'
import { ApiError, api } from '../api'
import { navigate } from '../route'
import type { SessionUser } from '../types'

const MIN_PASSWORD = 8 // #262

function words(error: unknown): string {
  if (!(error instanceof ApiError)) return 'משהו השתבש. נסו שוב.'
  switch (error.refusal) {
    case 'wrong':
      return 'שם המשתמש או הסיסמה שגויים.'
    case 'disabled':
      return 'החשבון הושבת. פנו למנהל האתר.'
    case 'key_not_usable':
      return 'קוד ההזמנה לא תקף: הוא שגוי, כבר נוצל או בוטל.'
    case 'username_taken':
      return 'שם המשתמש תפוס. בחרו שם אחר.'
    case 'username_invalid':
      return 'שם המשתמש לא עומד בכללים שמתחת לשדה.'
    case 'password_too_short':
      return `הסיסמה קצרה מדי: לפחות ${MIN_PASSWORD} תווים.`
    case 'changed':
      return 'הסיסמה שונתה בינתיים. התחברו שוב.'
  }
  if (error.status === 0) return 'אין חיבור לאתר. בדקו שהוא פועל ונסו שוב.'
  return 'משהו השתבש. נסו שוב.'
}

function go(path: string) {
  return (event: MouseEvent) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
    event.preventDefault()
    navigate(path)
  }
}

function Screen({ title, lead, children }: { title: string; lead?: ReactNode; children: ReactNode }) {
  return (
    <main className="shell screen">
      <div className="formcard">
        <h1>{title}</h1>
        {lead && <p className="lead">{lead}</p>}
        {children}
      </div>
    </main>
  )
}

function TextField({
  id,
  label,
  value,
  onChange,
  autoComplete,
  type = 'text',
  hint,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  autoComplete: string
  type?: string
  hint?: string
}) {
  return (
    <div className="tfield">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={id}
        type={type}
        dir="ltr"
        value={value}
        autoComplete={autoComplete}
        autoCapitalize="none"
        spellCheck={false}
        aria-describedby={hint ? `${id}-hint` : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {hint && (
        <p className="tfield-hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
    </div>
  )
}

function Problem({ text }: { text: string | null }) {
  return (
    <p className="formerror" role="alert">
      {text}
    </p>
  )
}

/** The seconds left of a delay, counting down; 0 when there is none. */
function useCountdown(): [number, (seconds: number) => void] {
  const [until, setUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (until <= now) return
    const timer = window.setTimeout(() => setNow(Date.now()), 250)
    return () => window.clearTimeout(timer)
  }, [until, now])
  const start = (seconds: number) => {
    const at = Date.now()
    setNow(at)
    setUntil(at + seconds * 1000)
  }
  return [Math.max(0, Math.ceil((until - now) / 1000)), start]
}

export function SignIn({ onSignedIn }: { onSignedIn: (user: SessionUser) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [wait, delay] = useCountdown()

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy || wait) return
    setBusy(true)
    setProblem(null)
    try {
      const { user } = await api.signIn(username.trim(), password)
      onSignedIn(user)
    } catch (error) {
      setPassword('')
      if (error instanceof ApiError && error.refusal === 'delayed') delay(error.retryAfter ?? 30)
      else setProblem(words(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title="התחברות">
      <form onSubmit={submit} noValidate>
        <TextField id="si-user" label="שם משתמש" value={username} onChange={setUsername} autoComplete="username" />
        <TextField
          id="si-pass"
          label="סיסמה"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
        />
        <Problem text={wait ? `יותר מדי ניסיונות שגויים. אפשר לנסות שוב בעוד ${wait} שניות.` : problem} />
        <button className="mainbtn" type="submit" disabled={busy || wait > 0 || !username || !password}>
          {busy ? 'מתחבר…' : 'התחברות'}
        </button>
      </form>
      <p className="formfoot">
        אין לכם חשבון?{' '}
        <a href="/sign-up" onClick={go('/sign-up')}>
          הרשמה עם קוד הזמנה
        </a>
      </p>
    </Screen>
  )
}

export function SignUp({ onSignedIn }: { onSignedIn: (user: SessionUser) => void }) {
  const [key, setKey] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [again, setAgain] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy) return
    if (password.length < MIN_PASSWORD) return setProblem(`הסיסמה קצרה מדי: לפחות ${MIN_PASSWORD} תווים.`)
    if (password !== again) return setProblem('שתי הסיסמאות שונות זו מזו.')
    setBusy(true)
    setProblem(null)
    try {
      const { user } = await api.signUp(key.trim(), username.trim(), password)
      onSignedIn(user)
    } catch (error) {
      setProblem(words(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen title="הרשמה" lead="ההרשמה בקוד הזמנה אישי, חד-פעמי. אחרי ההרשמה בוחרים העדפות בעמוד ההעדפות.">
      <form onSubmit={submit} noValidate>
        <TextField id="su-key" label="קוד הזמנה" value={key} onChange={setKey} autoComplete="off" />
        <TextField
          id="su-user"
          label="שם משתמש"
          value={username}
          onChange={setUsername}
          autoComplete="username"
          hint="אותיות באנגלית, ספרות, וגם _ . -, בין 3 ל-32 תווים. אי אפשר לשנות אותו אחר כך."
        />
        <TextField
          id="su-pass"
          label="סיסמה"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          hint={`לפחות ${MIN_PASSWORD} תווים.`}
        />
        <TextField
          id="su-again"
          label="הסיסמה שוב"
          type="password"
          value={again}
          onChange={setAgain}
          autoComplete="new-password"
        />
        <Problem text={problem} />
        <button className="mainbtn" type="submit" disabled={busy || !key || !username || !password || !again}>
          {busy ? 'נרשם…' : 'הרשמה'}
        </button>
      </form>
      <p className="formfoot">
        כבר יש לכם חשבון?{' '}
        <a href="/sign-in" onClick={go('/sign-in')}>
          התחברות
        </a>
      </p>
    </Screen>
  )
}

export function PasswordScreen({
  forced,
  onChanged,
  onSignOut,
}: {
  forced: boolean
  onChanged: (user: SessionUser) => void
  onSignOut: () => void
}) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (busy) return
    if (next.length < MIN_PASSWORD) return setProblem(`הסיסמה החדשה קצרה מדי: לפחות ${MIN_PASSWORD} תווים.`)
    if (next !== again) return setProblem('שתי הסיסמאות החדשות שונות זו מזו.')
    setBusy(true)
    setProblem(null)
    try {
      const { user } = await api.password(current, next)
      setCurrent('')
      setNext('')
      setAgain('')
      setDone(true)
      onChanged(user)
    } catch (error) {
      const wrong = error instanceof ApiError && error.refusal === 'wrong'
      setProblem(wrong ? (forced ? 'הסיסמה הזמנית שגויה.' : 'הסיסמה הנוכחית שגויה.') : words(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen
      title={forced ? 'בחירת סיסמה חדשה' : 'שינוי סיסמה'}
      lead={forced ? 'הסיסמה שלכם אופסה. כדי להמשיך, בחרו סיסמה חדשה.' : 'אחרי השינוי, החיבורים שלכם במכשירים אחרים יסתיימו.'}
    >
      {done && !forced ? (
        <p className="formok" role="status">
          הסיסמה שונתה.
        </p>
      ) : (
        <form onSubmit={submit} noValidate>
          <TextField
            id="pw-current"
            label={forced ? 'הסיסמה הזמנית' : 'הסיסמה הנוכחית'}
            type="password"
            value={current}
            onChange={setCurrent}
            autoComplete="current-password"
          />
          <TextField
            id="pw-new"
            label="סיסמה חדשה"
            type="password"
            value={next}
            onChange={setNext}
            autoComplete="new-password"
            hint={`לפחות ${MIN_PASSWORD} תווים.`}
          />
          <TextField
            id="pw-again"
            label="הסיסמה החדשה שוב"
            type="password"
            value={again}
            onChange={setAgain}
            autoComplete="new-password"
          />
          <Problem text={problem} />
          <button className="mainbtn" type="submit" disabled={busy || !current || !next || !again}>
            {busy ? 'שומר…' : 'שמירת הסיסמה'}
          </button>
        </form>
      )}
      <p className="formfoot">
        {forced ? (
          <button type="button" className="linkbtn" onClick={onSignOut}>
            התנתק
          </button>
        ) : (
          <a href="/preferences" onClick={go('/preferences')}>
            חזרה להעדפות
          </a>
        )}
      </p>
    </Screen>
  )
}
