// A, the list in pages (#376–#377): the page holds the whole order of its load, the items drawn so
// far, and where the next page starts. The order is fixed for the load: a page asked later never
// skips or repeats an item, whatever changed meanwhile; it changes only on the next load. A card the
// user flags or reports leaves in place, the count one less, with no reload (#377). Pure: no fetch.
// The admin's lists page their rows the same way (3.8 (b), #397): an item is anything with an id.
import type { CardData } from './types'

/** The items of a list's first answer, and of each later page: whole rows at 2, 3, 4 and 6
 * columns (#376). */
export const PAGE = 48

interface Item {
  id: string
  /** A card's posts: any of them finds the card. */
  post_ids?: string[]
}

export interface Loaded<T extends Item = CardData> {
  count: number
  /** Every item id of this load, in its order. */
  order: string[]
  cards: T[]
  /** Where in `order` the next page starts. */
  next: number
}

/** A list's first answer (whatever else it carries is not read). */
export function firstLoad<A extends { count: number; order: string[]; cards: Item[] }>(answer: A): Loaded<A['cards'][number]> {
  return { count: answer.count, order: answer.order, cards: answer.cards, next: answer.cards.length }
}

/** The ids of the next page, or none when the load is all drawn. */
export function nextIds<T extends Item>(list: Loaded<T>): string[] {
  return list.order.slice(list.next, list.next + PAGE)
}

/** A page appended: an item already drawn (regrouped meanwhile) is not drawn twice; an id that is
 * `gone` leaves the count. */
export function withPage<T extends Item, P extends { cards: T[]; gone: string[] }>(list: Loaded<T>, asked: string[], page: P): Loaded<T> {
  const drawn = new Set(list.cards.map((card) => card.id))
  const added = page.cards.filter((card) => !drawn.has(card.id))
  return {
    count: Math.max(0, list.count - page.gone.length),
    order: list.order,
    cards: [...list.cards, ...added],
    next: list.next + asked.length,
  }
}

/** The item holding this post leaves the list in place (#377); an item not drawn yet leaves the
 * order. Nothing changes for an id the load does not hold. */
export function withoutCard<T extends Item>(list: Loaded<T>, postId: string): Loaded<T> {
  const card = list.cards.find((each) => each.id === postId || (each.post_ids ?? []).includes(postId))
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
