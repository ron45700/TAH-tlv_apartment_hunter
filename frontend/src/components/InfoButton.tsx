// The "i" over the photo's top-left corner, inside the card, on a faded background (#323, #337): it
// shows the tier's words on hover or focus (desktop) and on tap (phone). It is a button whose
// accessible name is the label, so a screen reader reads the tier without the colour.
import { useEffect, useRef, useState } from 'react'

export function InfoButton({ label }: { label: string }) {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (event: Event) => {
      if (!button.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', close)
    return () => document.removeEventListener('pointerdown', close)
  }, [open])

  return (
    <button
      ref={button}
      className={open ? 'info open' : 'info'}
      type="button"
      aria-label={label}
      aria-expanded={open}
      onClick={(event) => {
        event.preventDefault()
        event.stopPropagation()
        setOpen((value) => !value)
      }}
      onKeyDown={(event) => event.key === 'Escape' && setOpen(false)}
    >
      <span aria-hidden="true">i</span>
      <span className="tip" role="tooltip">
        {label}
      </span>
    </button>
  )
}
