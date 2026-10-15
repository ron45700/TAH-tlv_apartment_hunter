// The correction's value form (3.8 (h), step 5): one reportable field in its Gate B shape. A Marked
// field first asks its state (written, not stated, unclear), then the value; a closed list is a set
// of radio buttons; the areas are 3.7's area picker; the phones' names one box per phone of the
// post. The server checks the value by its Gate B type and as the whole post (#284, #405).
import { useState, type FormEvent, type ReactNode } from 'react'
import { CHOICES, KINDS, draftOf, isMarked, valueOf, type Draft, type MarkedState } from '../../admin/values'
import { AreaPicker } from '../../components/fields'
import type { AreaGroup } from '../../types'

const STATES: [MarkedState, string][] = [
  ['written', 'כתוב במודעה'],
  ['not_written', 'לא צוין'],
  ['unclear', 'לא ברור'],
]

interface Props {
  field: string
  label: string
  /** The value users see now: the form opens on it. */
  value: unknown
  phones: string[]
  groups: AreaGroup[]
  names: ReadonlyMap<number, string>
  busy: boolean
  error: string | null
  onSubmit: (value: unknown) => void
  onCancel: () => void
}

export function ValueForm({ field, label, value, phones, groups, names, busy, error, onSubmit, onCancel }: Props) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(field, value, phones))
  const kind = KINDS[field]
  const result = valueOf(field, draft)
  const set = (change: Partial<Draft>) => setDraft((current) => ({ ...current, ...change }))
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (result !== null) onSubmit(result)
  }
  const id = `vf-${field}`

  return (
    <form className="valueform" onSubmit={submit} aria-labelledby={`${id}-title`}>
      <h3 id={`${id}-title`}>תיקון: {label}</h3>
      {kind === 'enum' && (
        <Radios
          name={`${id}-choice`}
          legend={label}
          choices={CHOICES[field]}
          value={draft.choice}
          onChange={(choice) => set({ choice })}
        />
      )}
      {isMarked(kind) && (
        <Radios
          name={`${id}-state`}
          legend="מה המודעה אומרת"
          choices={STATES}
          value={draft.state}
          onChange={(state) => set({ state: state as MarkedState })}
        />
      )}
      {isMarked(kind) && draft.state === 'written' && <MarkedValue id={id} field={field} draft={draft} set={set} />}
      {kind === 'areas' && (
        <div className="valueform-areas">
          <AreaPicker selected={draft.areas} groups={groups} names={names} onChange={(areas) => set({ areas })} />
        </div>
      )}
      {kind === 'lines' && (
        <Labelled id={`${id}-text`} label="רחוב בכל שורה">
          <textarea id={`${id}-text`} rows={3} value={draft.text} onChange={(event) => set({ text: event.target.value })} />
        </Labelled>
      )}
      {kind === 'city' && (
        <Labelled id={`${id}-text`} label="העיר" hint="השאירו ריק כשהמודעה בתל אביב-יפו.">
          <input id={`${id}-text`} value={draft.text} onChange={(event) => set({ text: event.target.value })} />
        </Labelled>
      )}
      {kind === 'phones' &&
        (phones.length === 0 ? (
          <p className="tfield-hint">אין טלפונים במודעה.</p>
        ) : (
          phones.map((phone) => (
            <Labelled key={phone} id={`${id}-${phone}`} label={`השם ליד ${phone}`}>
              <input
                id={`${id}-${phone}`}
                value={draft.names[phone] ?? ''}
                onChange={(event) => set({ names: { ...draft.names, [phone]: event.target.value } })}
              />
            </Labelled>
          ))
        ))}
      {error && (
        <p className="formerror" role="alert">
          {error}
        </p>
      )}
      <div className="valueform-actions">
        <button type="submit" className="mainbtn" disabled={busy || result === null}>
          שמירת התיקון
        </button>
        <button type="button" className="linkbtn" onClick={onCancel}>
          ביטול
        </button>
      </div>
    </form>
  )
}

function MarkedValue({
  id,
  field,
  draft,
  set,
}: {
  id: string
  field: string
  draft: Draft
  set: (change: Partial<Draft>) => void
}) {
  const kind = KINDS[field]
  const text = (label: string, hint?: string, inputMode: 'numeric' | 'decimal' | 'text' = 'text') => (
    <Labelled id={`${id}-text`} label={label} hint={hint}>
      <input
        id={`${id}-text`}
        dir="ltr"
        inputMode={inputMode}
        value={draft.text}
        onChange={(event) => set({ text: event.target.value })}
      />
    </Labelled>
  )
  const radios = (legend: string, choices: [string, string][]) => (
    <Radios name={`${id}-choice`} legend={legend} choices={choices} value={draft.choice} onChange={(choice) => set({ choice })} />
  )
  switch (kind) {
    case 'marked-enum':
      return radios('הערך', CHOICES[field])
    case 'marked-bool':
      return radios('הערך', CHOICES.bool)
    case 'marked-amounts':
      return text('הסכומים בשקלים', 'כמה סכומים: מופרדים ברווח.', 'numeric')
    case 'marked-float':
      return text('המספר', 'חצאים בנקודה, למשל 3.5.', 'decimal')
    case 'marked-int':
      return text('המספר', field === 'floor' ? 'קרקע 0, מרתף -1.' : undefined, 'numeric')
    case 'marked-date':
      return (
        <>
          {radios('הכניסה', [
            ['immediate', 'מיידית'],
            ['date', 'בתאריך'],
          ])}
          {draft.choice === 'date' && (
            <Labelled id={`${id}-text`} label="התאריך">
              <input id={`${id}-text`} type="date" value={draft.text} onChange={(event) => set({ text: event.target.value })} />
            </Labelled>
          )}
        </>
      )
    case 'marked-fee':
      return (
        <>
          {radios('הסכום', [
            ['amount', 'סכום'],
            ['included', 'כלול במחיר'],
          ])}
          {draft.choice === 'amount' && text('הסכום בשקלים', undefined, 'numeric')}
        </>
      )
    default:
      return null
  }
}

function Radios({
  name,
  legend,
  choices,
  value,
  onChange,
}: {
  name: string
  legend: string
  choices: [string, string][]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <fieldset className="radios">
      <legend>{legend}</legend>
      {choices.map(([choice, words]) => (
        <label key={choice} className="radio">
          <input type="radio" name={name} value={choice} checked={value === choice} onChange={() => onChange(choice)} />
          <span>{words}</span>
        </label>
      ))}
    </fieldset>
  )
}

function Labelled({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="tfield">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <p className="tfield-hint">{hint}</p>}
    </div>
  )
}
