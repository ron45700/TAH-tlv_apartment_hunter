// The site (PHASE_3.md 3.7 (f)): the list (home) with the filter bar, the opened post, and the
// screens of build step 5: sign-in, sign-up with a key, the forced password change and the
// preferences page. A grid of cards on a desktop and a tablet, one card under the other on a phone
// (#303), in one centred column that grows with the screen (#347).
//
// The bar (3.7 (e)(ii)): for a signed-in user it opens on the saved preferences, for a guest empty
// (#315, #335); a change is temporary and "ההעדפות שלי" resets it. It lives in the tab's memory and
// `sessionStorage` (#330 point 14): a reload keeps a changed bar, a new visit starts again. It is sent
// with each list request and never saved (#335): preferences are saved on the preferences page only.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, api } from './api'
import { barHeldCount, barOf, emptyBar, israelToday, refusalWords, sameBar, type Bar } from './bar'
import { Card } from './components/Card'
import { FilterBar, type BarStanding } from './components/FilterBar'
import { Header } from './components/Header'
import { PostView } from './components/PostView'
import { navigate, postPath, useRoute } from './route'
import { PasswordScreen, SignIn, SignUp } from './screens/Account'
import { Preferences } from './screens/Preferences'
import type { CardsResponse, Reference, SessionUser } from './types'

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
  const now = useNow()
  const phone = useMedia(PHONE)
  const openedFromList = useRef(false)
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
  }, [bar])

  const names = useMemo(() => new Map((reference?.areas ?? []).map((area) => [area.number, area.name])), [reference])

  const open = useCallback((id: string) => {
    openedFromList.current = true
    navigate(postPath(id))
  }, [])

  // A post opened from the list closes back to it, as the browser's back does; a post opened by its
  // own address goes to the list.
  const close = useCallback(() => {
    if (openedFromList.current) {
      openedFromList.current = false
      history.back()
    } else navigate('/')
  }, [])

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
              <Card key={card.id} card={card} now={now} onOpen={open} />
            ))}
          </div>
        )}
      </main>
      {openId && <PostView id={openId} card={openCard} now={now} phone={phone} onClose={close} />}
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
