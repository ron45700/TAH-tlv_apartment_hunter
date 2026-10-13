// The closed card (PHASE_3.md 3.7 (c)): built of fixed slots, so every card is the same height and
// nothing moves whatever it holds (#341): the photo, the kind line, the price, three lines of text,
// two lines of location, the four stats, one row of chips, and a foot of two rows. The glow and the
// colours are the API's (#308, #309, #322); only the green chips are shown closed (#326), with the
// red "women only" icon, the important-missing badge and the orange location line.
import type { MouseEvent } from 'react'
import {
  closedChips,
  formatEntry,
  formatFloor,
  formatPrice,
  kindLine,
  locationLine,
  publishedTimes,
  relativeTime,
  roomsClosed,
  sizeClosed,
  type StatText,
} from '../format'
import { postPath } from '../route'
import type { CardData, Colour, Kind } from '../types'
import { Carousel } from './Carousel'
import { InfoButton } from './InfoButton'

interface Props {
  card: CardData
  now: Date
  onOpen: (id: string) => void
}

/** How a colour reads to a screen reader: the state in words (#323). */
export const COLOUR_WORDS: Record<Colour, string> = {
  green: 'חיובי',
  red: 'לא מתאים להעדפה שלך',
  grey: 'לא צוין במודעה',
  orange: 'לא ברור',
  plain: '',
  missing: 'חסר',
}

export function Card({ card, now, onOpen }: Props) {
  const kind = card.apartment_kind.value
  const corrected = new Set(card.evaluation.corrected)
  const line = kindLine(kind, card.evaluation.kind_marked, card.evaluation.option, card.post_nature === 'sublet_offer')
  const price = formatPrice(card.price)
  const entry = formatEntry(card)
  const chips = closedChips(card, card.colours)
  const reposts = publishedTimes(card.publications)
  const sizeField = kind === 'room' && card.room_size_sqm.state === 'written' ? 'room_size_sqm' : 'size_sqm'
  const open = (event: MouseEvent) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
    event.preventDefault()
    onOpen(card.id)
  }

  return (
    <article className={`card ${card.glow ? `glow-${card.glow}` : 'glow-none'}`}>
      <a
        className="open"
        href={postPath(card.id)}
        onClick={open}
        aria-label={`פתיחת המודעה${card.tier_label ? `. ${card.tier_label}` : ''}`}
      />
      <div className="media">
        <Carousel photos={card.photos} videos={card.videos} variant="card" />
        {card.tier_label && <InfoButton label={card.tier_label} />}
      </div>
      <div className="body">
        <div className="kindrow">
          <span className={line.unclear ? 'kind kind-unclear' : 'kind'}>{line.text}</span>
        </div>
        <div className="pricerow">
          {price === null ? (
            <span className="missing">אין מחיר</span>
          ) : (
            <span className={`price c-${card.colours.price}`}>{price}</span>
          )}
          {corrected.has('price') && <Fixed />}
        </div>
        <p className="txt clamp" dir="auto">
          {card.text}
        </p>
        <p className={`loc c-${card.colours.areas}`}>
          {locationLine(card)}
          {corrected.has('areas') && <Fixed />}
        </p>
        <dl className="stats">
          <Stat label="חדרים" value={roomsClosed(kind, card.rooms)} colour={card.colours.rooms} fixed={corrected.has('rooms')} />
          <Stat
            label="מ״ר"
            value={sizeClosed(kind, card.size_sqm, card.room_size_sqm)}
            colour={card.colours[sizeField]}
            fixed={corrected.has('size_sqm') || corrected.has('room_size_sqm')}
          />
          <Stat
            label="קומה"
            value={formatFloor(card.floor, card.building_floors)}
            colour={card.colours.floor}
            fixed={corrected.has('floor')}
          />
          <div className="stat">
            <dt>כניסה</dt>
            <dd>
              {entry === null ? (
                <span className="missing sm">אין תאריך כניסה</span>
              ) : (
                <span className={`one c-${card.colours.entry_date}`}>{entry}</span>
              )}
              {corrected.has('entry_date') && <Fixed />}
            </dd>
          </div>
        </dl>
        <p className="phoneline">
          <span className={`c-${card.colours.rooms}`}>{roomsLine(kind, card)}</span>
          <span className="sep" aria-hidden="true" />
          {entry === null ? (
            <span className="missing sm">אין תאריך כניסה</span>
          ) : (
            <span className={`one c-${card.colours.entry_date}`}>
              {entry.startsWith('כניסה') ? entry : `כניסה: ${entry}`}
            </span>
          )}
        </p>
        <div className="feats">
          {card.evaluation.women_only_icon && <span className="chip chip-women">נשים בלבד</span>}
          {chips.map((chip) => (
            <span key={chip.field} className="chip c-green" aria-label={`${chip.text}, ${COLOUR_WORDS.green}`}>
              {chip.text}
              {corrected.has(chip.field) && <Fixed />}
            </span>
          ))}
        </div>
        <div className="foot">
          <span className="when">{relativeTime(card.last_published_at, now)}</span>
          {/* The buttons pack to the left with no reserved place (#351, amending #341 for this row):
              from the left, report, WhatsApp, Facebook; an absent one (a guest's report, a post
              with no mobile number's WhatsApp) leaves no gap. In the right-to-left row the first
              in order sits furthest right. The report button is build step 6's. */}
          <div className="acts">
            <a className="btn-o btn-fb" href={card.permalink} target="_blank" rel="noopener noreferrer">
              פייסבוק
            </a>
            {card.whatsapp && (
              <a className="btn-o btn-wa" href={card.whatsapp} target="_blank" rel="noopener noreferrer">
                וואטסאפ
              </a>
            )}
          </div>
          <span className="reposts">{reposts}</span>
        </div>
      </div>
    </article>
  )
}

function Stat({ label, value, colour, fixed }: { label: string; value: StatText; colour: Colour; fixed: boolean }) {
  return (
    <div className="stat">
      <dt>{label}</dt>
      <dd>
        <span className={value.missing ? 'ns' : `c-${colour}`}>{value.text}</span>
        {fixed && <Fixed />}
        {value.note && <span className="note">{value.note}</span>}
      </dd>
    </div>
  )
}

/** The phone's line beside the photo (3.7 (c), rows 7 and 18): the rooms, then the entry date. */
function roomsLine(kind: Kind | null, card: CardData): string {
  const rooms = roomsClosed(kind, card.rooms)
  if (kind === 'room') return rooms.note ? `חדר · ${rooms.note}` : `${rooms.text} חדרים`
  return rooms.missing ? 'חדרים: לא צוין' : `${rooms.text} חדרים`
}

/** "Corrected by hand" beside a corrected item (#256): "תוקן" on the card, "תוקן ידנית" inside. */
export function Fixed({ long = false }: { long?: boolean }) {
  return <span className="fixed">{long ? 'תוקן ידנית' : 'תוקן'}</span>
}
