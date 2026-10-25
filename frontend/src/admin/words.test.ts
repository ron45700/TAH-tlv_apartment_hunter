import { describe, expect, it } from 'vitest'
import { firstLoad, nextIds, withPage } from '../paging'
import type { Row } from './types'
import { REASON_FAMILY, REASON_ORDER, flagActions, restoreLabel, valueWords } from './words'

function row(id: string, by: string | null, at: string | null): Row {
  return {
    id,
    state: 'rejected',
    state_words: 'נדחתה',
    reason: 'flagged',
    reason_words: 'סומנה כמשקרת',
    city: null,
    posted_at: '2026-10-13T09:00:00+00:00',
    last_published_at: '2026-10-13T09:00:00+00:00',
    publications: 1,
    text: 'דירה',
    source: 'facebook',
    permalink: 'https://example.invalid',
    photo: null,
    photo_count: 0,
    videos: [],
    failures: 0,
    last_error: null,
    flag: by === null ? null : { by, at, note: null },
    listing: null,
    corrected: [],
    version: `v-${id}`,
  }
}

describe('flag actions (#393)', () => {
  it('groups consecutive rows of one user and time', () => {
    const rows = [row('a', 'dana', 't1'), row('b', 'dana', 't1'), row('c', 'dana', 't2'), row('d', 'noa', 't1')]
    expect(flagActions(rows).map((action) => action.rows.map((r) => r.id))).toEqual([['a', 'b'], ['c'], ['d']])
  })
})

describe('value words', () => {
  it('reads a Marked value by its state', () => {
    expect(valueWords({ state: 'not_written', value: null })).toBe('לא צוין')
    expect(valueWords({ state: 'unclear', value: null })).toBe('לא ברור')
    expect(valueWords({ state: 'written', value: [4500, 5000] })).toBe('4500, 5000')
    expect(valueWords({ state: 'written', value: true })).toBe('כן')
    expect(valueWords({ state: 'written', value: 'partial' })).toBe('חלקי')
  })
  it('names the areas, the phones, the plain enums and the empty values', () => {
    expect(valueWords([30, 31], new Map([[30, 'הצפון הישן']]), 'areas')).toBe('הצפון הישן, 31')
    expect(valueWords([{ phone: '0541234567', name: 'דנה' }], undefined, 'phone_names')).toBe('דנה (0541234567)')
    expect(valueWords('women_only')).toBe('נשים בלבד')
    expect(valueWords(null)).toBe('—')
    expect(valueWords([])).toBe('—')
  })
})

describe('reasons', () => {
  it('every reason has a family, in Gate E order', () => {
    expect(REASON_ORDER.every((reason) => REASON_FAMILY[reason])).toBe(true)
    expect(REASON_ORDER.at(-1)).toBe('misclassified')
  })
})

describe('rows page as cards do (#376)', () => {
  it('a later page of rows appends with no repeat, and gone leaves the count', () => {
    const list = firstLoad({ count: 3, order: ['a', 'b', 'c'], cards: [row('a', null, null)] })
    const ids = nextIds(list)
    const next = withPage(list, ids, { cards: [row('b', null, null), row('a', null, null)], gone: ['c'] })
    expect(next.cards.map((r) => r.id)).toEqual(['a', 'b'])
    expect(next.count).toBe(2)
  })
})

describe('the flags page restore button (#412)', () => {
  it('is named by its post, its name starting with the visible words', () => {
    const one = { ...row('a', 'dana', 't1'), text: 'דירת 3 חדרים   בפלורנטין, קומה שנייה עם מרפסת שמש גדולה ומטבח חדש' }
    expect(restoreLabel([one])).toEqual({
      text: 'שחזור',
      label: 'שחזור: דירת 3 חדרים בפלורנטין, קומה שנייה עם…', // a whole word last
    })
    const two = restoreLabel([one, row('b', 'dana', 't1')])
    expect(two.text).toBe('שחזור 2 הפרסומים')
    expect(two.label.startsWith(`${two.text}: דירת 3 חדרים`)).toBe(true)
    expect(restoreLabel([{ ...one, text: null }]).label).toBe('שחזור: מודעה בלי טקסט')
  })
})
