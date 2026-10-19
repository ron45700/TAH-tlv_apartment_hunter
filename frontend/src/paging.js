/** The items of a list's first answer, and of each later page: whole rows at 2, 3, 4 and 6
 * columns (#376). */
export const PAGE = 48;
/** A list's first answer (whatever else it carries is not read). */
export function firstLoad(answer) {
    return { count: answer.count, order: answer.order, cards: answer.cards, next: answer.cards.length };
}
/** The ids of the next page, or none when the load is all drawn. */
export function nextIds(list) {
    return list.order.slice(list.next, list.next + PAGE);
}
/** A page appended: an item already drawn (regrouped meanwhile) is not drawn twice; an id that is
 * `gone` leaves the count. */
export function withPage(list, asked, page) {
    const drawn = new Set(list.cards.map((card) => card.id));
    const added = page.cards.filter((card) => !drawn.has(card.id));
    return {
        count: Math.max(0, list.count - page.gone.length),
        order: list.order,
        cards: [...list.cards, ...added],
        next: list.next + asked.length,
    };
}
const TIER_RANK = { preferences_met: 0, critical_met: 1, unknown: 2 };
/** Whether card `a` comes before card `b` in a user's list, as the server orders it
 * (`policy/order.py`): unviewed before viewed (#62), then the tier, then the newer last
 * publication, then the id. */
function sortsBefore(a, b) {
    const key = (card) => [Number(card.viewed === true), TIER_RANK[card.evaluation.tier ?? 'unknown'], -Date.parse(card.last_published_at)];
    const [x, y] = [key(a), key(b)];
    for (let i = 0; i < x.length; i++)
        if (x[i] !== y[i])
            return x[i] < y[i];
    return a.id < b.id;
}
/** A card whose viewed mark changed while its post was open takes its place in the list when the
 * post closes (Ron, 2026-10-18; #62): a viewed card goes below the unviewed ones, a card marked
 * as not viewed comes back up. Its place is found among the cards drawn; a viewed card that sorts
 * after all of them while the load holds more goes to the end of the order, below every unviewed
 * card (its exact place among the viewed ones is the next load's). Nothing changes for a post the
 * load does not hold, or a card already in its place. */
export function withViewedSettled(list, postId) {
    const card = list.cards.find((each) => each.id === postId || each.post_ids.includes(postId));
    if (!card)
        return list;
    const rest = list.cards.filter((each) => each !== card);
    const at = rest.findIndex((each) => sortsBefore(card, each));
    const order = list.order.filter((id) => id !== card.id);
    if (at >= 0 || list.next >= list.order.length) {
        const cards = at >= 0 ? [...rest.slice(0, at), card, ...rest.slice(at)] : [...rest, card];
        if (cards.every((each, i) => each === list.cards[i]))
            return list;
        const before = at >= 0 ? order.indexOf(rest[at].id) : order.length;
        return { ...list, order: [...order.slice(0, before), card.id, ...order.slice(before)], cards };
    }
    if (card.viewed !== true)
        return list;
    return { ...list, order: [...order, card.id], cards: rest, next: list.next - 1 };
}
/** What the card's pill offers a signed-in user (#466): "בטל הסתרה" on a hidden card; "הסתר" on a
 * card in the middle or bottom tier always, and in the top tier only once viewed; by tier, not by
 * glow, since a card with no preference has no glow. `viewed` may be newer than the card's own. */
export function hideOffer(card, viewed = card.viewed === true) {
    if (card.hidden)
        return 'unhide';
    return card.evaluation.tier === 'preferences_met' && !viewed ? null : 'hide';
}
/** The card holding this post with its hidden mark changed, in place (#468, points 13 and 15). */
export function withHidden(list, postId, hidden) {
    return {
        ...list,
        cards: list.cards.map((card) => (card.id === postId || card.post_ids.includes(postId) ? { ...card, hidden } : card)),
    };
}
/** A card taken out in place comes back where it was, the count one more: "בטל הסתרה" right after
 * hiding it on the saved preferences (#468). Nothing changes when it is already drawn. */
export function withCardBack(list, card, at) {
    if (list.cards.some((each) => each.id === card.id))
        return list;
    const i = Math.max(0, Math.min(at, list.cards.length));
    return {
        count: list.count + 1,
        order: [...list.order.slice(0, i), card.id, ...list.order.slice(i).filter((id) => id !== card.id)],
        cards: [...list.cards.slice(0, i), card, ...list.cards.slice(i)],
        next: list.next + 1,
    };
}
/** The item holding this post leaves the list in place (#377); an item not drawn yet leaves the
 * order. Nothing changes for an id the load does not hold. */
export function withoutCard(list, postId) {
    const card = list.cards.find((each) => each.id === postId || (each.post_ids ?? []).includes(postId));
    const id = card ? card.id : postId;
    const at = list.order.indexOf(id);
    if (!card && at < 0)
        return list;
    return {
        count: Math.max(0, list.count - 1),
        order: at < 0 ? list.order : [...list.order.slice(0, at), ...list.order.slice(at + 1)],
        cards: card ? list.cards.filter((each) => each !== card) : list.cards,
        next: at >= 0 && at < list.next ? list.next - 1 : list.next,
    };
}
