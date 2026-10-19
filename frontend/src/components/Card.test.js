import { jsx as _jsx } from "react/jsx-runtime";
// The card's button row (#351, amending #341 for the row): packed to the left with no reserved place;
// from the left report, WhatsApp, Facebook, so in the right-to-left row's order Facebook, WhatsApp,
// report; an absent button leaves nothing behind. Rendered to static markup in Node (no DOM).
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Card } from './Card';
const none = { state: 'not_written', value: null };
function card(whatsapp, viewed) {
    return {
        id: 'a'.repeat(64),
        post_ids: ['a'.repeat(64)],
        post_nature: 'listing_offer',
        apartment_kind: { state: 'written', value: 'whole_apartment' },
        price: { state: 'written', value: [5000] },
        entry_date: none,
        entry_date_written: null,
        rooms: { state: 'written', value: 3 },
        floor: none,
        building_floors: none,
        size_sqm: none,
        room_size_sqm: none,
        broker: none,
        balcony: none,
        parking: none,
        elevator: none,
        air_conditioning: none,
        furnished: none,
        arnona: none,
        house_committee: none,
        gender: 'no_restriction',
        areas: [],
        streets: [],
        stated_area_names: [],
        evaluation: {
            option: 'whole_apartment',
            tier: 'critical_met',
            kind_marked: false,
            fields: {},
            missing_important: [],
            area_orange: false,
            women_only_icon: false,
            corrected: [],
        },
        glow: null,
        tier_label: null,
        colours: {},
        text: 'דירה',
        permalink: 'https://www.facebook.com/groups/1/posts/2',
        photos: [],
        videos: [],
        whatsapp,
        last_published_at: '2026-10-14T08:00:00+00:00',
        publications: 1,
        ...(viewed === undefined ? {} : { viewed }),
    };
}
const signedIn = { onFlag: () => { }, onReport: () => { }, onHide: () => { }, onUnhide: () => { } };
function acts(markup) {
    const found = /<div class="acts">(.*?)<\/div><span class="reposts"/.exec(markup);
    expect(found).not.toBeNull();
    return found[1];
}
function buttons(markup) {
    return [...acts(markup).matchAll(/class="btn-o (btn-\w+)"/g)].map((match) => match[1]);
}
describe('the button row (#351)', () => {
    const now = new Date('2026-10-14T09:00:00Z');
    it('holds Facebook then WhatsApp in order: from the left, WhatsApp then Facebook', () => {
        const markup = renderToStaticMarkup(_jsx(Card, { card: card('https://wa.me/972541234567'), now: now, onOpen: () => { } }));
        expect(buttons(markup)).toEqual(['btn-fb', 'btn-wa']);
    });
    it("leaves no place for an absent WhatsApp or a guest's report", () => {
        const markup = renderToStaticMarkup(_jsx(Card, { card: card(null), now: now, onOpen: () => { } }));
        expect(buttons(markup)).toEqual(['btn-fb']);
        expect(acts(markup)).not.toMatch(/slot|rep/); // no empty place is kept
    });
});
describe('build step 6: the report button and the viewed state', () => {
    const now = new Date('2026-10-14T09:00:00Z');
    it("puts a signed-in user's report button furthest left (#328, #351)", () => {
        const markup = renderToStaticMarkup(_jsx(Card, { card: card('https://wa.me/972541234567', false), now: now, onOpen: () => { }, actions: signedIn }));
        expect(buttons(markup)).toEqual(['btn-fb', 'btn-wa', 'btn-rep']);
        expect(acts(markup)).toContain('>דיווח<');
        expect(acts(markup)).toContain('aria-haspopup="menu"');
    });
    it('packs the report button beside Facebook when there is no WhatsApp', () => {
        const markup = renderToStaticMarkup(_jsx(Card, { card: card(null, false), now: now, onOpen: () => { }, actions: signedIn }));
        expect(buttons(markup)).toEqual(['btn-fb', 'btn-rep']);
    });
    it('dims a viewed card and says "נצפה" in words; an unviewed one says nothing', () => {
        const viewed = renderToStaticMarkup(_jsx(Card, { card: card(null, true), now: now, onOpen: () => { }, actions: signedIn }));
        expect(viewed).toMatch(/class="card glow-none is-viewed"/);
        expect(viewed).toContain('<span class="seen">נצפה</span>');
        expect(viewed).toMatch(/aria-label="פתיחת המודעה, נצפתה"/);
        const fresh = renderToStaticMarkup(_jsx(Card, { card: card(null, false), now: now, onOpen: () => { }, actions: signedIn }));
        expect(fresh).not.toContain('נצפה');
        expect(fresh).not.toContain('is-viewed');
    });
});
describe('hiding (#464–#466, #468): the pill on the photo, the tag, the faded card', () => {
    const now = new Date('2026-10-14T09:00:00Z');
    const pill = (markup) => /<button type="button" class="hidepill">([^<]*)<\/button>/.exec(markup)?.[1] ?? null;
    const render = (data, actions) => renderToStaticMarkup(_jsx(Card, { card: data, now: now, onOpen: () => { }, actions: actions }));
    const tiered = (tier, viewed, hidden = false) => {
        const base = card(null, viewed);
        return { ...base, hidden, evaluation: { ...base.evaluation, tier } };
    };
    it('offers "הסתר" by tier: middle and bottom always, top once viewed; never to a guest', () => {
        expect(pill(render(tiered('critical_met', false), signedIn))).toBe('הסתר');
        expect(pill(render(tiered('unknown', false), signedIn))).toBe('הסתר');
        expect(pill(render(tiered('preferences_met', false), signedIn))).toBeNull();
        expect(pill(render(tiered('preferences_met', true), signedIn))).toBe('הסתר');
        expect(pill(render(tiered('critical_met', false)))).toBeNull();
    });
    it('a hidden card that is shown is faded, tagged "מוסתרת", and offers "בטל הסתרה"', () => {
        const markup = render(tiered('preferences_met', false, true), signedIn);
        expect(pill(markup)).toBe('בטל הסתרה');
        expect(markup).toMatch(/class="card glow-none is-hidden"/);
        expect(markup).toContain('<span class="seen hidden-tag">מוסתרת</span>');
        expect(markup).toMatch(/aria-label="פתיחת המודעה, מוסתרת"/);
    });
    it('leaves the foot as it was (#341, #351)', () => {
        expect(buttons(render(tiered('critical_met', false), signedIn))).toEqual(['btn-fb', 'btn-rep']);
    });
});
