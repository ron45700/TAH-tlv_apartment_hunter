// The admin's words and groupings (3.8 (c)). Pure: no fetch, no rule of the server's. The reason's
// family colours its chip by who rejected the post: before the model, the model, or a user.
import type { Flag, Mark, Reason, Row } from './types'

export type Family = 'pre' | 'model' | 'user'

export const REASON_FAMILY: Record<Reason, Family> = {
  no_text: 'pre',
  no_images: 'pre',
  other_city: 'model',
  seeking: 'model',
  for_sale: 'model',
  not_listing: 'model',
  flagged: 'user',
  misclassified: 'user',
}

/** Gate E's order. */
export const REASON_ORDER: Reason[] = [
  'no_text',
  'no_images',
  'other_city',
  'seeking',
  'for_sale',
  'not_listing',
  'flagged',
  'misclassified',
]

export const REASON_NAMES: Record<Reason, string> = {
  no_text: 'אין טקסט',
  no_images: 'אין תמונות',
  other_city: 'עיר אחרת',
  seeking: 'מחפשים דירה',
  for_sale: 'למכירה',
  not_listing: 'לא מודעת דירה',
  flagged: 'סומנה כמשקרת',
  misclassified: 'דווח סיווג שגוי',
}

export const MARK_WORDS: Record<Mark, string> = {
  not_removed: 'הדיווח נשמר, המודעה עדיין ברשימה',
  restore_unfinished: 'השחזור לא הושלם',
}

export const SOURCE_WORDS: Record<'correction' | 'native_location' | 'model', string> = {
  correction: 'לפי תיקון שלך',
  native_location: 'לפי שדה המיקום של פייסבוק',
  model: 'לפי המודל',
}

const WORDS: Record<string, string> = {
  rental_offer: 'השכרה',
  sublet_offer: 'סאבלט',
  seeking: 'מחפשים',
  for_sale: 'מכירה',
  not_listing: 'לא מודעה',
  room: 'חדר',
  whole_apartment: 'דירה שלמה',
  immediate: 'מיידי',
  yes: 'כן',
  partial: 'חלקי',
  no: 'לא',
  included: 'כלול',
  no_restriction: 'ללא הגבלה',
  women_preferred: 'עדיפות לבנות',
  women_only: 'נשים בלבד',
}

/** A field's value in words, as Gate B stores it: a `Marked` value with its state, a list, a yes or
 * no, an enum. Only how the stored value reads; never a rule. */
export function valueWords(value: unknown, areaNames?: ReadonlyMap<number, string>, field?: string): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'כן' : 'לא'
  if (Array.isArray(value)) {
    if (value.length === 0) return '—'
    if (field === 'areas' && areaNames) return value.map((n) => areaNames.get(n as number) ?? String(n)).join(', ')
    if (field === 'phone_names') {
      return value
        .map((entry) => {
          const { phone, name } = entry as { phone: string; name: string }
          return `${name} (${phone})`
        })
        .join(', ')
    }
    return value.map((item) => valueWords(item)).join(', ')
  }
  if (typeof value === 'object') {
    const marked = value as { state?: string; value?: unknown }
    if (marked.state === 'not_written') return 'לא צוין'
    if (marked.state === 'unclear') return marked.value == null ? 'לא ברור' : `לא ברור (${valueWords(marked.value)})`
    if ('value' in marked) return valueWords(marked.value)
    return JSON.stringify(value)
  }
  return WORDS[String(value)] ?? String(value)
}

export interface FlagAction {
  key: string
  flag: Flag
  rows: Row[]
}

/** The flags list's rows as flag actions (#393): consecutive rows with the same user and time are
 * one "lied" flag on one card. The server orders them so each action's rows stand together. */
export function flagActions(rows: Row[]): FlagAction[] {
  const actions: FlagAction[] = []
  for (const row of rows) {
    const flag = row.flag ?? { by: '', at: null, note: null }
    const key = `${flag.by}\u0000${flag.at ?? ''}`
    const last = actions[actions.length - 1]
    if (last && last.key === key) last.rows.push(row)
    else actions.push({ key, flag, rows: [row] })
  }
  return actions
}
