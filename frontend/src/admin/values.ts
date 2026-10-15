// The correction's value form (3.8 (h), step 5): each reportable field's Gate B shape, a draft the
// form edits, and the two directions between them. Pure: the server checks the value by its Gate B
// type and as the whole post (#284, #405) and says what is wrong; this only builds the JSON.

export type MarkedState = 'written' | 'not_written' | 'unclear'

export type Kind =
  | 'enum'
  | 'marked-enum'
  | 'marked-bool'
  | 'marked-amounts'
  | 'marked-date'
  | 'marked-float'
  | 'marked-int'
  | 'marked-fee'
  | 'areas'
  | 'lines'
  | 'city'
  | 'phones'

export const KINDS: Record<string, Kind> = {
  post_nature: 'enum',
  apartment_kind: 'marked-enum',
  price: 'marked-amounts',
  entry_date: 'marked-date',
  rooms: 'marked-float',
  floor: 'marked-int',
  building_floors: 'marked-int',
  size_sqm: 'marked-float',
  room_size_sqm: 'marked-float',
  broker: 'marked-bool',
  balcony: 'marked-bool',
  parking: 'marked-bool',
  elevator: 'marked-bool',
  air_conditioning: 'marked-bool',
  furnished: 'marked-enum',
  arnona: 'marked-fee',
  house_committee: 'marked-fee',
  gender: 'enum',
  areas: 'areas',
  streets: 'lines',
  other_city: 'city',
  phone_names: 'phones',
}

/** The choices of a field with a closed list: Gate B's values with their words. */
export const CHOICES: Record<string, [string, string][]> = {
  post_nature: [
    ['rental_offer', 'השכרה'],
    ['sublet_offer', 'סאבלט'],
    ['seeking', 'מחפשים דירה'],
    ['for_sale', 'מכירה'],
    ['not_listing', 'לא מודעת דירה'],
  ],
  apartment_kind: [
    ['room', 'חדר'],
    ['whole_apartment', 'דירה שלמה'],
  ],
  furnished: [
    ['yes', 'מרוהטת'],
    ['partial', 'חלקית'],
    ['no', 'לא מרוהטת'],
  ],
  gender: [
    ['no_restriction', 'ללא הגבלה'],
    ['women_preferred', 'עדיפות לבנות'],
    ['women_only', 'נשים בלבד'],
  ],
  bool: [
    ['true', 'כן'],
    ['false', 'לא'],
  ],
}

export interface Draft {
  state: MarkedState
  /** A choice: an enum value, "true"/"false", "immediate" or "date", "included" or "amount". */
  choice: string
  /** A number, the amounts, a date, a city, or the streets one per line. */
  text: string
  areas: number[]
  /** A name for each of the post's phones. */
  names: Record<string, string>
}

export function isMarked(kind: Kind): boolean {
  return kind.startsWith('marked-')
}

/** The draft a stored value opens the form with. */
export function draftOf(field: string, value: unknown, phones: string[]): Draft {
  const kind = KINDS[field]
  const draft: Draft = { state: 'written', choice: '', text: '', areas: [], names: {} }
  if (kind === 'enum') return { ...draft, choice: String(value ?? '') }
  if (kind === 'areas') return { ...draft, areas: Array.isArray(value) ? (value as number[]) : [] }
  if (kind === 'lines') return { ...draft, text: Array.isArray(value) ? (value as string[]).join('\n') : '' }
  if (kind === 'city') return { ...draft, text: typeof value === 'string' ? value : '' }
  if (kind === 'phones') {
    const names: Record<string, string> = Object.fromEntries(phones.map((phone) => [phone, '']))
    for (const entry of (value as { phone: string; name: string }[] | null) ?? []) names[entry.phone] = entry.name
    return { ...draft, names }
  }
  const marked = (value ?? { state: 'not_written', value: null }) as { state: MarkedState; value: unknown }
  const inner = marked.value
  const base = { ...draft, state: marked.state }
  if (inner === null || inner === undefined) return { ...base, choice: defaultChoice(kind) }
  switch (kind) {
    case 'marked-bool':
    case 'marked-enum':
      return { ...base, choice: String(inner) }
    case 'marked-amounts':
      return { ...base, text: (inner as number[]).join(' ') }
    case 'marked-date':
      return inner === 'immediate' ? { ...base, choice: 'immediate' } : { ...base, choice: 'date', text: String(inner) }
    case 'marked-fee':
      return inner === 'included' ? { ...base, choice: 'included' } : { ...base, choice: 'amount', text: String(inner) }
    default:
      return { ...base, text: String(inner) }
  }
}

function defaultChoice(kind: Kind): string {
  if (kind === 'marked-date') return 'date'
  if (kind === 'marked-fee') return 'amount'
  return ''
}

/** The value a draft stands for, in Gate B's JSON; `null` when a written value is not complete. */
export function valueOf(field: string, draft: Draft): unknown {
  const kind = KINDS[field]
  switch (kind) {
    case 'enum':
      return draft.choice || null
    case 'areas':
      return [...new Set(draft.areas)].sort((a, b) => a - b)
    case 'lines':
      return draft.text
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
    case 'city':
      return draft.text.trim() || null
    case 'phones':
      return Object.entries(draft.names)
        .filter(([, name]) => name.trim())
        .map(([phone, name]) => ({ phone, name: name.trim() }))
  }
  if (draft.state !== 'written') return { state: draft.state, value: null }
  const inner = writtenValue(kind, draft)
  return inner === null ? null : { state: 'written', value: inner }
}

function writtenValue(kind: Kind, draft: Draft): unknown {
  const text = draft.text.trim()
  switch (kind) {
    case 'marked-bool':
      return draft.choice === 'true' ? true : draft.choice === 'false' ? false : null
    case 'marked-enum':
      return draft.choice || null
    case 'marked-amounts': {
      const amounts = text
        .split(/\s+/)
        .map((token) => token.replace(/[^\d]/g, ''))
        .filter(Boolean)
        .map(Number)
      return amounts.length ? amounts : null
    }
    case 'marked-date':
      return draft.choice === 'immediate' ? 'immediate' : /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : null
    case 'marked-fee':
      if (draft.choice === 'included') return 'included'
      return /^\d+$/.test(text) ? Number(text) : null
    case 'marked-int':
      return /^-?\d+$/.test(text) ? Number(text) : null
    case 'marked-float':
      return text !== '' && Number.isFinite(Number(text)) ? Number(text) : null
    default:
      return null
  }
}
