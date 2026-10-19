// A, the list in pages (#376, #377): the page's merge of later pages and its removal in place.
import { describe, expect, it } from 'vitest'
import { PAGE, firstLoad, hideOffer, nextIds, withHidden, withPage, withViewedSettled, withoutCard, type Loaded } from './paging'
import type { CardData } from './types'

const card = (id: string, ...others: string[]) => ({ id, post_ids: [id, ...others] }) as unknown as CardData
const ids = (n: number, from = 0) => Array.from({ length: n }, (_, i) => `c${from + i}`)

function load(total: number): Loaded {
  const order = ids(total)
  return firstLoad({ generation: 1, count: total, order, cards: order.slice(0, PAGE).map((id) => card(id)) })
}

describe('the pages of a load (#376)', () => {
  it('starts after the first cards and asks the next 48 from the order', () => {
    const list = load(120)
    expect(list.next).toBe(PAGE)
    expect(nextIds(list)).toEqual(ids(PAGE, PAGE))
  })

  it('appends a page in the order, and asks nothing once all is drawn', () => {
    let list = load(60)
    const asked = nextIds(list)
    list = withPage(list, asked, { generation: 1, cards: asked.map((id) => card(id)), gone: [] })
    expect(list.cards.map((c) => c.id)).toEqual(ids(60))
    expect(nextIds(list)).toEqual([])
  })

  it('never draws a card twice, and takes a gone card out of the count', () => {
    let list = load(60)
    const asked = nextIds(list)
    // c48 was regrouped into c0's card meanwhile; c49 is gone
    const page = { generation: 2, cards: [card('c0'), ...asked.slice(2).map((id) => card(id))], gone: ['c49'] }
    list = withPage(list, asked, page)
    expect(list.cards.filter((c) => c.id === 'c0')).toHaveLength(1)
    expect(list.cards).toHaveLength(58)
    expect(list.count).toBe(59)
    expect(list.next).toBe(60)
  })
})

describe('a card leaves in place (#377)', () => {
  it('by any of its posts: the count one less, the next page still where it was', () => {
    const list = load(100)
    const withDup = { ...list, cards: [card('c0', 'd0'), ...list.cards.slice(1)] }
    const after = withoutCard(withDup, 'd0')
    expect(after.cards.map((c) => c.id)).not.toContain('c0')
    expect(after.count).toBe(99)
    expect(after.order).not.toContain('c0')
    expect(nextIds(after)).toEqual(nextIds(list))
  })

  it('a card not drawn yet leaves the order, and an unknown id changes nothing', () => {
    const list = load(100)
    const after = withoutCard(list, 'c70')
    expect(after.order).not.toContain('c70')
    expect(after.count).toBe(99)
    expect(after.next).toBe(list.next)
    expect(withoutCard(list, 'nobody')).toBe(list)
  })
})

describe('a viewed card takes its place when its post closes (Ron, 2026-10-18; #62)', () => {
  type Tier = 'preferences_met' | 'critical_met' | 'unknown'
  const at = (hour: number) => `2026-10-18T${String(hour).padStart(2, '0')}:00:00+00:00`
  const sorted = (id: string, tier: Tier, hour: number, viewed = false) =>
    ({ id, post_ids: [id], viewed, evaluation: { tier }, last_published_at: at(hour) }) as unknown as CardData
  const listOf = (cards: CardData[], more: string[] = []): Loaded => ({
    count: cards.length + more.length,
    order: [...cards.map((c) => c.id), ...more],
    cards,
    next: cards.length,
  })
  const viewedNow = (list: Loaded, id: string, viewed = true): Loaded => ({
    ...list,
    cards: list.cards.map((c) => (c.id === id ? { ...c, viewed } : c)),
  })

  const drawn = [
    sorted('a', 'preferences_met', 9),
    sorted('b', 'preferences_met', 8),
    sorted('c', 'critical_met', 9),
    sorted('d', 'preferences_met', 9, true),
    sorted('e', 'critical_met', 7, true),
  ]

  it('goes below the unviewed cards, into its tier among the viewed ones', () => {
    const after = withViewedSettled(viewedNow(listOf(drawn), 'b'), 'b')
    expect(after.cards.map((c) => c.id)).toEqual(['a', 'c', 'd', 'b', 'e'])
    expect(after.order).toEqual(['a', 'c', 'd', 'b', 'e'])
    expect(after.next).toBe(5)
    expect(after.count).toBe(5)
  })

  it('a card marked as not viewed comes back up', () => {
    const after = withViewedSettled(viewedNow(listOf(drawn), 'e', false), 'e')
    expect(after.cards.map((c) => c.id)).toEqual(['a', 'b', 'c', 'e', 'd'])
  })

  it('a viewed card that sorts after every drawn card, with more to come, goes to the end of the order', () => {
    const list = viewedNow(listOf(drawn.slice(0, 3), ['x', 'y']), 'a')
    const after = withViewedSettled(list, 'a')
    expect(after.cards.map((c) => c.id)).toEqual(['b', 'c'])
    expect(after.order).toEqual(['b', 'c', 'x', 'y', 'a'])
    expect(after.next).toBe(2)
    expect(nextIds(after)).toEqual(['x', 'y', 'a'])
    expect(after.count).toBe(5)
  })

  it('changes nothing for a card in its place or a post the load does not hold', () => {
    const list = listOf(drawn)
    expect(withViewedSettled(list, 'c')).toBe(list)
    expect(withViewedSettled(list, 'nobody')).toBe(list)
    const unviewedLast = listOf(drawn.slice(0, 3), ['x'])
    expect(withViewedSettled(unviewedLast, 'c')).toBe(unviewedLast)
  })
})

describe('hiding (#464–#466, #468)', () => {
  type Tier = 'preferences_met' | 'critical_met' | 'unknown'
  const card = (tier: Tier, viewed = false, hidden = false) =>
    ({ id: 'a', post_ids: ['a', 'b'], viewed, hidden, evaluation: { tier } }) as unknown as CardData

  it('"הסתר" on the middle and bottom tiers always, on the top tier once viewed; "בטל הסתרה" when hidden', () => {
    expect(hideOffer(card('critical_met'))).toBe('hide')
    expect(hideOffer(card('unknown'))).toBe('hide')
    expect(hideOffer(card('preferences_met'))).toBeNull()
    expect(hideOffer(card('preferences_met', true))).toBe('hide')
    expect(hideOffer(card('preferences_met'), true)).toBe('hide') // viewed meanwhile, in the open post
    expect(hideOffer(card('preferences_met', false, true))).toBe('unhide')
  })

  it('marks the card holding any of its posts, in place', () => {
    const list: Loaded = { count: 1, order: ['a'], cards: [card('unknown')], next: 1 }
    const after = withHidden(list, 'b', true)
    expect(after.cards[0].hidden).toBe(true)
    expect(after.order).toEqual(['a'])
    expect(after.count).toBe(1)
  })
})
