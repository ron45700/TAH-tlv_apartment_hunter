// The page's formatters: values into Hebrew words, nothing more (PHASE_3.md 3.7 (c); BASELINE.md §6).
// No rule lives here: which colour a field takes, the glow and the tier's words come from the API.
// Every function is pure, so format.test.ts covers it without a browser.

import type { Kind, ListingFields, Marked } from './types'

export const NOT_STATED = 'לא צוין'
export const UNCLEAR = 'לא ברור'

const number = new Intl.NumberFormat('en-US')

/** A shekel amount, "₪5,500". */
export function shekels(amount: number): string {
  return `₪${number.format(amount)}`
}

/** The price (#95): every amount the post gives, "₪5,000/5,500"; `null` when not written (the
 *  card shows the important-missing badge instead). */
export function formatPrice(price: Marked<number[]>): string | null {
  if (price.state === 'unclear') return 'המחיר לא ברור'
  if (price.state !== 'written' || !price.value?.length) return null
  const [first, ...rest] = price.value
  return [shekels(first), ...rest.map((amount) => number.format(amount))].join('/')
}

export interface StatText {
  text: string
  /** A grey line under the value ("סה״כ לא צוין"), #332 point 27. */
  note?: string
  /** The value is not written: shown as "לא צוין" in grey (#321). */
  missing?: boolean
}

/** Rooms on the closed card. A room post reads "1/N" (#325); with the total not written, "1" and a
 *  grey "סה״כ לא צוין" under it (#332). A whole apartment reads its total. */
export function roomsClosed(kind: Kind | null, rooms: Marked<number>): StatText {
  if (kind === 'room') {
    if (rooms.state === 'written' && rooms.value !== null) return { text: `1/${rooms.value}` }
    return { text: '1', note: `סה״כ ${rooms.state === 'unclear' ? UNCLEAR : NOT_STATED}` }
  }
  return valueOrMissing(rooms, String)
}

/** Rooms inside the opened post (#120): "חדר 1 מתוך N", or "חדר" with no "of" when the total is
 *  not written; a whole apartment, "3.5 חדרים". */
export function roomsOpen(kind: Kind | null, rooms: Marked<number>): StatText {
  if (kind === 'room') {
    if (rooms.state === 'written' && rooms.value !== null) return { text: `חדר 1 מתוך ${rooms.value}` }
    return { text: 'חדר' }
  }
  return valueOrMissing(rooms, (value) => `${value} חדרים`)
}

/** The size inside the opened post (#99, #121): on a room post "X מ״ר לחדר, מתוך Y" when both
 *  are written, "X מ״ר לחדר" when only the room's is, and the apartment's alone named as such. */
export function sizeOpen(kind: Kind | null, size: Marked<number>, room: Marked<number>): StatText {
  const apartment = written(size)
  if (kind === 'room') {
    const own = written(room)
    if (own !== null && apartment !== null) return { text: `${own} מ״ר לחדר, מתוך ${apartment}` }
    if (own !== null) return { text: `${own} מ״ר לחדר` }
    if (apartment !== null) return { text: `${apartment} מ״ר (כל הדירה)` }
    return missingOf(size.state === 'unclear' || room.state === 'unclear')
  }
  return valueOrMissing(size, (value) => `${value} מ״ר`)
}

/** The size on the closed card's narrow stat: on a room post "12/80" (the room of the apartment),
 *  "12" (the room's), or "80" with a grey "כל הדירה" under it (the apartment's alone); "80" on a
 *  whole apartment. */
export function sizeClosed(kind: Kind | null, size: Marked<number>, room: Marked<number>): StatText {
  const apartment = written(size)
  if (kind === 'room') {
    const own = written(room)
    if (own !== null && apartment !== null) return { text: `${own}/${apartment}` }
    if (own !== null) return { text: String(own) }
    if (apartment !== null) return { text: String(apartment), note: 'כל הדירה' }
    return missingOf(size.state === 'unclear' || room.state === 'unclear')
  }
  return valueOrMissing(size, String)
}

