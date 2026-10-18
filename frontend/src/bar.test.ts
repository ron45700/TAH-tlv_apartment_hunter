// The bar's and the preferences page's rules (PHASE_3.md 3.7 (e), (l) 10): "changed" field by field,
// "copy from the other option" (#272, #317), "don't care" as null, the count of held controls, the
// values in words (no glyph, #323), Israel's date for "immediate" (#270), a 422 in words.
import { describe, expect, it } from 'vitest'
import {
  addMonths,
  barHeldCount,
  copyFromOther,
  emptyBar,
  emptyOption,
  entryWords,
  floorWords,
  heldCount,
  israelToday,
  optionSummary,
  priceWords,
  refusalWords,
  roomsWords,
  sameBar,
  setDateEnd,
  setEarliest,
  setRangeEnd,
  toggleAreas,
  withOption,
  type Bar,
} from './bar'

const names = new Map([
  [30, 'הצפון הישן - צפון'],
  [31, 'הצפון הישן - דרום'],
])

function filled(): Bar {
  return {
    room: {
      ...emptyOption(),
      areas: [30, 31],
      price_max: 4000,
      rooms: { min: 3, max: 4, level: 'critical' },
      broker: 'preference',
      entry_date: { earliest: null, latest: '2026-11-01', level: 'preference' },
      hide_women_only: false,
    },
    whole_apartment: {
      ...emptyOption(),
      enabled: false,
      price_min: 6000,
      size_sqm: { min: 60, max: null, level: 'preference' },
    },
    include_sublets: true,
  }
}

describe('sameBar: "changed" is compared field by field', () => {
  it('ignores the order of keys and the saved profile\'s other fields', () => {
    const bar = filled()
    const reordered = JSON.parse(
      JSON.stringify({ include_sublets: true, whole_apartment: bar.whole_apartment, room: bar.room }),
    )
    expect(sameBar(bar, reordered)).toBe(true)
    expect(sameBar(bar, { ...bar, updated_at: '2026-10-14T00:00:00+00:00' } as Bar)).toBe(true)
  })

  it('sees one changed value, the sublet switch and a level', () => {
    const bar = filled()
    expect(sameBar(bar, withOption(bar, 'room', { price_max: 4100 }))).toBe(false)
    expect(sameBar(bar, { ...bar, include_sublets: false })).toBe(false)
    expect(sameBar(bar, withOption(bar, 'room', { rooms: { min: 3, max: 4, level: 'preference' } }))).toBe(false)
  })
})

describe('copy from the other option (#272, #317)', () => {
  it('copies every value but on/off into the room option, never the sqm range', () => {
    const bar = filled()
    const copied = copyFromOther(bar, 'room')
    expect(copied.room.enabled).toBe(true) // its own on/off
    expect(copied.room.price_min).toBe(6000)
    expect(copied.room.price_max).toBeNull()
    expect(copied.room.areas).toEqual([])
    expect(copied.room.size_sqm).toBeNull() // never into the room option (#247)
    expect(copied.whole_apartment).toEqual(bar.whole_apartment)
    expect(copied.include_sublets).toBe(true) // the profile's switch, not copied
  })

  it('copying into the whole apartment keeps its own sqm range and on/off', () => {
    const bar = filled()
    const copied = copyFromOther(bar, 'whole_apartment')
    expect(copied.whole_apartment.enabled).toBe(false)
    expect(copied.whole_apartment.size_sqm).toEqual({ min: 60, max: null, level: 'preference' })
    expect(copied.whole_apartment.areas).toEqual([30, 31])
    expect(copied.whole_apartment.rooms).toEqual(bar.room.rooms)
    expect(copied.whole_apartment.hide_women_only).toBe(false)
    copied.whole_apartment.areas.push(5)
    expect(bar.room.areas).toEqual([30, 31]) // a copy, not the same list
  })
})

