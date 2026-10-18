// The values of one search option, as fields (PHASE_3.md 3.7 (e)): the areas grouped as §6 with
// "select all" per group and the non-residential group collapsed at the bottom (#248, #249, #261);
// the price (critical, no level, BASELINE.md §8); the ranges with their level; the features with a
// fixed wanted value (#269); the entry date with "immediate" as a quick chip (#270); "women only".
// The bar's popovers and phone sheet show them compact; the preferences page shows them in full,
// each range with a slider (`full`). Every field's "נקה" clears it to "don't care".
import { useEffect, useRef, type ReactNode } from 'react'
import {
  FEATURES,
  FEATURE_NAMES,
  setDateEnd,
  setEarliest,
  setRangeEnd,
  toggleAreas,
  type DateRange,
  type Feature,
  type Level,
  type OptionName,
  type Range,
  type SearchOption,
} from '../bar'
import type { AreaGroup } from '../types'
import { DualSlider, LevelSwitch, NumberBox, Switch } from './controls'

type Change = (change: Partial<SearchOption>) => void

export function Field({
  title,
  onClear,
  children,
  hint,
}: {
  title: string
  onClear?: () => void
  children: ReactNode
  hint?: string
}) {
  return (
    <fieldset className="field">
      <div className="field-head">
        <legend>{title}</legend>
        {onClear && (
          <button type="button" className="linkbtn" onClick={onClear}>
            נקה
          </button>
        )}
      </div>
      {hint && <p className="field-hint">{hint}</p>}
      {children}
    </fieldset>
  )
}

// --- areas ---

export function AreaPicker({
  selected,
  groups,
  names,
  onChange,
}: {
  selected: number[]
  groups: AreaGroup[]
  names: ReadonlyMap<number, string>
  onChange: (areas: number[]) => void
}) {
  const chosen = new Set(selected)
  return (
    <div className="areas">
      {groups.map((group) => {
        const inGroup = group.areas.filter((n) => chosen.has(n)).length
        const all = (
          <GroupCheck
            heading={group.heading}
            count={inGroup}
            total={group.areas.length}
            onChange={(on) => onChange(toggleAreas(selected, group.areas, on))}
          />
        )
        const list = (
          <ul className="area-list">
            {group.areas.map((number) => (
              <li key={number}>
                <label className="check">
                  <input
                    name={`area-${number}`}
                    type="checkbox"
                    checked={chosen.has(number)}
                    onChange={(event) => onChange(toggleAreas(selected, [number], event.target.checked))}
                  />
                  <span>{names.get(number) ?? number}</span>
                </label>
              </li>
            ))}
          </ul>
        )
        if (group.collapsed) {
          return (
            <details key={group.heading} className="area-group is-collapsed" open={inGroup > 0 || undefined}>
              <summary>
                <span className="area-heading">{group.heading}</span>
                {inGroup > 0 && <span className="area-count">{inGroup} נבחרו</span>}
              </summary>
              <div className="area-all">{all}</div>
              {list}
            </details>
          )
        }
        return (
          <section key={group.heading} className="area-group">
            <div className="area-head">
              <h3 className="area-heading">{group.heading}</h3>
              {all}
            </div>
            {list}
          </section>
        )
      })}
    </div>
  )
}

function GroupCheck({
  heading,
  count,
  total,
  onChange,
}: {
  heading: string
  count: number
  total: number
  onChange: (on: boolean) => void
}) {
  const box = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (box.current) box.current.indeterminate = count > 0 && count < total
  }, [count, total])
  return (
    <label className="check check-all">
      <input
        ref={box}
        name={`group-${heading}`}
        type="checkbox"
        aria-label={`כל האזורים ב${heading}`}
        checked={count === total}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>בחירת הכל</span>
    </label>
  )
}

export function AreasField({
  option,
  groups,
  names,
  onChange,
}: {
  option: SearchOption
  groups: AreaGroup[]
  names: ReadonlyMap<number, string>
  onChange: Change
}) {
  const count = option.areas.length
  return (
    <Field
      title="אזורים"
      onClear={count ? () => onChange({ areas: [] }) : undefined}
      hint={count ? `${count} נבחרו. מודעה מחוץ לאזורים שנבחרו לא תוצג.` : 'בלי בחירה: כל האזורים.'}
    >
      <AreaPicker selected={option.areas} groups={groups} names={names} onChange={(areas) => onChange({ areas })} />
    </Field>
  )
}

// --- price and ranges ---

const SCALES = {
  price: { min: 0, max: 15000, step: 100 },
  rooms: { min: 1, max: 8, step: 0.5 },
  floor: { min: -1, max: 30, step: 1 },
  size: { min: 0, max: 250, step: 5 },
} as const

export function PriceField({ option, onChange, full = false }: { option: SearchOption; onChange: Change; full?: boolean }) {
  const held = option.price_min !== null || option.price_max !== null
  return (
    <Field
      title="מחיר לחודש (₪)"
      onClear={held ? () => onChange({ price_min: null, price_max: null }) : undefined}
      hint={full ? 'מודעה מחוץ לטווח לא תוצג. תיבה ריקה: ללא הגבלה.' : undefined}
    >
      <div className="pair">
        <NumberBox label="מ-" value={option.price_min} min={0} step={100} onChange={(v) => onChange({ price_min: v })} />
        <NumberBox label="עד" value={option.price_max} min={0} step={100} onChange={(v) => onChange({ price_max: v })} />
      </div>
      {full && (
        <DualSlider
          label="מחיר"
          {...SCALES.price}
          low={option.price_min}
          high={option.price_max}
          onChange={(low, high) => onChange({ price_min: low, price_max: high })}
        />
      )}
    </Field>
  )
}

