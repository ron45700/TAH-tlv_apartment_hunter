// The card's button row (#351, amending #341 for the row): packed to the left with no reserved place;
// from the left report, WhatsApp, Facebook, so in the right-to-left row's order Facebook, WhatsApp,
// report; an absent button leaves nothing behind. Rendered to static markup in Node (no DOM).
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { CardData, Marked } from '../types'
import { Card } from './Card'

const none: Marked<never> = { state: 'not_written', value: null }

function card(whatsapp: string | null): CardData {
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
  }
}

function acts(markup: string): string {
  const found = /<div class="acts">(.*?)<\/div>/.exec(markup)
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