describe('values as the profile keeps them', () => {
  it('areas sorted with no repeats; a group selected and cleared at once', () => {
    expect(toggleAreas([31], [30, 31, 32], true)).toEqual([30, 31, 32])
    expect(toggleAreas([30, 31, 32, 40], [30, 31, 32], false)).toEqual([40])
  })

  it('a range with both ends empty is "don\'t care"; its level is kept otherwise', () => {
    expect(setRangeEnd(null, 'min', 2)).toEqual({ min: 2, max: null, level: 'preference' })
    expect(setRangeEnd({ min: 2, max: null, level: 'critical' }, 'max', 3)).toEqual({ min: 2, max: 3, level: 'critical' })
    expect(setRangeEnd({ min: 2, max: null, level: 'critical' }, 'min', null)).toBeNull()
    expect(setDateEnd(null, 'latest', '2026-11-01')).toEqual({ earliest: null, latest: '2026-11-01', level: 'preference' })
    expect(setDateEnd({ earliest: null, latest: '2026-11-01', level: 'preference' }, 'latest', '')).toBeNull()
  })

  it('three calendar months on: the same day, or the last day of a shorter month', () => {
    expect(addMonths('2026-10-18', 3)).toBe('2027-01-18')
    expect(addMonths('2026-11-30', 3)).toBe('2027-02-28')
    expect(addMonths('2027-11-30', 3)).toBe('2028-02-29') // a leap year
    expect(addMonths('2026-12-31', 3)).toBe('2027-03-31')
    expect(addMonths('2026-05-31', 1)).toBe('2026-06-30')
  })

  it('"מתאריך" with "עד תאריך" empty fills it three months on; a set "עד תאריך" is kept (Ron, 2026-10-18)', () => {
    expect(setEarliest(null, '2026-11-01')).toEqual({ earliest: '2026-11-01', latest: '2027-02-01', level: 'preference' })
    const critical = { earliest: null, latest: null, level: 'critical' as const }
    expect(setEarliest(critical, '2026-11-01')).toEqual({ earliest: '2026-11-01', latest: '2027-02-01', level: 'critical' })
    const typed = { earliest: null, latest: '2026-12-15', level: 'preference' as const }
    expect(setEarliest(typed, '2026-11-01')).toEqual({ earliest: '2026-11-01', latest: '2026-12-15', level: 'preference' })
    const changed = { earliest: '2026-11-01', latest: '2027-01-10', level: 'preference' as const }
    expect(setEarliest(changed, '2026-11-05')).toEqual({ earliest: '2026-11-05', latest: '2027-01-10', level: 'preference' })
  })

  it('the filled date follows the year as it is typed, and goes when "מתאריך" is cleared', () => {
    let entry = setEarliest(null, '0002-11-01')
    for (const year of ['0020', '0202', '2026']) entry = setEarliest(entry, `${year}-11-01`)
    expect(entry).toEqual({ earliest: '2026-11-01', latest: '2027-02-01', level: 'preference' })
    expect(setEarliest(entry, '')).toBeNull()
    const typed = { earliest: '2026-11-01', latest: '2026-12-15', level: 'preference' as const }
    expect(setEarliest(typed, '')).toEqual({ earliest: null, latest: '2026-12-15', level: 'preference' })
  })

  it("a new bar is #268's: both on, nothing set, sublets off, women only hidden", () => {
    const bar = emptyBar()
    expect(bar.room.enabled && bar.whole_apartment.enabled).toBe(true)
    expect(bar.include_sublets).toBe(false)
    expect(bar.room.hide_women_only).toBe(true)
    expect(barHeldCount(bar)).toBe(0)
  })

  it('"סינון (N)" counts the controls holding a value, of the options that are on', () => {
    const bar = filled()
    expect(heldCount(bar.room)).toBe(6) // areas, price, rooms, broker, entry date, women only shown
    expect(heldCount(bar.whole_apartment)).toBe(2)
    expect(barHeldCount(bar)).toBe(6) // the whole apartment is off
  })
})

describe('the values in words', () => {
  it('price, rooms and floor; a "must" adds the word, no glyph', () => {
    expect(priceWords({ ...emptyOption(), price_max: 5500 })).toBe('מחיר עד ₪5,500')
    expect(priceWords({ ...emptyOption(), price_min: 4000, price_max: 5500 })).toBe('מחיר ₪4,000–₪5,500')
    expect(priceWords({ ...emptyOption(), price_min: 4000 })).toBe('מחיר מ-₪4,000')
    expect(roomsWords({ min: 2.5, max: 3, level: 'critical' })).toBe('חדרים 2.5–3, חובה')
    expect(roomsWords({ min: 2, max: null, level: 'preference' })).toBe('חדרים מ-2')
    expect(floorWords({ min: -1, max: 0, level: 'preference' })).toBe('קומה מרתף–קרקע')
  })

  it('the entry date: "immediate" is until today; no year (#115)', () => {
    const today = '2026-10-14'
    expect(entryWords({ earliest: null, latest: today, level: 'preference' }, today)).toBe('כניסה מיידית')
    expect(entryWords({ earliest: '2026-11-01', latest: '2026-12-15', level: 'critical' }, today)).toBe(
      'כניסה 1.11–15.12, חובה',
    )
  })

  it('the summary lists every value of an option', () => {
    expect(optionSummary(filled().room, names, '2026-10-14')).toEqual([
      '2 אזורים',
      'מחיר עד ₪4,000',
      'חדרים 3–4, חובה',
      'כניסה עד 1.11',
      'ללא תיווך',
      'כולל מודעות לנשים בלבד',
    ])
    expect(optionSummary({ ...emptyOption(), areas: [30] }, names, '2026-10-14')).toEqual(['הצפון הישן - צפון'])
  })
})

describe('Israel\'s date for "immediate" (#270)', () => {
  it('is the date in Israel, not in UTC', () => {
    expect(israelToday(new Date('2026-10-13T21:30:00Z'))).toBe('2026-10-14') // 00:30 in Israel
    expect(israelToday(new Date('2026-01-14T21:59:00Z'))).toBe('2026-01-14') // 23:59 in winter
  })
})

describe('an invalid bar in words', () => {
  it("names the option and the rule from the server's 422", () => {
    expect(refusalWords('whole_apartment: Value error, price_min must not exceed price_max')).toBe(
      'הסינון לא תקין. דירה שלמה: המחיר המינימלי גבוה מהמקסימלי.',
    )
    expect(refusalWords('room.rooms: Value error, min must not exceed max')).toBe(
      'הסינון לא תקין. חדר בדירת שותפים: בטווח, הערך הנמוך גבוה מהגבוה.',
    )
    expect(refusalWords(undefined)).toBe('הסינון לא תקין. בדקו את הערכים.')
  })
})
