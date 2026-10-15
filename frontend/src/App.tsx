// The site (PHASE_3.md 3.7 (f)): the list (home) with the filter bar, the opened post, and the
// screens of build step 5: sign-in, sign-up with a key, the forced password change and the
// preferences page. A grid of cards on a desktop and a tablet, one card under the other on a phone
// (#303), in one centred column that grows with the screen (#347).
//
// The bar (3.7 (e)(ii)): for a signed-in user it opens on the saved preferences, for a guest empty
// (#315, #335); a change is temporary and "ההעדפות שלי" resets it. It lives in the tab's memory and
// `sessionStorage` (#330 point 14): a reload keeps a changed bar, a new visit starts again. It is sent
// with each list request and never saved (#335): preferences are saved on the preferences page only.
//
// Build step 6 (3.7 (i)), signed-in only: viewed cards are dimmed and listed after the unviewed (the
// server's order, #62); an opened post marks its card viewed at once, and the order follows on the
// next load of the list, so nothing jumps under the reader. A "lied" flag asks first; a flag or a
// report says in words what it did (a partial flag offers a retry, #330 point 21) and the list
// reloads, so the card leaves it. A write on a post removed meanwhile (409) says so and reloads.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, api } from './api'
import { barHeldCount, barOf, emptyBar, israelToday, refusalWords, sameBar, type Bar } from './bar'
import { ConfirmFlag, NoticeBar, type Notice } from './components/actions'
import { Card, type CardActions } from './components/Card'
import { FilterBar, type BarStanding } from './components/FilterBar'
import { Header } from './components/Header'
import { PostView, type PostActions } from './components/PostView'
import { navigate, postPath, useRoute } from './route'
import { PasswordScreen, SignIn, SignUp } from './screens/Account'
import { Preferences } from './screens/Preferences'
import type { CardsResponse, FlagAnswer, Reference, SessionUser } from './types'

const PHONE = '(max-width: 699.98px)'
const BAR_KEY = 'tlv.bar'

/** The bar kept for this tab, if it belongs to the same viewer (a username, or a guest). */
function storedBar(owner: string | null): Bar | null {
  try {
    const raw = sessionStorage.getItem(BAR_KEY)
    if (!raw) return null
    const kept = JSON.parse(raw) as { owner: string | null; bar: Bar }
    return kept.owner === owner && kept.bar ? kept.bar : null
  } catch {
    return null
  }
}

function keepBar(owner: string | null, bar: Bar): void {
  try {
    sessionStorage.setItem(BAR_KEY, JSON.stringify({ owner, bar }))
  } catch {
    // a browser that keeps nothing: the bar lives in the tab's memory only
  }
}

function forgetBar(): void {
  try {
    sessionStorage.removeItem(BAR_KEY)
  } catch {
    // nothing kept
  }
}