export function RangeField({
  title,
  scale,
  range,
  onChange,
  full = false,
  hint,
}: {
  title: string
  scale: keyof typeof SCALES
  range: Range | null
  onChange: (range: Range | null) => void
  full?: boolean
  hint?: string
}) {
  const { min, max, step } = SCALES[scale]
  return (
    <Field title={title} onClear={range ? () => onChange(null) : undefined} hint={hint}>
      <div className="pair">
        <NumberBox
          label="מ-"
          value={range?.min ?? null}
          min={min}
          step={step}
          onChange={(v) => onChange(setRangeEnd(range, 'min', v))}
        />
        <NumberBox
          label="עד"
          value={range?.max ?? null}
          min={min}
          step={step}
          onChange={(v) => onChange(setRangeEnd(range, 'max', v))}
        />
      </div>
      {full && (
        <DualSlider
          label={title}
          min={min}
          max={max}
          step={step}
          low={range?.min ?? null}
          high={range?.max ?? null}
          onChange={(low, high) =>
            onChange(low === null && high === null ? null : { min: low, max: high, level: range?.level ?? 'preference' })
          }
        />
      )}
      {range && <LevelSwitch label={title} value={range.level} onChange={(level) => onChange({ ...range, level })} />}
    </Field>
  )
}

// --- features, entry date, women only ---

function FeatureControl({
  feature,
  level,
  onChange,
  tile,
}: {
  feature: Feature
  level: Level | null
  onChange: (level: Level | null) => void
  tile: boolean
}) {
  const name = FEATURE_NAMES[feature]
  return (
    <div className={`feature${level ? ' is-on' : ''}`}>
      {tile ? (
        <button type="button" className="tile" aria-pressed={level !== null} onClick={() => onChange(level ? null : 'preference')}>
          {name}
        </button>
      ) : (
        <Switch label={name} checked={level !== null} onChange={(on) => onChange(on ? 'preference' : null)} />
      )}
      {level && <LevelSwitch label={name} value={level} onChange={onChange} />}
    </div>
  )
}

export function FeaturesField({ option, onChange, tiles = false }: { option: SearchOption; onChange: Change; tiles?: boolean }) {
  const held = FEATURES.some((feature) => option[feature] !== null)
  return (
    <Field title="מאפיינים" onClear={held ? () => onChange({ broker: null, parking: null, balcony: null }) : undefined}>
      <div className={tiles ? 'features is-tiles' : 'features'}>
        {FEATURES.map((feature) => (
          <FeatureControl
            key={feature}
            feature={feature}
            level={option[feature]}
            tile={tiles}
            onChange={(level) => onChange({ [feature]: level })}
          />
        ))}
      </div>
    </Field>
  )
}

export function EntryField({
  entry,
  today,
  onChange,
}: {
  entry: DateRange | null
  today: string
  onChange: (entry: DateRange | null) => void
}) {
  const immediate = entry !== null && entry.earliest === null && entry.latest === today
  return (
    <Field title="תאריך כניסה" onClear={entry ? () => onChange(null) : undefined}>
      <div className="quick">
        <button
          type="button"
          className={immediate ? 'qchip is-on' : 'qchip'}
          aria-pressed={immediate}
          onClick={() => onChange(immediate ? null : { earliest: null, latest: today, level: entry?.level ?? 'preference' })}
        >
          מיידי
        </button>
      </div>
      <div className="pair">
        <label className="numbox">
          <span className="numbox-label">מתאריך</span>
          <input
            name="entry-earliest"
            type="date"
            value={entry?.earliest ?? ''}
            onChange={(event) => onChange(setEarliest(entry, event.target.value))}
          />
        </label>
        <label className="numbox">
          <span className="numbox-label">עד תאריך</span>
          <input
            name="entry-latest"
            type="date"
            value={entry?.latest ?? ''}
            onChange={(event) => onChange(setDateEnd(entry, 'latest', event.target.value))}
          />
        </label>
      </div>
      {entry && <LevelSwitch label="תאריך כניסה" value={entry.level} onChange={(level) => onChange({ ...entry, level })} />}
    </Field>
  )
}

export function WomenField({ option, onChange }: { option: SearchOption; onChange: Change }) {
  return (
    <Field title="נשים בלבד">
      <Switch
        label="הסתרת מודעות לנשים בלבד"
        checked={option.hide_women_only}
        onChange={(hide) => onChange({ hide_women_only: hide })}
      />
    </Field>
  )
}

/** Everything inside "עוד" (3.7 (e)(ii)): floor, sqm in the whole apartment only (#247), the
 *  features, the entry date and "women only", each category with its level (#330 point 15). */
export function MoreFields({
  name,
  option,
  today,
  onChange,
}: {
  name: OptionName
  option: SearchOption
  today: string
  onChange: Change
}) {
  return (
    <>
      <RangeField title="קומה" scale="floor" range={option.floor} hint="-1 מרתף, 0 קרקע" onChange={(floor) => onChange({ floor })} />
      {name === 'whole_apartment' && (
        <RangeField title="גודל (מ״ר)" scale="size" range={option.size_sqm} onChange={(size_sqm) => onChange({ size_sqm })} />
      )}
      <FeaturesField option={option} onChange={onChange} />
      <EntryField entry={option.entry_date} today={today} onChange={(entry_date) => onChange({ entry_date })} />
      <WomenField option={option} onChange={onChange} />
    </>
  )
}
