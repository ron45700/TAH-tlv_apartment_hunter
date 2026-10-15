// A, the list in pages (#376–#377): the page holds the whole order of its load, the cards drawn so
// far, and where the next page starts. The order is fixed for the load: a page asked later never
// skips or repeats a card, whatever changed meanwhile; it changes only on the next load. A card the
// user flags or reports leaves in place, the count one less, with no reload (#377). Pure: no fetch.
import type { CardData, CardsPage, CardsResponse } from './types'

/** The cards of a list's first answer, and of each later page: whole rows at 2, 3, 4 and 6
 * columns (#376). */
export const PAGE = 48

export interface Loaded {
  count: number
  /** Every card id of this load, in its order. */
  order: string[]
  cards: CardData[]
  /** Where in `order` the next page starts. */
  next: number
}

export function firstLoad(answer: CardsResponse): Loaded {
  return { count: answer.count, order: answer.order, cards: answer.cards, next: answer.cards.length }
}

/** The ids of the next page, or none when the load is all drawn. */
export function nextIds(list: Loaded): string[] {
  return list.order.slice(list.next, list.next + PAGE)
}

/** A page appended: a card already drawn (regrouped meanwhile) is not drawn twice; an id that is
 * `gone` leaves the count. */
export function withPage(list: Loaded, asked: string[], page: CardsPage): Loaded {
  const drawn = new Set(list.cards.map((card) => card.id))
  const added = page.cards.filter((card) => !drawn.has(card.id))
  return {
    count: Math.max(0, list.count - page.gone.length),
    order: list.order,
    cards: [...list.cards, ...added],
    next: list.next + asked.length,
  }
}

/** The card holding this post leaves the list in place (#377); a card not drawn yet leaves the
 * order. Nothing changes for an id the load does not hold. */
export function withoutCard(list: Loaded, postId: string): Loaded {
  const card = list.cards.find((each) => each.id === postId || each.post_ids.includes(postId))
  const id = card ? card.id : postId
  const at = list.order.indexOf(id)
  if (!card && at < 0) return list
  return {
    count: Math.max(0, list.count - 1),
    order: at < 0 ? list.order : [...list.order.slice(0, at), ...list.order.slice(at + 1)],
    cards: card ? list.cards.filter((each) => each !== card) : list.cards,
    next: at >= 0 && at < list.next ? list.next - 1 : list.next,
  }
}
