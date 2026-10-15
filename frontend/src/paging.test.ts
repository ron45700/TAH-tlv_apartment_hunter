// A, the list in pages (#376, #377): the page's merge of later pages and its removal in place.
import { describe, expect, it } from 'vitest'
import { PAGE, firstLoad, nextIds, withPage, withoutCard, type Loaded } from './paging'
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
