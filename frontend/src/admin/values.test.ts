import { describe, expect, it } from 'vitest'
import { KINDS, draftOf, valueOf } from './values'

const PHONES = ['0541234567', '0529876543']

// One stored value per reportable field, in Gate B's JSON: the form opens on it and gives it back.
const STORED: [string, unknown][] = [
  ['post_nature', 'sublet_offer'],
  ['apartment_kind', { state: 'written', value: 'room' }],
  ['price', { state: 'written', value: [4500, 4800] }],
  ['entry_date', { state: 'written', value: '2026-11-01' }],
  ['entry_date', { state: 'written', value: 'immediate' }],
  ['rooms', { state: 'written', value: 3.5 }],
  ['floor', { state: 'written', value: -1 }],
  ['building_floors', { state: 'unclear', value: null }],
  ['size_sqm', { state: 'written', value: 72 }],
  ['room_size_sqm', { state: 'not_written', value: null }],
  ['broker', { state: 'written', value: false }],
  ['balcony', { state: 'written', value: true }],
  ['parking', { state: 'not_written', value: null }],
  ['elevator', { state: 'written', value: true }],
  ['air_conditioning', { state: 'written', value: false }],
  ['furnished', { state: 'written', value: 'partial' }],
  ['arnona', { state: 'written', value: 450 }],
  ['house_committee', { state: 'written', value: 'included' }],
  ['gender', 'women_only'],
  ['areas', [30, 31]],
  ['streets', ['דיזנגוף', 'בן יהודה']],
  ['other_city', 'חולון'],
  ['other_city', null],
  ['phone_names', [{ phone: '0541234567', name: 'דנה' }]],
]

describe('the correction value form (step 5)', () => {
  it('covers the 22 reportable fields', () => {
    expect(Object.keys(KINDS)).toHaveLength(22)
  })

  it.each(STORED)('opens %s on its stored value and gives it back', (field, value) => {
    expect(valueOf(field, draftOf(field, value, PHONES))).toEqual(value)
  })

  it('reads the amounts with their thousands separators and the shekel sign', () => {
    const draft = { ...draftOf('price', null, []), state: 'written' as const, text: '4,500 ₪5,000' }
    expect(valueOf('price', draft)).toEqual({ state: 'written', value: [4500, 5000] })
  })

  it('gives null for a written value that is not complete', () => {
    const draft = { ...draftOf('rooms', null, []), state: 'written' as const, text: '' }
    expect(valueOf('rooms', draft)).toBeNull()
    expect(valueOf('entry_date', { ...draft, choice: 'date', text: '1.11' })).toBeNull()
  })

  it('sorts the areas and drops repeats, keeps the streets one per line', () => {
    const areas = { ...draftOf('areas', [], []), areas: [31, 30, 31] }
    expect(valueOf('areas', areas)).toEqual([30, 31])
    const streets = { ...draftOf('streets', [], []), text: ' דיזנגוף \n\nבן יהודה' }
    expect(valueOf('streets', streets)).toEqual(['דיזנגוף', 'בן יהודה'])
  })
})