/** One floor: 0 the ground floor, -1 the basement (#98). */
export function floorName(floor: number): string {
  if (floor === 0) return 'קרקע'
  if (floor === -1) return 'מרתף'
  return String(floor)
}

/** The floor, "X/Y" only when the building's floors are written (#98, #106). */
export function formatFloor(floor: Marked<number>, floors: Marked<number>): StatText {
  const total = written(floors)
  return valueOrMissing(floor, (value) => (total === null ? floorName(value) : `${floorName(value)}/${total}`))
}

/** The entry date: the text as the poster wrote it (#96). Its year is never displayed (#115): when
 *  only the comparable value is known (a corrected date), it reads "D.M". `null` when not written
 *  (the card shows the important-missing badge). */
export function formatEntry(fields: Pick<ListingFields, 'entry_date' | 'entry_date_written'>): string | null {
  const { entry_date: entry, entry_date_written: text } = fields
  if (entry.state === 'not_written') return null
  if (entry.state === 'unclear') return text ?? `תאריך הכניסה ${UNCLEAR}`
  if (text) return text
  if (entry.value === 'immediate') return 'כניסה מיידית'
  return entry.value ? dayAndMonth(entry.value) : null
}

/** The entry date beside a label that already says "כניסה": a leading word "כניסה" dropped
 *  ("כניסה מיידית" reads "מיידית"; #485). Display only: the stored text stays verbatim (#96). */
export function withoutEntryWord(text: string): string {
  const rest = text.replace(/^\s*כניסה(?=[\s:\-–]|$)[\s:\-–]*/, '')
  return rest.trim() ? rest : text
}

/** "2026-11-01" as "1.11": day and month, never the year (#115). */
export function dayAndMonth(isoDate: string): string {
  const [, month, day] = isoDate.split('-').map(Number)
  return `${day}.${month}`
}

/** Arnona or the house committee (#101, #116): the amount, "כלול" when included. */
export function formatFee(fee: Marked<number | 'included'>): StatText {
  if (fee.state === 'unclear') return { text: UNCLEAR }
  if (fee.state !== 'written' || fee.value === null) return { text: NOT_STATED, missing: true }
  return { text: fee.value === 'included' ? 'כלול' : shekels(fee.value) }
}

/** The last publication, relative (#122): minutes up to an hour, hours up to 24 hours, days after
 *  that. */
export function relativeTime(iso: string, now: Date): string {
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(iso).getTime()) / 60000))
  if (minutes < 1) return 'עכשיו'
  if (minutes < 60) return ago(minutes, 'דקה', 'שתי דקות', 'דקות')
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return ago(hours, 'שעה', 'שעתיים', 'שעות')
  return ago(Math.floor(hours / 24), 'יום', 'יומיים', 'ימים')
}

function ago(count: number, one: string, two: string, many: string): string {
  if (count === 1) return `לפני ${one}`
  if (count === 2) return `לפני ${two}`
  return `לפני ${count} ${many}`
}

const ISRAEL = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Jerusalem',
  day: 'numeric',
  month: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/** A moment in Israel time, "13.10, 12:00" (invariant 9: the conversion happens at display only). */
export function israelTime(iso: string): string {
  const parts = Object.fromEntries(ISRAEL.formatToParts(new Date(iso)).map((p) => [p.type, p.value]))
  return `${Number(parts.day)}.${Number(parts.month)}, ${parts.hour}:${parts.minute}`
}

/** "פורסם N פעמים" on its own line under the time, only after a repost (#340). */
export function publishedTimes(count: number): string | null {
  return count > 1 ? `פורסם ${count} פעמים` : null
}

/** The carousel's position, "1/5" (#332 point 30). */
export function photoPosition(index: number, total: number): string {
  return `${index + 1}/${total}`
}

/** A phone as `name-number` when the post gave a name (BASELINE.md §6). */
export function phoneLabel(phone: string, name: string | null): string {
  return name ? `${name}-${phone}` : phone
}