export function App() {
  const route = useRoute()
  const [user, setUser] = useState<SessionUser | null | undefined>(undefined)
  const [reference, setReference] = useState<Reference | null>(null)
  const [saved, setSaved] = useState<Bar | null>(null)
  const [bar, setBar] = useState<Bar | null>(null)
  const [list, setList] = useState<CardsResponse | null>(null)
  const [failed, setFailed] = useState(false)
  const [barProblem, setBarProblem] = useState<string | null>(null)
  const [reloads, setReloads] = useState(0)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [flagging, setFlagging] = useState<string | null>(null)
  const [flagBusy, setFlagBusy] = useState(false)
  const [reportFor, setReportFor] = useState<string | null>(null)
  const now = useNow()
  const phone = useMedia(PHONE)
  const openedFromList = useRef(false)
  const returnFocusTo = useRef<string | null>(null)
  const today = israelToday(now)

  useEffect(() => {
    api
      .session()
      .then((answer) => setUser(answer.user))
      .catch(() => setUser(null))
    api
      .reference()
      .then(setReference)
      .catch(() => setFailed(true))
  }, [])

  // The saved preferences of a signed-in user, and where the bar starts.
  const owner = user ? user.username : null
  useEffect(() => {
    if (user === undefined) return
    if (user === null || user.must_change_password) {
      setSaved(null)
      setBar(storedBar(null) ?? emptyBar())
      return
    }
    let live = true
    api
      .profile()
      .then((profile) => {
        if (!live) return
        const mine = barOf(profile)
        setSaved(mine)
        setBar(storedBar(user.username) ?? mine)
      })
      .catch(() => {
        if (!live) return
        setSaved(null)
        setBar(emptyBar())
      })
    return () => {
      live = false
    }
  }, [user])

  useEffect(() => {
    if (bar && user !== undefined) keepBar(owner, bar)
  }, [bar, owner, user])

  // The list follows the bar, a moment after the last change; an older request is dropped.
  const first = useRef(true)
  useEffect(() => {
    if (!bar) return
    const controller = new AbortController()
    const timer = window.setTimeout(
      () => {
        api
          .cards(bar, controller.signal)
          .then((cards) => {
            setList(cards)
            setFailed(false)
            setBarProblem(null)
          })
          .catch((error) => {
            if (error instanceof DOMException) return
            if (error instanceof ApiError && error.status === 422) setBarProblem(refusalWords(error.detail))
            else setFailed(true)
          })
      },
      first.current ? 0 : 250,
    )
    first.current = false
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [bar, reloads])

  const names = useMemo(() => new Map((reference?.areas ?? []).map((area) => [area.number, area.name])), [reference])

  const open = useCallback((id: string) => {
    openedFromList.current = true
    returnFocusTo.current = id
    navigate(postPath(id))
  }, [])

  // A post opened from the list closes back to it, as the browser's back does; a post opened by its
  // own address goes to the list.
  const close = useCallback(() => {
    setReportFor(null)
    if (openedFromList.current) {
      openedFromList.current = false
      history.back()
    } else navigate('/')
  }, [])

  // Closing a post opened from the list returns the focus to the card that opened it (#374); a card
  // that left the list meanwhile (a flag, a report) leaves the focus where the page puts it.
  const onPost = route.name === 'post'
  useEffect(() => {
    if (onPost || returnFocusTo.current === null) return
    const id = returnFocusTo.current
    returnFocusTo.current = null
    const frame = requestAnimationFrame(() => {
      document.querySelector<HTMLAnchorElement>(`a.open[href="${postPath(id)}"]`)?.focus()
    })
    return () => cancelAnimationFrame(frame)
  }, [onPost])

  // --- build step 6: a signed-in user's writes on a card ---
  const reload = useCallback(() => setReloads((n) => n + 1), [])
  const dismissNotice = useCallback(() => setNotice(null), [])
  const openPostId = route.name === 'post' ? route.id : null

  const flagDone = useCallback(
    (answer: FlagAnswer, retry: (id: string) => void) => {
      if (answer.flagged === answer.of) {
        setNotice({ text: 'המודעה סומנה כמשקרת והוסרה מהרשימה.' })
      } else {
        setNotice({
          text: `סומנו ${answer.flagged} מתוך ${answer.of} הפרסומים של המודעה: היא השתנתה בינתיים.`,
          retry: answer.remaining.length ? { label: 'נסו שוב', run: () => retry(answer.remaining[0]) } : undefined,
        })
      }
    },
    [],
  )

  const runFlag = useCallback(
    (id: string) => {
      setFlagBusy(true)
      setNotice(null)
      api
        .flag(id)
        .then((answer) => {
          flagDone(answer, runFlag)
          if (openPostId) close()
        })
        .catch((error) => {
          if (error instanceof ApiError && error.refusal === 'gone') {
            setNotice({ text: 'המודעה כבר הוסרה מהרשימה בינתיים.' })
            if (openPostId) close()
          } else {
            setNotice({ text: 'הסימון לא נשמר. בדקו את החיבור ונסו שוב.', retry: { label: 'נסו שוב', run: () => runFlag(id) } })
          }
        })
        .finally(() => {
          setFlagBusy(false)
          setFlagging(null)
          reload()
        })
    },
    [close, flagDone, openPostId, reload],
  )

  const markList = useCallback((postIds: string[], viewed: boolean) => {
    setList((current) =>
      current && {
        ...current,
        cards: current.cards.map((card) => (card.post_ids.some((id) => postIds.includes(id)) ? { ...card, viewed } : card)),
      },
    )
  }, [])

  const signedInUser = user && !user.must_change_password ? user : null
  const cardActions: CardActions | undefined = useMemo(
    () =>
      signedInUser
        ? {
            onFlag: (id) => setFlagging(id),
            onReport: (id) => {
              setReportFor(id)
              open(id)
            },
          }
        : undefined,
    [signedInUser, open],
  )
  const postActions: PostActions | undefined =
    signedInUser && reference
      ? {
          reportFields: reference.reportable_fields,
          startReport: reportFor !== null && reportFor === openPostId,
          onViewed: markList,
          onFlag: (id) => setFlagging(id),
          onReported: (removed) => {
            setNotice({
              text: removed
                ? 'הדיווח נשלח. המודעה הוסרה מהרשימה עד שהמנהל יבדוק אותה.'
                : 'הדיווח נשמר. המודעה עדיין ברשימה, והמנהל יטפל בה.',
            })
            if (removed) close()
            reload()
          },
          onGone: () => {
            setNotice({ text: 'המודעה כבר הוסרה מהרשימה בינתיים.' })
            close()
            reload()
          },
        }
      : undefined

  const signedIn = useCallback((next: SessionUser) => {
    forgetBar() // the bar opens on the saved preferences (#335)
    setBar(null)
    setUser(next)
    navigate(next.must_change_password ? '/password' : '/', { replace: true })
  }, [])

  const signOut = useCallback(() => {
    api
      .signOut()
      .catch(() => undefined)
      .finally(() => {
        forgetBar()
        setBar(null)
        setUser(null)
        navigate('/', { replace: true })
      })
  }, [])

  const savedNow = useCallback(
    (next: Bar) => {
      // A bar that stood on the saved preferences follows them; a changed one stays as it is.
      if (bar && saved && sameBar(bar, saved)) setBar(next)
      setSaved(next)
    },
    [bar, saved],
  )

  // Where a screen needs a signed-in user, or a guest, the address follows.
  const passwordDue = user?.must_change_password === true
  useEffect(() => {
    if (user === undefined) return
    if (passwordDue && route.name !== 'password') navigate('/password', { replace: true })
    else if (!user && (route.name === 'preferences' || route.name === 'password')) navigate('/sign-in', { replace: true })
    else if (user && (route.name === 'sign-in' || route.name === 'sign-up')) navigate('/', { replace: true })
  }, [user, passwordDue, route.name])

  const header = <Header user={user} onSignOut={signOut} />

  if (passwordDue || (user && route.name === 'password')) {
    return (
      <>
        {header}
        <PasswordScreen forced={passwordDue} onChanged={setUser} onSignOut={signOut} />
      </>
    )
  }
  if (!user && route.name === 'sign-in') {
    return (
      <>
        {header}
        <SignIn onSignedIn={signedIn} />
      </>
    )
  }
  if (!user && route.name === 'sign-up') {
    return (
      <>
        {header}
        <SignUp onSignedIn={signedIn} />
      </>
    )
  }
  if (route.name === 'preferences' || route.name === 'password') {
    return (
      <>
        {header}
        {user && saved && reference ? (
          <Preferences saved={saved} onSaved={savedNow} groups={reference.area_groups} names={names} today={today} />
        ) : (
          <main className="shell screen">
            <p className="empty">טוען…</p>
          </main>
        )}
      </>
    )
  }

  const standing: BarStanding = !user || !saved || !bar ? 'guest' : sameBar(bar, saved) ? 'saved' : 'changed'
  const openId = route.name === 'post' ? route.id : null
  const openCard = openId ? list?.cards.find((card) => card.post_ids.includes(openId)) : undefined

  return (
    <>
      {header}
      {bar && reference ? (
        <FilterBar
          bar={bar}
          onChange={setBar}
          standing={standing}
          onReset={() => saved && setBar(saved)}
          count={list ? list.count : null}
          error={barProblem}
          groups={reference.area_groups}
          names={names}
          today={today}
          phone={phone}
        />
      ) : (
        <div className="filterbar is-waiting" aria-hidden="true" />
      )}
      <main className="shell">
        {failed && !list ? (
          <p className="empty">לא הצלחנו לטעון את המודעות. בדקו שהאתר פועל ורעננו את הדף.</p>
        ) : !list ? (
          <Skeleton />
        ) : list.cards.length === 0 ? (
          <p className="empty">
            {bar && !bar.room.enabled && !bar.whole_apartment.enabled
              ? 'בחרו חדר בדירת שותפים או דירה שלמה כדי לראות מודעות.'
              : bar && barHeldCount(bar) > 0
                ? 'אין מודעה שמתאימה לסינון. נסו לנקות אחד הערכים.'
                : 'אין כרגע מודעות להצגה.'}
          </p>
        ) : (
          <div className="grid">
            {list.cards.map((card) => (
              <Card key={card.id} card={card} now={now} onOpen={open} actions={cardActions} />
            ))}
          </div>
        )}
      </main>
      {openId && <PostView id={openId} card={openCard} now={now} phone={phone} onClose={close} actions={postActions} />}
      {flagging && (
        <ConfirmFlag busy={flagBusy} onConfirm={() => runFlag(flagging)} onCancel={() => setFlagging(null)} />
      )}
      <NoticeBar notice={notice} onDismiss={dismissNotice} />
    </>
  )
}

function Skeleton() {
  return (
    <div className="grid" aria-hidden="true">
      {Array.from({ length: 8 }, (_, i) => (
        <div key={i} className="card skeleton" />
      ))}
    </div>
  )
}

/** The relative times move on once a minute. */
function useNow(): Date {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000)
    return () => window.clearInterval(timer)
  }, [])
  return now
}

function useMedia(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const media = window.matchMedia(query)
    const update = () => setMatches(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [query])
  return matches
}
