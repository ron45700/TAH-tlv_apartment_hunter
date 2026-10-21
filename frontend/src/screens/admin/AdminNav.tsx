// The admin's nav (#483): three sections, and the current section's pages beside them. On a wide
// screen two columns at the right: the sections on the header's tint, then the pages with their
// counts (a section of one page has no second column). Where it becomes a top bar, the same lists
// are two rows; a row that overflows shows ‹ › and takes the mouse wheel sideways.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ADMIN_SECTIONS, adminPath, sectionOf, type AdminPage } from '../../route'
import { Link } from './ui'

type ListedPage = Exclude<AdminPage, 'post'>

export const SECTION_TITLES: Record<string, string> = {
  posts: 'סקירת מודעות',
  analysis: 'ניתוח מידע',
  system: 'ניהול מערכת',
}

interface Props {
  page: AdminPage
  titles: Record<ListedPage, string>
  count: (page: ListedPage) => number | null
}

export function AdminNav({ page, titles, count }: Props) {
  const section = sectionOf(page)
  const current = page === 'post' ? null : page
  return (
    <nav className="anav" aria-label="דפי המנהל">
      <ScrollRow className="anav-sections" label="אזורי הניהול" current={section.name}>
        {ADMIN_SECTIONS.map((each) => {
          const on = each.name === section.name
          return (
            <li key={each.name}>
              <Link
                to={adminPath(each.pages[0])}
                className={`anav-section${on ? ' is-on' : ''}`}
                current={on && page === each.pages[0]}
              >
                {SECTION_TITLES[each.name]}
              </Link>
            </li>
          )
        })}
      </ScrollRow>
      {section.pages.length > 1 && (
        <ScrollRow className="anav-pages rail" label={SECTION_TITLES[section.name]} current={page}>
          {section.pages.map((name) => {
            const n = count(name)
            const on = name === current
            return (
              <li key={name}>
                <Link to={adminPath(name)} className={`rail-link${on ? ' is-on' : ''}`} current={on}>
                  <span>{titles[name]}</span>
                  {n !== null && <span className="rail-count">{n}</span>}
                </Link>
              </li>
            )
          })}
        </ScrollRow>
      )}
    </nav>
  )
}

/** A list that scrolls sideways when it overflows: the arrows appear only then, the wheel turns
 *  into a sideways scroll while the row can still move, and the current item is brought into view.
 *  Right to left: the start is at the right, `scrollLeft` runs from 0 down to negative. */
function ScrollRow({
  className,
  label,
  current,
  children,
}: {
  className: string
  label: string
  current: string
  children: ReactNode
}) {
  const list = useRef<HTMLUListElement>(null)
  const [ends, setEnds] = useState({ start: false, end: false })

  useEffect(() => {
    const row = list.current
    if (!row) return
    const measure = () => {
      const room = row.scrollWidth - row.clientWidth
      const moved = Math.abs(row.scrollLeft)
      setEnds({ start: room > 1 && moved > 1, end: room > 1 && moved < room - 1 })
    }
    const wheel = (event: WheelEvent) => {
      const room = row.scrollWidth - row.clientWidth
      if (room <= 1 || Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return
      const moved = Math.abs(row.scrollLeft)
      // Down scrolls towards the end (the left); at either end the page takes the wheel again.
      if ((event.deltaY > 0 && moved >= room - 1) || (event.deltaY < 0 && moved <= 1)) return
      event.preventDefault()
      row.scrollBy({ left: -event.deltaY })
    }
    // The items grow when their counts arrive: measured again, and the current one shown again.
    const resized = () => {
      reveal(row)
      measure()
    }
    resized()
    const observer = new ResizeObserver(resized)
    observer.observe(row)
    row.querySelectorAll('li').forEach((item) => observer.observe(item))
    row.addEventListener('scroll', measure, { passive: true })
    row.addEventListener('wheel', wheel, { passive: false })
    return () => {
      observer.disconnect()
      row.removeEventListener('scroll', measure)
      row.removeEventListener('wheel', wheel)
    }
  }, [current])

  /** The current item into view, inside the row only (never the page). */
  function reveal(row: HTMLUListElement) {
    const item = row.querySelector<HTMLElement>('.is-on')
    if (!item || row.scrollWidth <= row.clientWidth) return
    const rowBox = row.getBoundingClientRect()
    const box = item.getBoundingClientRect()
    if (box.left < rowBox.left + 44) row.scrollBy({ left: box.left - rowBox.left - 48 })
    else if (box.right > rowBox.right - 44) row.scrollBy({ left: box.right - rowBox.right + 48 })
  }

  const step = (towards: 1 | -1) => {
    const row = list.current
    if (row) row.scrollBy({ left: towards * row.clientWidth * 0.7, behavior: 'smooth' })
  }
  return (
    <div className={`srow ${className}`}>
      {ends.start && (
        <button type="button" className="srow-arrow srow-start" onClick={() => step(1)} aria-label={`הקודמים ב${label}`}>
          ›
        </button>
      )}
      <ul ref={list} aria-label={label}>
        {children}
      </ul>
      {ends.end && (
        <button type="button" className="srow-arrow srow-end" onClick={() => step(-1)} aria-label={`הבאים ב${label}`}>
          ‹
        </button>
      )}
    </div>
  )
}
