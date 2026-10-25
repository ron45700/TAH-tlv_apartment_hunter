// The API's payloads as the page reads them (tlv_hunter/web/cards.py). The server decides every
// rule: the colours, the glow, the tier's words. The page only formats values and lays them out.

import type { Bar } from './bar'

export type MarkedState = 'written' | 'not_written' | 'unclear'

export interface Marked<T> {
  state: MarkedState
  value: T | null
}

export type Colour = 'green' | 'red' | 'grey' | 'orange' | 'plain' | 'missing'
export type Glow = 'green' | 'orange' | 'red'
export type Kind = 'room' | 'whole_apartment'

export interface Area {
  number: number
  name: string
}

/** The fields every card and opened post carry (cards.py `_listing`). */
export interface ListingFields {
  post_nature: string
  apartment_kind: Marked<Kind>
  price: Marked<number[]>
  entry_date: Marked<string>
  entry_date_written: string | null
  rooms: Marked<number>
  floor: Marked<number>
  building_floors: Marked<number>
  size_sqm: Marked<number>
  room_size_sqm: Marked<number>
  broker: Marked<boolean>
  balcony: Marked<boolean>
  parking: Marked<boolean>
  elevator: Marked<boolean>
  air_conditioning: Marked<boolean>
  furnished: Marked<'yes' | 'partial' | 'no'>
  arnona: Marked<number | 'included'>
  house_committee: Marked<number | 'included'>
  gender: 'no_restriction' | 'women_preferred' | 'women_only'
  areas: Area[]
  streets: string[]
  stated_area_names: string[]
}

export type Colours = Record<string, Colour>

export interface Evaluation {
  option: Kind | null
  tier: 'preferences_met' | 'critical_met' | 'unknown' | null
  kind_marked: boolean
  fields: Record<string, string>
  missing_important: string[]
  area_orange: boolean
  women_only_icon: boolean
  corrected: string[]
}

export interface CardData extends ListingFields {
  id: string
  post_ids: string[]
  evaluation: Evaluation
  glow: Glow | null
  tier_label: string | null
  colours: Colours
  /** The post's source (#500, #533). */
  source: Source
  text: string | null
  permalink: string
  photos: string[]
  videos: string[]
  whatsapp: string | null
  last_published_at: string
  publications: number
  /** A signed-in user's only (#62, #253); absent for a guest. */
  viewed?: boolean
  /** A signed-in user's only (#464, #468): any post of the card hidden by the user. */
  hidden?: boolean
}

/** A list's first answer (#376): the count, the whole order of this load (each card's id) and its
 * first cards whole; `first: 0` gives the count alone (#378). */
export interface CardsResponse {
  generation: number
  count: number
  /** A signed-in user's only (#465, #468): the bar holds the saved preferences, decided by the
   * server; there, with "הצגת מוסתרים" off, the hidden cards are not in the list or the count. */
  hiding?: boolean
  /** How many of the cards the bar shows are hidden. */
  hidden_count?: number
  order: string[]
  cards: CardData[]
}

/** A later page of a load, by id (#376); an id no longer in a shown card is in `gone`. */
export interface CardsPage {
  generation: number
  cards: CardData[]
  gone: string[]
}

/** Facebook's (either provider) or Yad2's (#500). A Yad2 post has no phone (#497). */
export type Source = 'facebook' | 'yad2'

export interface Phone {
  phone: string
  name: string | null
  whatsapp: string | null
}

export interface Publication {
  id: string
  posted_at: string
}

export interface PostData extends ListingFields {
  id: string
  post_ids: string[]
  corrected: string[]
  own_colours: Colours
  source: Source
  text: string | null
  permalink: string
  photos: string[]
  videos: string[]
  phones: Phone[]
  last_published_at: string
  publications: Publication[]
}

export interface AreaGroup {
  heading: string
  collapsed: boolean
  areas: number[]
}

/** GET /api/reference: the 71 areas and their region groups (§6). */
export interface Reference {
  areas: Area[]
  area_groups: AreaGroup[]
  /** The report form's fields (#277), each with its Hebrew label, in the form's order. */
  reportable_fields: ReportableField[]
}

export interface ReportableField {
  field: string
  label: string
}

/** POST /api/flag's answer: `flagged` of `of` members; a retry sends `remaining[0]` (#330 point 21). */
export interface FlagAnswer {
  flagged: number
  of: number
  remaining: string[]
}

/** GET /api/session's user (3.7 (g)). */
export interface SessionUser {
  username: string
  is_admin: boolean
  must_change_password: boolean
}

/** GET /api/telegram (#453): whether the account is linked, and since when (ISO, UTC). */
export interface TelegramState {
  linked: boolean
  linked_at: string | null
}

/** POST /api/telegram/link: a one-time code, shown once (#453). */
export interface TelegramCode {
  link: string
  code: string
  expires_at: string
}

/** GET and PUT /api/profile: the saved profile's values (#317). */
export interface SavedProfile extends Bar {
  updated_at: string
}
