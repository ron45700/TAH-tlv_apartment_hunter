// The filter bar, as redesigned in round 9 (PHASE_3.md 3.7 (e)(ii); #329, #333–#336, #317): sticky
// under the header. Row 1: the two kinds and the profile's one sublet switch, disabled with its line
// when both kinds are off; then the status line, the count and where the bar stands, in words, with
// "ההעדפות שלי" to reset it when it differs from the saved preferences (#335). One values row per
// kind that is on, labelled with the kind's name: areas, price, rooms and "עוד", each a pill that
// fills with its value in words. No save in the bar (#335). On a phone (point 39, option A): the three
// switches on one row, one dense row with the status and "סינון (N)", and a full-screen sheet with
// the same rows and "הצגת N מודעות".
import { useEffect, useState, type ReactNode } from 'react'
import {
  OPTIONS,
  OPTION_NAMES,
  areasWords,
  barHeldCount,
  moreCount,
  priceWords,
  roomsWords,
  withOption,
  type Bar,
  type OptionName,
  type SearchOption,
} from '../bar'
import type { AreaGroup } from '../types'
import { Popover, Switch } from './controls'
import { AreasField, MoreFields, PriceField, RangeField } from './fields'

export type BarStanding = 'guest' | 'saved' | 'changed'

interface Props {
  bar: Bar
  onChange: (bar: Bar) => void
  standing: BarStanding
  onReset: () => void
  count: number | null
  error: string | null
  groups: AreaGroup[]
  names: ReadonlyMap<number, string>
  today: string
  phone: boolean
}

export function FilterBar(props: Props) {
  const { bar, onChange, phone } = props
  const [sheet, setSheet] = useState(false)
  const noKind = !bar.room.enabled && !bar.whole_apartment.enabled
  const kinds = (
    <div className="kinds">
      {OPTIONS.map((name) => (
        <Switch
          key={name}
          label={OPTION_NAMES[name]}
          checked={bar[name].enabled}
          onChange={(enabled) => onChange(withOption(bar, name, { enabled }))}
        />
      ))}
      <Switch
        label="גם סאבלט"
        checked={bar.include_sublets}
        disabled={noKind}
        describedBy={noKind ? 'no-kind-line' : undefined}
        onChange={(include_sublets) => onChange({ ...bar, include_sublets })}
      />
    </div>
  )
  const noKindLine = noKind && (
    <p className="bar-note" id="no-kind-line">
      בחרו חדר או דירה שלמה כדי לראות סאבלטים
    </p>
  )
  const error = props.error && (
    <p className="bar-error" role="alert">
      {props.error}
    </p>
  )

  if (phone) {
    const held = barHeldCount(bar)
    return (
      <div className="filterbar is-phone">
        <div className="shell">
          {kinds}
          {noKindLine}
          <div className="bar-statusrow">
            <Status {...props} />
            <button type="button" className="barbtn" onClick={() => setSheet(true)} aria-haspopup="dialog">
              {held ? `סינון (${held})` : 'סינון'}
            </button>
          </div>
          {error}
        </div>
        {sheet && <Sheet {...props} noKind={noKind} onClose={() => setSheet(false)} />}
      </div>
    )
  }

  return (
    <div className="filterbar">
      <div className="shell">
        <div className="bar-row">
          {kinds}
          <Status {...props} />
        </div>
        {noKindLine}
        {OPTIONS.filter((name) => bar[name].enabled).map((name) => (
          <ValuesRow key={name} name={name} {...props} />
        ))}
        {error}
      </div>
    </div>
  )
}

function Status({ standing, count, onReset }: Props) {
  return (
    <p className="bar-status" aria-live="polite">
      <span>
        <strong>{count === null ? 'טוען מודעות…' : `${count} מודעות`}</strong>
        {standing === 'saved' && ' · לפי ההעדפות השמורות'}
        {standing === 'changed' && (
          <>
            {' · סינון זמני'}
            <span className="status-long">, שונה מההעדפות שלך</span>
          </>
        )}
      </span>
      {standing === 'changed' && (
        <button type="button" className="barbtn is-reset" onClick={onReset}>
          ההעדפות שלי
        </button>
      )}
    </p>
  )
}

type Control = 'areas' | 'price' | 'rooms' | 'more'

