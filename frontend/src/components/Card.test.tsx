// The card's button row (#351, amending #341 for the row): packed to the left with no reserved place;
// from the left report, WhatsApp, Facebook, so in the right-to-left row's order Facebook, WhatsApp,
// report; an absent button leaves nothing behind. Rendered to static markup in Node (no DOM).
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { CardData, Marked } from '../types'
import { Card, type CardActions } from './Card'

const none: Marked<never> = { state: 'not_written', value: null }

function card(whatsapp: string | null, viewed?: boolean): CardData {
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
    source: 'facebook',
    text: 'דירה',
    permalink: 'https://www.facebook.com/groups/1/posts/2',
    photos: [],
    videos: [],
    whatsapp,
    last_published_at: '2026-10-14T08:00:00+00:00',
    publications: 1,
    ...(viewed === undefined ? {} : { viewed }),
  }
}

const signedIn: CardActions = { onFlag: () => {}, onReport: () => {}, onHide: () => {}, onUnhide: () => {} }

function acts(markup: string): string {
  const found = /<div class="acts">(.*?)<\/div><span class="reposts"/.exec(markup)
  expect(found).not.toBeNull()
  return found![1]
}

function buttons(markup: string): string[] {
  return [...acts(markup).matchAll(/class="btn-o (btn-\w+)"/g)].map((match) => match[1])
}

describe('the button row (#351)', () => {
  const now = new Date('2026-10-14T09:00:00Z')

  it('holds Facebook then WhatsApp in order: from the left, WhatsApp then Facebook', () => {
    const markup = renderToStaticMarkup(<Card card={card('https://wa.me/972541234567')} now={now} onOpen={() => {}} />)
    expect(buttons(markup)).toEqual(['btn-fb', 'btn-wa'])
  })

  it("leaves no place for an absent WhatsApp or a guest's report", () => {
    const markup = renderToStaticMarkup(<Card card={card(null)} now={now} onOpen={() => {}} />)
    expect(buttons(markup)).toEqual(['btn-fb'])
    expect(acts(markup)).not.toMatch(/slot|rep/) // no empty place is kept
  })
})

describe('build step 6: the report button and the viewed state', () => {
  const now = new Date('2026-10-14T09:00:00Z')

  it("puts a signed-in user's report button furthest left (#328, #351)", () => {
    const markup = renderToStaticMarkup(
      <Card card={card('https://wa.me/972541234567', false)} now={now} onOpen={() => {}} actions={signedIn} />,
    )
    expect(buttons(markup)).toEqual(['btn-fb', 'btn-wa', 'btn-rep'])
    expect(acts(markup)).toContain('>דיווח<')
    expect(acts(markup)).toContain('aria-haspopup="menu"')
  })

  it('packs the report button beside Facebook when there is no WhatsApp', () => {
    const markup = renderToStaticMarkup(<Card card={card(null, false)} now={now} onOpen={() => {}} actions={signedIn} />)
    expect(buttons(markup)).toEqual(['btn-fb', 'btn-rep'])
  })

  it('dims a viewed card and says "נצפה" in words; an unviewed one says nothing', () => {
    const viewed = renderToStaticMarkup(<Card card={card(null, true)} now={now} onOpen={() => {}} actions={signedIn} />)
    expect(viewed).toMatch(/class="card glow-none is-viewed"/)
    expect(viewed).toContain('<span class="seen">נצפה</span>')
    expect(viewed).toMatch(/aria-label="פתיחת המודעה, נצפתה"/)
    const fresh = renderToStaticMarkup(<Card card={card(null, false)} now={now} onOpen={() => {}} actions={signedIn} />)
    expect(fresh).not.toContain('נצפה')
    expect(fresh).not.toContain('is-viewed')
  })
})

describe('hiding (#464–#466, #468): the pill on the photo, the tag, the faded card', () => {
  const now = new Date('2026-10-14T09:00:00Z')
  const pill = (markup: string) => /<button type="button" class="hidepill">([^<]*)<\/button>/.exec(markup)?.[1] ?? null
  const render = (data: CardData, actions?: CardActions) =>
    renderToStaticMarkup(<Card card={data} now={now} onOpen={() => {}} actions={actions} />)
  const tiered = (tier: 'preferences_met' | 'critical_met' | 'unknown', viewed: boolean, hidden = false): CardData => {
    const base = card(null, viewed)
    return { ...base, hidden, evaluation: { ...base.evaluation, tier } }
  }

  it('offers "הסתר" by tier: middle and bottom always, top once viewed; never to a guest', () => {
    expect(pill(render(tiered('critical_met', false), signedIn))).toBe('הסתר')
    expect(pill(render(tiered('unknown', false), signedIn))).toBe('הסתר')
    expect(pill(render(tiered('preferences_met', false), signedIn))).toBeNull()
    expect(pill(render(tiered('preferences_met', true), signedIn))).toBe('הסתר')
    expect(pill(render(tiered('critical_met', false)))).toBeNull()
  })

  it('a hidden card that is shown is faded, tagged "מוסתרת", and offers "בטל הסתרה"', () => {
    const markup = render(tiered('preferences_met', false, true), signedIn)
    expect(pill(markup)).toBe('בטל הסתרה')
    expect(markup).toMatch(/class="card glow-none is-hidden"/)
    expect(markup).toContain('<span class="seen hidden-tag">מוסתרת</span>')
    expect(markup).toMatch(/aria-label="פתיחת המודעה, מוסתרת"/)
  })

  it('leaves the foot as it was (#341, #351)', () => {
    expect(buttons(render(tiered('critical_met', false), signedIn))).toEqual(['btn-fb', 'btn-rep'])
  })
})

// Yad2 (#533, #534): the source pill in the kind row, the "יד2" link, no WhatsApp, the place as given.
describe('a Yad2 card', () => {
  const yad2: CardData = {
    ...card(null),
    source: 'yad2',
    permalink: 'https://www.yad2.co.il/realestate/item/tel-aviv-area/p0000001',
    areas: [{ number: 50, name: 'נווה עופר' }],
    stated_area_names: ['נווה עופר, תל כביר', 'יפו'],
    streets: ['שלמה 12', 'רחוב אחר'],
  }

  it('names its source in the kind row and links to the listing as "יד2"', () => {
    const html = renderToStaticMarkup(<Card card={yad2} now={new Date('2026-10-14T09:00:00Z')} onOpen={() => {}} />)
    expect(html).toContain('<span class="src src-yad2">יד2</span>')
    expect(html).toContain('href="https://www.yad2.co.il/realestate/item/tel-aviv-area/p0000001"')
    expect(html).not.toContain('פייסבוק')
    expect(html).not.toContain('וואטסאפ')
  })

  it('shows the neighbourhood and street Yad2 gave, not the names of the areas', () => {
    const html = renderToStaticMarkup(<Card card={yad2} now={new Date('2026-10-14T09:00:00Z')} onOpen={() => {}} />)
    expect(html).toContain('נווה עופר, תל כביר · שלמה 12')
    expect(html).not.toContain('רחוב אחר')
  })

  it('a Facebook card names its source too', () => {
    const html = renderToStaticMarkup(<Card card={card(null)} now={new Date('2026-10-14T09:00:00Z')} onOpen={() => {}} />)
    expect(html).toContain('<span class="src src-facebook">פייסבוק</span>')
  })
})
