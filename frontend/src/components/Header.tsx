// The header (#333, #334, #342): its own cool tint, the user area at the right, the logo at the left,
// the one deliberate exception to "nothing on the left" (#324). A guest sees "התחבר" and "הירשם",
// pills of one height (#343). A signed-in user sees one pill (#343): a round avatar with the
// username's first letter on a sky-to-teal gradient, the username and a chevron (on a phone the
// avatar and the chevron); it opens a menu with "ההעדפות שלי" and under it "התנתק" (#334); the admin
// also has "ניהול" at the top, the admin's pages (3.8 (a)).
import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { navigate } from '../route'
import type { SessionUser } from '../types'

interface Props {
  /** `undefined` while the session is read: the area stays empty, so nothing jumps. */
  user: SessionUser | null | undefined
  onSignOut: () => void
}

function go(path: string) {
  return (event: MouseEvent) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
    event.preventDefault()
    navigate(path)
  }
}

export function Header({ user, onSignOut }: Props) {
  return (
    <header className="appbar">
      <div className="shell appbar-row">
        <div className="userarea">
          {user === null && (
            <>
              <a className="pill pill-primary" href="/sign-in" onClick={go('/sign-in')}>
                התחבר
              </a>
              <a className="pill" href="/sign-up" onClick={go('/sign-up')}>
                הירשם
              </a>
            </>
          )}
          {user && <UserMenu user={user} onSignOut={onSignOut} />}
        </div>
        <a className="logo" href="/" onClick={go('/')} aria-label="TLV Apartment Hunter, לעמוד הראשי" dir="ltr">
          <LogoMark />
          <span className="word">
            <span className="w1">TLV</span>{' '}
            <span className="w2">Apartment Hunter</span>
          </span>
        </a>
      </div>
    </header>
  )
}

function UserMenu({ user, onSignOut }: { user: SessionUser; onSignOut: () => void }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (event: PointerEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        button.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])
  const letter = user.username.slice(0, 1).toUpperCase()
  return (
    <div className="usermenu" ref={box}>
      <button
        ref={button}
        type="button"
        className="userpill"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`${user.username}, תפריט החשבון`}
        onClick={() => setOpen((value) => !value)}
      >
        {/* the letter is drawn by CSS, so the name starts with the username shown (#374) */}
        <span className="avatar" aria-hidden="true" data-letter={letter} />
        <span className="username" dir="ltr">
          {user.username}
        </span>
        <span className="chev" aria-hidden="true" />
      </button>
      {open && (
        <div className="menu" role="menu">
          {user.is_admin && !user.must_change_password && (
            <a
              role="menuitem"
              href="/admin"
              onClick={(event) => {
                setOpen(false)
                go('/admin')(event)
              }}
            >
              ניהול
            </a>
          )}
          {!user.must_change_password && (
            <a
              role="menuitem"
              href="/preferences"
              onClick={(event) => {
                setOpen(false)
                go('/preferences')(event)
              }}
            >
              ההעדפות שלי
            </a>
          )}
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false)
              onSignOut()
            }}
          >
            התנתק
          </button>
        </div>
      )}
    </div>
  )
}

/** The mark: three white-city blocks with their windows, over the sea's line, on a sky-to-teal
 *  tile. Light and cool (#333). The same drawing is public/favicon.svg. */
export function LogoMark() {
  return (
    <svg className="mark" width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
      <defs>
        <linearGradient id="logo-sky" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#c7ecfb" />
          <stop offset="1" stopColor="#5fd8c6" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="42" height="42" rx="12" fill="url(#logo-sky)" />
      <circle cx="33.5" cy="11" r="3.2" fill="#ffffff" fillOpacity=".9" />
      <path d="M8 32V20.5l6.5-3.5V32z M16.5 32V12.5l8-4V32z M26.5 32V17l9 3.2V32z" fill="#ffffff" />
      <path
        d="M10.5 22.5h2M10.5 26h2M19.5 14h2M19.5 17.5h2M19.5 21h2M19.5 24.5h2M29.5 21.5h3M29.5 25h3"
        stroke="#7cc9d9"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M5 36.5c4-2.4 7-2.4 11 0s7 2.4 11 0 7-2.4 12 0"
        stroke="#0e7490"
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  )
}