function ValuesRow({ name, bar, onChange, groups, names, today }: Props & { name: OptionName }) {
  const [open, setOpen] = useState<Control | null>(null)
  const option = bar[name]
  const change = (values: Partial<SearchOption>) => onChange(withOption(bar, name, values))
  const more = moreCount(option)
  const toggle = (control: Control) => setOpen((current) => (current === control ? null : control))
  const close = () => setOpen(null)
  const label = (control: string) => `${control}, ${OPTION_NAMES[name]}`
  return (
    <div className="values" role="group" aria-label={OPTION_NAMES[name]}>
      <span className="values-name">{OPTION_NAMES[name]}:</span>
      <ValueChip
        label="אזורים"
        words={areasWords(option.areas, names)}
        open={open === 'areas'}
        onToggle={() => toggle('areas')}
        onClear={() => change({ areas: [] })}
      >
        <Popover label={label('אזורים')} onClose={close} wide>
          <AreasField option={option} groups={groups} names={names} onChange={change} />
        </Popover>
      </ValueChip>
      <ValueChip
        label="מחיר"
        words={priceWords(option)}
        open={open === 'price'}
        onToggle={() => toggle('price')}
        onClear={() => change({ price_min: null, price_max: null })}
      >
        <Popover label={label('מחיר')} onClose={close}>
          <PriceField option={option} onChange={change} />
        </Popover>
      </ValueChip>
      <ValueChip
        label="חדרים"
        words={roomsWords(option.rooms)}
        open={open === 'rooms'}
        onToggle={() => toggle('rooms')}
        onClear={() => change({ rooms: null })}
      >
        <Popover label={label('חדרים')} onClose={close}>
          <RangeField title="חדרים" scale="rooms" range={option.rooms} onChange={(rooms) => change({ rooms })} />
        </Popover>
      </ValueChip>
      <ValueChip label="עוד" words={more ? `עוד (${more})` : null} open={open === 'more'} onToggle={() => toggle('more')}>
        <Popover label={label('עוד')} onClose={close} wide>
          <div className="more-grid">
            <MoreFields name={name} option={option} today={today} onChange={change} />
          </div>
        </Popover>
      </ValueChip>
    </div>
  )
}

function ValueChip({
  label,
  words,
  open,
  onToggle,
  onClear,
  children,
}: {
  label: string
  words: string | null
  open: boolean
  onToggle: () => void
  onClear?: () => void
  children: ReactNode
}) {
  return (
    <div className="bchip-wrap">
      <button
        type="button"
        className={words ? 'bchip is-held' : 'bchip'}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={onToggle}
      >
        {words ?? label}
      </button>
      {words && onClear && (
        <button type="button" className="bchip-clear" onClick={onClear} aria-label={`ניקוי: ${words}`}>
          נקה
        </button>
      )}
      {open && children}
    </div>
  )
}

/** The phone's full-screen sheet (3.7 (e)(ii)): the kind rows, labelled as on a desktop, and
 *  "הצגת N מודעות" at its foot. The list behind it follows every change. */
function Sheet(props: Props & { noKind: boolean; onClose: () => void }) {
  const { bar, onChange, groups, names, today, count, onClose } = props
  useEffect(() => {
    document.body.classList.add('locked')
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => {
      document.body.classList.remove('locked')
      document.removeEventListener('keydown', onKey)
    }
  }, [onClose])
  return (
    <div className="barsheet" role="dialog" aria-modal="true" aria-label="סינון">
      <div className="barsheet-top">
        <h2>סינון</h2>
        <button type="button" className="barbtn" onClick={onClose}>
          סגירה
        </button>
      </div>
      <div className="barsheet-body">
        {props.noKind && <p className="bar-note">בחרו חדר או דירה שלמה בשורה העליונה.</p>}
        {OPTIONS.filter((name) => bar[name].enabled).map((name) => {
          const option = bar[name]
          const change = (values: Partial<SearchOption>) => onChange(withOption(bar, name, values))
          const chosen = option.areas.length
          return (
            <section key={name} className="sheet-kind">
              <h3>{OPTION_NAMES[name]}</h3>
              <details className="sheet-areas">
                <summary>{chosen ? `אזורים: ${chosen} נבחרו` : 'אזורים: כל האזורים'}</summary>
                <AreasField option={option} groups={groups} names={names} onChange={change} />
              </details>
              <PriceField option={option} onChange={change} />
              <RangeField title="חדרים" scale="rooms" range={option.rooms} onChange={(rooms) => change({ rooms })} />
              <MoreFields name={name} option={option} today={today} onChange={change} />
            </section>
          )
        })}
        {props.error && (
          <p className="bar-error" role="alert">
            {props.error}
          </p>
        )}
      </div>
      <div className="barsheet-foot">
        <button type="button" className="mainbtn" onClick={onClose}>
          {count === null ? 'טוען…' : `הצגת ${count} מודעות`}
        </button>
      </div>
    </div>
  )
}
