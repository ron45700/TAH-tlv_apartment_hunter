// The API's payloads as the page reads them (tlv_hunter/web/cards.py). The server decides every
// rule: the colours, the glow, the tier's words. The page only formats values and lays them out.

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
  text: string | null
  permalink: string
  photos: string[]
  videos: string[]
  whatsapp: string | null
  last_published_at: string
  publications: number
}

export interface CardsResponse {
  generation: number
  count: number
  cards: CardData[]
}

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
  text: string | null
  permalink: string
  photos: string[]
  videos: string[]
  phones: Phone[]
  last_published_at: string
  publications: Publication[]
}
