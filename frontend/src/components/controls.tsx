// Small controls the bar and the preferences page share (PHASE_3.md 3.7 (e)). A switch reads on or
// off by its track and position, its label always in words; the level is a two-way switch,
// "העדפה" or "חובה" (BASELINE.md §8); no glyph carries a state (#323).
import { useEffect, useId, useRef, type CSSProperties, type ReactNode } from 'react'
import type { Level } from '../bar'

export function Switch({
  label,
  checked,
  onChange,
  disabled = false,
  describedBy,
}: {
  label: ReactNode
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  describedBy?: string
}) {
  const name = useId()
  return (
    <label className={`switch${disabled ? ' is-disabled' : ''}`}>
      <input
        name={name}
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="track" aria-hidden="true" />
      <span className="switch-label">{label}</span>
    </label>
  )
}

export const LEVEL_WORDS: Record<Level, string> = { preference: 'העדפה', critical: 'חובה' }
export const MUST_HIDES = 'חובה: מודעה שלא עומדת בזה לא תוצג. העדפה: משפיעה רק על הסדר והצבעים.'

export function LevelSwitch({
  value,
  onChange,
  label,
}: {
  value: Level
  onChange: (level: Level) => void
  label: string
}) {
  const name = useId()
  return (
    <div className="levels" role="radiogroup" aria-label={`רמה: ${label}`}>
      {(['preference', 'critical'] as const).map((level) => (
        <label key={level} className={value === level ? 'level is-on' : 'level'}>
          <input type="radio" name={name} checked={value === level} onChange={() => onChange(level)} />
          {LEVEL_WORDS[level]}
        </label>
      ))}
    </div>
  )
}

/** A panel under its button: closes on a click outside it and on Esc, and gives the focus back. */
export function Popover({
  label,
  onClose,
  children,
  wide = false,
}: {
  label: string
  onClose: () => void
  children: ReactNode
  wide?: boolean
}) {
  const panel = useRef<HTMLDivElement>(null)
  const close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    panel.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        close.current()
      }
    }
    const onDown = (event: PointerEvent) => {
      const target = event.target as Node
      if (panel.current?.contains(target) || opener?.contains(target)) return // the opener toggles
      close.current()
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onDown)
      opener?.focus?.()
    }
  }, [])
  return (
    <div className={wide ? 'popover is-wide' : 'popover'} role="dialog" aria-label={label} ref={panel} tabIndex={-1}>
      {children}
    </div>
  )
}

/** A number box; an empty box is "don't care" (`null`). */
export function NumberBox({
  label,
  value,
  onChange,
  min,
  max,
  step,
  placeholder,
}: {
  label: string
  value: number | null
  onChange: (value: number | null) => void
  min?: number
  max?: number
  step?: number
  placeholder?: string
}) {
  const name = useId()
  return (
    <label className="numbox">
      <span className="numbox-label">{label}</span>
      <input
        name={name}
        type="number"
        inputMode="decimal"
        dir="ltr"
        value={value ?? ''}
        min={min}
        max={max}
        step={step}
        placeholder={placeholder}
        onChange={(event) => {
          const text = event.target.value
          const parsed = text === '' ? null : Number(text)
          onChange(parsed === null || Number.isNaN(parsed) ? null : parsed)
        }}
      />
    </label>
  )
}

/** Two thumbs on one track (the preferences page's ranges, 3.7 (e)(iii)). A thumb at its end of the
 *  track is an open end (`null`). */
export function DualSlider({
  label,
  low,
  high,
  min,
  max,
  step,
  onChange,
}: {
  label: string
  low: number | null
  high: number | null
  min: number
  max: number
  step: number
  onChange: (low: number | null, high: number | null) => void
}) {
  const id = useId()
  const lowValue = Math.max(min, Math.min(low ?? min, max))
  const highValue = Math.max(min, Math.min(high ?? max, max))
  const percent = (value: number) => ((value - min) / (max - min)) * 100
  const style = { '--lo': `${percent(lowValue)}%`, '--hi': `${percent(highValue)}%` } as CSSProperties
  return (
    <div className={low === null && high === null ? 'dual is-open' : 'dual'} style={style} dir="rtl">
      <span className="dual-fill" aria-hidden="true" />
      <input
        name={`${id}-low`}
        type="range"
        aria-label={`${label}: מינימום`}
        min={min}
        max={max}
        step={step}
        value={lowValue}
        onChange={(event) => {
          const value = Math.min(Number(event.target.value), highValue)
          onChange(value <= min ? null : value, high)
        }}
      />
      <input
        name={`${id}-high`}
        type="range"
        aria-label={`${label}: מקסימום`}
        min={min}
        max={max}
        step={step}
        value={highValue}
        onChange={(event) => {
          const value = Math.max(Number(event.target.value), lowValue)
          onChange(low, value >= max ? null : value)
        }}
      />
    </div>
  )
}
