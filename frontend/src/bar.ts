// The filter bar's and the preferences page's values: a profile's shape (PHASE_3.md 3.7 (e)). The
// server validates every value with the profile's own rules and evaluates the posts (#330 point 18);
// this module only holds the shape, compares it, copies between the two options (#272) and puts the
// values into words. Pure, so bar.test.ts covers it without a browser.
import { shekels } from './format'

export type Level = 'preference' | 'critical'
export type OptionName = 'room' | 'whole_apartment'

export interface Range {
  min: number | null
  max: number | null
  level: Level
}

/** The entry date: a range, or with `immediate` the chip "מיידי", no dates: entry no later than 3
 *  calendar months from the day the server evaluates, rolling (#458, #468). */
export interface DateRange {
  earliest: string | null
  latest: string | null
  immediate: boolean
  level: Level
}

export interface SearchOption {
  enabled: boolean
  areas: number[]
  price_min: number | null
  price_max: number | null
  hide_women_only: boolean
  rooms: Range | null
  floor: Range | null
  size_sqm: Range | null
  broker: Level | null
  parking: Level | null
  balcony: Level | null
  entry_date: DateRange | null
}

export interface Bar {
  room: SearchOption
  whole_apartment: SearchOption
  include_sublets: boolean
}

export const OPTIONS: readonly OptionName[] = ['room', 'whole_apartment']

/** The kind's one name everywhere (#339). */
export const OPTION_NAMES: Record<OptionName, string> = {
  room: 'חדר בדירת שותפים',
  whole_apartment: 'דירה שלמה',
}

export const FEATURES = ['broker', 'parking', 'balcony'] as const
export type Feature = (typeof FEATURES)[number]

/** The fixed wanted value of each feature (#269), in words. */
export const FEATURE_NAMES: Record<Feature, string> = {
  broker: 'ללא תיווך',
  parking: 'חניה',
  balcony: 'מרפסת',
}

/** A new profile's option (#268): on, nothing set, "women only" hidden. A guest's bar starts so. */
export function emptyOption(): SearchOption {
  return {
    enabled: true,
    areas: [],
    price_min: null,
    price_max: null,
    hide_women_only: true,
    rooms: null,
    floor: null,
    size_sqm: null,
    broker: null,
    parking: null,
    balcony: null,
    entry_date: null,
  }
}

export function emptyBar(): Bar {
  return { room: emptyOption(), whole_apartment: emptyOption(), include_sublets: false }
}

/** The bar's three values out of anything shaped like a profile (the saved one carries more). */
export function barOf(profile: Bar): Bar {
  return {
    room: profile.room,
    whole_apartment: profile.whole_apartment,
    include_sublets: profile.include_sublets,
  }
}

/** A bar kept in the tab before the chip became a marker (#468) has no `immediate`: it reads as
 *  false, its dates as they were. */
export function currentBar(bar: Bar): Bar {
  const entry = (option: SearchOption): SearchOption =>
    option.entry_date && option.entry_date.immediate === undefined
      ? { ...option, entry_date: { ...option.entry_date, immediate: false } }
      : option
  return { ...bar, room: entry(bar.room), whole_apartment: entry(bar.whole_apartment) }
}

/** The chip "מיידי" (#458): the marker, at the range's level. */
export function immediateEntry(range: DateRange | null): DateRange {
  return { earliest: null, latest: null, immediate: true, level: range?.level ?? 'preference' }
}

/** Field by field, whatever the order of the keys: "changed" is computed so (3.7 (e)). */
export function sameBar(a: Bar, b: Bar): boolean {
  return canonical(barOf(a)) === canonical(barOf(b))
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => (a < b ? -1 : 1))
    return `{${entries.map(([key, inner]) => `${JSON.stringify(key)}:${canonical(inner)}`).join(',')}}`
  }
  return JSON.stringify(value)
}

/** One option changed, the rest of the bar kept. */
export function withOption(bar: Bar, name: OptionName, change: Partial<SearchOption>): Bar {
  return { ...bar, [name]: { ...bar[name], ...change } }
}

/** "Copy from the other option" (#272, #317): every value but on/off; never the sqm range into the
 *  room option, and the whole apartment's own sqm range is kept; the sublet switch is the profile's
 *  and is not copied. */
export function copyFromOther(bar: Bar, into: OptionName): Bar {
  const from = bar[other(into)]
  const target = bar[into]
  return withOption(bar, into, {
    ...from,
    areas: [...from.areas],
    enabled: target.enabled,
    size_sqm: into === 'room' ? null : target.size_sqm,
  })
}

