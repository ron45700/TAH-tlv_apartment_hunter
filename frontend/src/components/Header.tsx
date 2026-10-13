// The header (#333, #334, #342): its own cool tint, the user area at the right, the logo at the left,
// the one deliberate exception to "nothing on the left" (#324). A guest sees "התחבר" and "הירשם",
// pills of one height (#343); they lead nowhere until sign-in is built (step 5).

export function Header() {
  return (
    <header className="appbar">
      <div className="shell appbar-row">
        <div className="userarea">
          <button className="pill pill-primary" type="button" aria-disabled="true" title="ההתחברות תיפתח בקרוב">
            התחבר
          </button>
          <button className="pill" type="button" aria-disabled="true" title="ההרשמה תיפתח בקרוב">
            הירשם
          </button>
        </div>
        <a className="logo" href="/" aria-label="TLV Apartment Hunter, לעמוד הראשי" dir="ltr">
          <LogoMark />
          <span className="word">
            <span className="w1">TLV</span>
            <span className="w2">Apartment Hunter</span>
          </span>
        </a>
      </div>
    </header>
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