/** The kind line (§8: every card says the option it answers): the kind in words, "סאבלט" for a
 *  sublet; a kind that is unclear or not written is marked with the option it is shown as (#273,
 *  #332). The one name "דירה שלמה" everywhere (#339). */
export function kindLine(
  kind: Kind | null,
  kindMarked: boolean,
  shownAs: Kind | null,
  sublet: boolean,
): { text: string; unclear: boolean } {
  const names: Record<Kind, string> = { room: 'חדר בדירת שותפים', whole_apartment: 'דירה שלמה' }
  const short: Record<Kind, string> = { room: 'חדר', whole_apartment: 'דירה שלמה' }
  const tail = sublet ? ' · סאבלט' : ''
  if (kindMarked || kind === null) {
    const as = shownAs ? ` · מוצג כ: ${short[shownAs]}` : ''
    return { text: `סוג לא ברור${as}${tail}`, unclear: true }
  }
  return { text: `${names[kind]}${tail}`, unclear: false }
}

/** The location line: the areas' names, then the streets as written (§7); no area with a street,
 *  "האזור לא ברור"; nothing at all, "מיקום: לא צוין" (#110, #321). */
export function locationLine(fields: Pick<ListingFields, 'areas' | 'streets' | 'stated_area_names'>): string {
  const areas = fields.areas.map((area) => area.name)
  if (areas.length) return [...areas, ...fields.streets].join(' · ')
  const given = [...fields.stated_area_names, ...fields.streets]
  if (given.length) return ['האזור לא ברור', ...given].join(' · ')
  return `מיקום: ${NOT_STATED}`
}

export interface ChipWords {
  field: string
  text: string
}

// field: [the positive value's words, the negative value's, the field's name, the positive value]
const YES_NO: [keyof ListingFields, string, string, string, boolean][] = [
  ['broker', 'ללא תיווך', 'בתיווך', 'תיווך', false],
  ['balcony', 'מרפסת', 'אין מרפסת', 'מרפסת', true],
  ['parking', 'חניה', 'אין חניה', 'חניה', true],
  ['elevator', 'מעלית', 'אין מעלית', 'מעלית', true],
  ['air_conditioning', 'מיזוג', 'אין מיזוג', 'מיזוג', true],
]
const FURNISHED = { yes: 'מרוהטת', partial: 'מרוהטת חלקית', no: 'לא מרוהטת' } as const

/** The feature chips' words, in their order (§6): each value in words, so no chip needs a glyph
 *  (#323); not written "X: לא צוין" (#321). Which words describe the known positive is wording;
 *  the chip's colour is the API's. */
export function featureChips(fields: ListingFields): ChipWords[] {
  const chips = YES_NO.map(([field, positive, negative, name, good]) => {
    const marked = fields[field] as Marked<boolean>
    if (marked.state === 'not_written') return { field, text: `${name}: ${NOT_STATED}` }
    if (marked.state === 'unclear' || marked.value === null) return { field, text: `${name}: ${UNCLEAR}` }
    return { field, text: marked.value === good ? positive : negative }
  })
  const furnished = fields.furnished
  chips.push({
    field: 'furnished',
    text:
      furnished.state === 'written' && furnished.value
        ? FURNISHED[furnished.value]
        : `ריהוט: ${furnished.state === 'unclear' ? UNCLEAR : NOT_STATED}`,
  })
  return chips
}

/** The closed card keeps only the green chips (#326, #332 point 28). */
export function closedChips(fields: ListingFields, colours: Record<string, string>): ChipWords[] {
  return featureChips(fields).filter((chip) => colours[chip.field] === 'green')
}

function written(marked: Marked<number>): number | null {
  return marked.state === 'written' ? marked.value : null
}

function valueOrMissing(marked: Marked<number>, show: (value: number) => string): StatText {
  if (marked.state === 'written' && marked.value !== null) return { text: show(marked.value) }
  return missingOf(marked.state === 'unclear')
}

function missingOf(unclear: boolean): StatText {
  return unclear ? { text: UNCLEAR } : { text: NOT_STATED, missing: true }
}