export function other(name: OptionName): OptionName {
  return name === 'room' ? 'whole_apartment' : 'room'
}

/** Areas as the profile keeps them: sorted, no repeats. */
export function toggleAreas(areas: number[], numbers: number[], on: boolean): number[] {
  const set = new Set(areas)
  for (const number of numbers) {
    if (on) set.add(number)
    else set.delete(number)
  }
  return [...set].sort((a, b) => a - b)
}

/** A range's new end; both ends empty means "don't care" (null), as the profile requires. */
export function setRangeEnd(range: Range | null, end: 'min' | 'max', value: number | null): Range | null {
  const next = { min: range?.min ?? null, max: range?.max ?? null, level: range?.level ?? 'preference', [end]: value }
  return next.min === null && next.max === null ? null : next
}

export function setDateEnd(range: DateRange | null, end: 'earliest' | 'latest', value: string | null): DateRange | null {
  const next = {
    earliest: range?.earliest ?? null,
    latest: range?.latest ?? null,
    immediate: false, // a date typed ends the chip's marker
    level: range?.level ?? 'preference',
    [end]: value || null,
  }
  return next.earliest === null && next.latest === null ? null : next
}

/** How far "עד תאריך" is filled after "מתאריך" (Ron, 2026-10-18): three calendar months. */
export const ENTRY_SPAN_MONTHS = 3

/** A date `months` calendar months on: the same day, or the month's last day when it has fewer
 *  (30.11 + 3 → 28.2). YYYY-MM-DD in and out. */
export function addMonths(iso: string, months: number): string {
  const [year, month, day] = iso.split('-').map(Number)
  const index = year * 12 + month - 1 + months
  const y = Math.floor(index / 12)
  const m = index - y * 12 + 1
  const leap = y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0)
  const last = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
  const pad = (n: number, width: number) => String(n).padStart(width, '0')
  return `${pad(y, 4)}-${pad(m, 2)}-${pad(Math.min(day, last), 2)}`
}

/** "מתאריך" typed (Ron, 2026-10-18): when "עד תאריך" is empty it is filled with the same date
 *  three calendar months on, a fixed date the user can change. It keeps following "מתאריך" while
 *  it still holds the date filled for the previous one (a date box reports each year digit as it is
 *  typed: 0002, 0020, 0202, 2026), and goes with it when "מתאריך" is cleared; a date the user set
 *  in "עד תאריך" is never touched. */
export function setEarliest(range: DateRange | null, value: string): DateRange | null {
  const before = range?.immediate ? null : (range?.earliest ?? null)
  const latest = range?.immediate ? null : (range?.latest ?? null)
  const filled = latest === null || (before !== null && latest === addMonths(before, ENTRY_SPAN_MONTHS))
  if (!filled) return setDateEnd(range, 'earliest', value)
  if (!value) return null
  return {
    earliest: value,
    latest: addMonths(value, ENTRY_SPAN_MONTHS),
    immediate: false,
    level: range?.level ?? 'preference',
  }
}

/** The controls of one option that hold a value: what "סינון (3)" counts. "Women only" counts when
 *  the posts are shown (the default hides them). */
export function heldCount(option: SearchOption): number {
  return (
    Number(option.areas.length > 0) +
    Number(option.price_min !== null || option.price_max !== null) +
    Number(option.rooms !== null) +
    moreCount(option)
  )
}

/** The controls inside "עוד" that hold a value. */
export function moreCount(option: SearchOption): number {
  return (
    Number(option.floor !== null) +
    Number(option.size_sqm !== null) +
    Number(option.entry_date !== null) +
    FEATURES.filter((feature) => option[feature] !== null).length +
    Number(!option.hide_women_only)
  )
}

export function barHeldCount(bar: Bar): number {
  return OPTIONS.filter((name) => bar[name].enabled).reduce((sum, name) => sum + heldCount(bar[name]), 0)
}

const MUST = 'חובה'
const number = new Intl.NumberFormat('en-US')

function withLevel(text: string, level: Level): string {
  return level === 'critical' ? `${text}, ${MUST}` : text
}

function span(min: number | null, max: number | null, show: (n: number) => string): string {
  if (min !== null && max !== null) return min === max ? show(min) : `${show(min)}–${show(max)}`
  if (min !== null) return `מ-${show(min)}`
  return `עד ${show(max as number)}`
}

