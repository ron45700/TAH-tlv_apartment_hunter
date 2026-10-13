// The list (home) and the opened post, for a guest (PHASE_3.md 3.7 (f), build step 3). The list is a
// guest's empty bar (#315); the filter bar arrives with step 4, sign-in with step 5. A grid of cards
// on a desktop and a tablet, one card under the other on a phone (#303), in one centred column that
// grows with the screen, so every size is laid out for itself (#347).
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { Card } from './components/Card'
import { Header } from './components/Header'
import { PostView } from './components/PostView'
import { navigate, postPath, useRoute } from './route'
import type { CardsResponse } from './types'

const PHONE = '(max-width: 699.98px)'

export function App() {
  const route = useRoute()
  const [list, setList] = useState<CardsResponse | null>(null)
  const [failed, setFailed] = useState(false)
  const now = useNow()
  const phone = useMedia(PHONE)
  const openedFromList = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    api
      .cards(controller.signal)
      .then(setList)
      .catch((error) => {
        if (!(error instanceof DOMException)) setFailed(true)
      })
    return () => controller.abort()
  }, [])

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

  const openId = route.name === 'post' ? route.id : null
  const openCard = openId ? list?.cards.find((card) => card.post_ids.includes(openId)) : undefined

  return (
    <>
      <Header />
      <div className="statusbar">
        <div className="shell">
          <p className="status" aria-live="polite">
            {list ? (
              <>
                <strong>{list.count}</strong> מודעות
              </>
            ) : failed ? null : (
              'טוען מודעות…'
            )}
          </p>
        </div>
      </div>
      <main className="shell">
        {failed ? (
          <p className="empty">לא הצלחנו לטעון את המודעות. בדקו שהאתר פועל ורעננו את הדף.</p>
        ) : !list ? (
          <Skeleton />
        ) : list.cards.length === 0 ? (
          <p className="empty">אין כרגע מודעות להצגה.</p>
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