/** The areas control in words: the one area's name, or how many. */
export function areasWords(areas: number[], names: ReadonlyMap<number, string>): string | null {
  if (areas.length === 0) return null
  if (areas.length === 1) return names.get(areas[0]) ?? '1 אזור'
  return `${areas.length} אזורים`
}

/** "מחיר עד ₪5,500" (3.7 (e)); the price is critical by the rules, so it carries no level word. */
export function priceWords(option: SearchOption): string | null {
  if (option.price_min === null && option.price_max === null) return null
  return `מחיר ${span(option.price_min, option.price_max, shekels)}`
}

export function roomsWords(rooms: Range | null): string | null {
  if (!rooms) return null
  return withLevel(`חדרים ${span(rooms.min, rooms.max, (n) => number.format(n))}`, rooms.level)
}

export function floorWords(floor: Range | null): string | null {
  if (!floor) return null
  return withLevel(`קומה ${span(floor.min, floor.max, floorName)}`, floor.level)
}

export function floorName(floor: number): string {
  if (floor === -1) return 'מרתף'
  if (floor === 0) return 'קרקע'
  return String(floor)
}

export function sizeWords(size: Range | null): string | null {
  if (!size) return null
  return withLevel(`${span(size.min, size.max, (n) => number.format(n))} מ״ר`, size.level)
}

/** The entry date in words; dates as day.month, the year never shown (#115). */
export function entryWords(entry: DateRange | null): string | null {
  if (!entry) return null
  const day = (iso: string) => {
    const [, month, date] = iso.split('-')
    return `${Number(date)}.${Number(month)}`
  }
  let text: string
  if (entry.immediate) text = 'כניסה מיידית'
  else if (entry.earliest !== null && entry.latest !== null) text = `כניסה ${day(entry.earliest)}–${day(entry.latest)}`
  else if (entry.earliest !== null) text = `כניסה מ-${day(entry.earliest)}`
  else text = `כניסה עד ${day(entry.latest as string)}`
  return withLevel(text, entry.level)
}

export function featureWords(option: SearchOption, feature: Feature): string | null {
  const level = option[feature]
  return level === null ? null : withLevel(FEATURE_NAMES[feature], level)
}

/** Every value of one option in words, for the preferences page's summary. */
export function optionSummary(option: SearchOption, names: ReadonlyMap<number, string>): string[] {
  return [
    areasWords(option.areas, names),
    priceWords(option),
    roomsWords(option.rooms),
    floorWords(option.floor),
    sizeWords(option.size_sqm),
    entryWords(option.entry_date),
    ...FEATURES.map((feature) => featureWords(option, feature)),
    option.hide_women_only ? null : 'כולל מודעות לנשים בלבד',
  ].filter((words): words is string => words !== null)
}

// The rules a bar can break, in words (the server's 422 names the rule, never a value).
const RULE_WORDS: [RegExp, string][] = [
  [/price_min must not exceed price_max/, 'המחיר המינימלי גבוה מהמקסימלי'],
  [/earliest must not be after latest/, 'תאריך הכניסה המוקדם מאוחר מהמאוחר'],
  [/immediate entry date has no dates/, 'כניסה מיידית בלי תאריכים'],
  [/min must not exceed max/, 'בטווח, הערך הנמוך גבוה מהגבוה'],
  [/no sqm filter/, 'בחיפוש חדר אין סינון לפי מ״ר'],
  [/whole or half/, 'חדרים: מספר שלם או חצי'],
  [/lowest floor/, 'הקומה הנמוכה ביותר היא מרתף'],
  [/areas are/, 'אזור לא מוכר'],
]

/** The server's 422 for a bar, in words: which option and which rule. */
export function refusalWords(detail: unknown): string {
  const text = typeof detail === 'string' ? detail : ''
  const rules = text
    .split('; ')
    .map((part) => {
      const rule = RULE_WORDS.find(([pattern]) => pattern.test(part))
      if (!rule) return null
      const option = OPTIONS.find((name) => part.startsWith(`${name}.`) || part.startsWith(`${name}:`))
      return option ? `${OPTION_NAMES[option]}: ${rule[1]}` : rule[1]
    })
    .filter((words): words is string => words !== null)
  const unique = [...new Set(rules)]
  return unique.length ? `הסינון לא תקין. ${unique.join('. ')}.` : 'הסינון לא תקין. בדקו את הערכים.'
}
