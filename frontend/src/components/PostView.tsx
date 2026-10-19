// The opened post (PHASE_3.md 3.7 (c), (f)): a dialog over the list on a desktop and a tablet
// (#304: the X or a click outside closes it), full screen with a back arrow on a phone (#313). Every
// item of (c): the carousel, the tier's words at the top of the price block (#332 point 29), every
// chip in its colour (#326), the rows ("לא צוין" in grey, #321), the whole text unchanged, the
// phones with WhatsApp (#311), the videos, the publications, the link to the original post (#330
// point 10). The tier, the glow and the colours come from the list's card, which follows the bar;
// a post the list does not hold shows its own colours and no tier.
//
// Build step 6, signed-in only: opening the post marks its card viewed (#253, #276); "סימון כלא
// נצפה", the "lied" flag and the "wrong classification" form sit in the foot on a desktop and in the
// top bar's menu on a phone (3.7 (c) rows 31–33).
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api, ApiError } from '../api'
import {
  featureChips,
  formatEntry,
  formatFee,
  formatFloor,
  formatPrice,
  israelTime,
  kindLine,
  phoneLabel,
  relativeTime,
  roomsOpen,
  sizeOpen,
  NOT_STATED,
  type StatText,
} from '../format'
import type { CardData, Colour, Colours, PostData, ReportableField } from '../types'
import { ActionMenu, ReportForm, type MenuItem } from './actions'
import { Carousel } from './Carousel'
import { hideOffer } from '../paging'
import { COLOUR_WORDS, Fixed } from './Card'

/** A signed-in user's writes on the opened post (build step 6); absent for a guest. */
export interface PostActions {
  reportFields: ReportableField[]
  /** Open the report form at once: "סיווג שגוי" chosen on the closed card (3.7 (c) row 33). */
  startReport: boolean
  onViewed: (postIds: string[], viewed: boolean) => void
  onFlag: (id: string) => void
  /** The report was stored; `removed` false: the post stays until the admin handles it. */
  onReported: (removed: boolean) => void
  /** A write found the post no longer in a current card (409 "gone"). */
  onGone: () => void
  /** "הסתר" and "בטל הסתרה" (#464–#466, #468), offered as on the card. */
  onHide: (id: string) => void
  onUnhide: (id: string) => void
}

interface Props {
  id: string
  card: CardData | undefined
  now: Date
  phone: boolean
  onClose: () => void
  actions?: PostActions
}

export function PostView({ id, card, now, phone, onClose, actions }: Props) {
  const [post, setPost] = useState<PostData | null>(null)
  const [failed, setFailed] = useState<number | null>(null)
  const [viewed, setViewed] = useState(false)
  const [reporting, setReporting] = useState(false)
  const sheet = useRef<HTMLDivElement>(null)
  const latest = useRef(actions)
  latest.current = actions

  useEffect(() => {
    const controller = new AbortController()
    setPost(null)
    setFailed(null)
    api
      .post(id, controller.signal)
      .then(setPost)
      .catch((error) => {
        if (error instanceof ApiError) setFailed(error.status)
      })
    return () => controller.abort()
  }, [id])

  // Opening marks the card viewed for a signed-in user (#253); the first time is kept (#276).
  const signedIn = actions !== undefined
  useEffect(() => {
    if (!post || !signedIn) return
    let live = true
    api
      .markViewed(post.id)
      .then(() => {
        if (!live) return
        setViewed(true)
        latest.current?.onViewed(post.post_ids, true)
      })
      .catch(() => undefined) // the card simply stays unviewed (3.7 (i))
    if (latest.current?.startReport) setReporting(true)
    return () => {
      live = false
    }
  }, [post, signedIn])

  const unview = () => {
    if (!post) return
    api
      .unmarkViewed(post.id)
      .then(() => {
        setViewed(false)
        latest.current?.onViewed(post.post_ids, false)
      })
      .catch((error) => {
        if (error instanceof ApiError && error.refusal === 'gone') latest.current?.onGone()
      })
  }

  const items: MenuItem[] = post
    ? [
        { label: 'המודעה משקרת', onSelect: () => actions?.onFlag(post.id) },
        { label: 'דיווח על סיווג שגוי', onSelect: () => setReporting(true) },
      ]
    : []
  // "הסתר" / "בטל הסתרה" by the list's card (the opened post carries no tier): none for a post
  // opened by its own address, which has no card in the list.
  const listed = post && card?.id === post.id ? card : undefined
  const offer = actions && listed ? hideOffer(listed, viewed || listed.viewed === true) : null
  const hideItems: MenuItem[] =
    offer && post
      ? [
          offer === 'hide'
            ? { label: 'הסתר', onSelect: () => actions?.onHide(post.id) }
            : { label: 'בטל הסתרה', onSelect: () => actions?.onUnhide(post.id) },
        ]
      : []

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    sheet.current?.focus()
    document.body.classList.add('locked')
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => {
      document.body.classList.remove('locked')
      document.removeEventListener('keydown', onKey)
      previous?.focus?.()
    }
  }, [onClose])

  return (
    <div className="post" role="dialog" aria-modal="true" aria-label="המודעה">
      {!phone && <div className="backdrop" onClick={onClose} aria-hidden="true" />}
      <div className="sheet" ref={sheet} tabIndex={-1}>
        <div className="topbar">
          {phone ? (
            <>
              <button className="back" type="button" onClick={onClose}>
                חזרה
              </button>
              {actions && post && (
                <ActionMenu
                  label="פעולות"
                  className="btn-o btn-act"
                  placement="down"
                  items={[...(viewed ? [{ label: 'סימון כלא נצפה', onSelect: unview }] : []), ...hideItems, ...items]}
                />
              )}
            </>
          ) : (
            <button className="close" type="button" onClick={onClose} aria-label="סגירה" />
          )}
        </div>
        {post ? (
          <Body
            post={post}
            card={card?.id === post.id ? card : undefined}
            now={now}
            phone={phone}
            foot={
              actions && !phone ? (
                <div className="bottombar-end">
                  {viewed && (
                    <button type="button" className="btn quiet" onClick={unview}>
                      סימון כלא נצפה
                    </button>
                  )}
                  {hideItems.map((item) => (
                    <button key={item.label} type="button" className="btn quiet" onClick={item.onSelect}>
                      {item.label}
                    </button>
                  ))}
                  <ActionMenu label="דיווח" className="btn rep" items={items} />
                </div>
              ) : null
            }
          />
        ) : (
          <p className="sheet-state">
            {failed === 404
              ? 'המודעה כבר לא מוצגת: היא הוסרה או עברה לארכיון.'
              : failed !== null
                ? 'לא הצלחנו לטעון את המודעה. נסו שוב.'
                : 'טוען…'}
          </p>
        )}
      </div>
      {reporting && post && actions && (
        <ReportForm
          fields={actions.reportFields}
          onCancel={() => setReporting(false)}
          onSend={(fields, note) =>
            api
              .report(post.id, fields, note)
              .then((answer) => {
                setReporting(false)
                latest.current?.onReported(answer.removed)
              })
              .catch((error) => {
                if (error instanceof ApiError && error.refusal === 'gone') {
                  setReporting(false)
                  latest.current?.onGone()
                  return
                }
                throw error
              })
          }
        />
      )}
    </div>
  )
}

function Body({
  post,
  card,
  now,
  phone,
  foot,
}: {
  post: PostData
  card: CardData | undefined
  now: Date
  phone: boolean
  foot: ReactNode
}) {
  const colours: Colours = card?.colours ?? post.own_colours
  const corrected = new Set(post.corrected)
  const kind = post.apartment_kind.value
  const line = kindLine(
    kind,
    card?.evaluation.kind_marked ?? post.apartment_kind.state !== 'written',
    card?.evaluation.option ?? null,
    post.post_nature === 'sublet_offer',
  )
  const price = formatPrice(post.price)
  const entry = formatEntry(post)
  const mobile = post.phones.find((phoneEntry) => phoneEntry.whatsapp)
  const sizeField = kind === 'room' && post.room_size_sqm.state === 'written' ? 'room_size_sqm' : 'size_sqm'

  return (
    <>
      <Carousel photos={post.photos} videos={post.videos} variant="open" eager />
      <div className="content">
        <div className="pblock">
          {card?.tier_label && <p className={`tierline t-${card.glow ?? 'none'}`}>{card.tier_label}</p>}
          <span className={line.unclear ? 'kind kind-unclear' : 'kind'}>{line.text}</span>
          <div className="pricerow big">
            {price === null ? (
              <span className="missing">אין מחיר</span>
            ) : (
              <span className={`price c-${colours.price}`}>{price}</span>
            )}
            {corrected.has('price') && <Fixed long />}
          </div>
          {post.gender !== 'no_restriction' && (
            <div className="gender">
              {post.gender === 'women_only' ? (
                <span className="chip chip-women">נשים בלבד</span>
              ) : (
                <span className="chip c-plain">עדיפות לבנות</span>
              )}
            </div>
          )}
          <p className="meta">פורסם {relativeTime(post.last_published_at, now)}</p>
        </div>

        <div className="feats feats-open">
          {featureChips(post).map((chip) => {
            const colour = colours[chip.field] ?? 'plain'
            const words = COLOUR_WORDS[colour]
            return (
              <span key={chip.field} className={`chip c-${colour}`} aria-label={words ? `${chip.text}, ${words}` : chip.text}>
                {chip.text}
                {corrected.has(chip.field) && <Fixed long />}
              </span>
            )
          })}
        </div>

        <dl className="rows">
          <Row label="חדרים" value={roomsOpen(kind, post.rooms)} colour={colours.rooms} fixed={corrected.has('rooms')} />
          <Row
            label="גודל"
            value={sizeOpen(kind, post.size_sqm, post.room_size_sqm)}
            colour={colours[sizeField]}
            fixed={corrected.has('size_sqm') || corrected.has('room_size_sqm')}
          />
          <Row label="קומה" value={formatFloor(post.floor, post.building_floors)} colour={colours.floor} fixed={corrected.has('floor')} />
          <div className="row">
            <dt>תאריך כניסה</dt>
            <dd>
              {entry === null ? (
                <span className="missing sm">אין תאריך כניסה</span>
              ) : (
                <span className={`c-${colours.entry_date}`}>{entry}</span>
              )}
              {corrected.has('entry_date') && <Fixed long />}
            </dd>
          </div>
          <Row label="ארנונה" value={formatFee(post.arnona)} colour={colours.arnona} fixed={corrected.has('arnona')} />
          <Row
            label="ועד בית"
            value={formatFee(post.house_committee)}
            colour={colours.house_committee}
            fixed={corrected.has('house_committee')}
          />
          <Row label="אזור" value={areaText(post)} colour={colours.areas} fixed={corrected.has('areas')} />
          <Row label="רחוב" value={listOrMissing(post.streets)} colour="plain" fixed={corrected.has('streets')} />
          <Row label="כפי שנכתב במודעה" value={listOrMissing(post.stated_area_names)} colour="plain" fixed={false} />
        </dl>

        <section>
          <h3>הטקסט המלא</h3>
          <p className="txt full" dir="auto">
            {post.text}
          </p>
        </section>

        {post.phones.length > 0 && (
          <section>
            <h3>טלפונים</h3>
            <ul className="phones">
              {post.phones.map((phoneEntry) => (
                <li key={phoneEntry.phone}>
                  <a href={`tel:${phoneEntry.phone}`} dir="ltr">
                    {phoneLabel(phoneEntry.phone, phoneEntry.name)}
                  </a>
                  {phoneEntry.whatsapp && (
                    <a className="btn-o btn-wa" href={phoneEntry.whatsapp} target="_blank" rel="noopener noreferrer">
                      וואטסאפ
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {post.videos.length > 0 && (
          <section className="videos">
            {post.videos.map((video, i) => (
              <a key={video} className="lk" href={video} target="_blank" rel="noopener noreferrer">
                {post.videos.length > 1 ? `צפייה בסרטון ${i + 1} בפייסבוק` : 'צפייה בסרטון בפייסבוק'}
              </a>
            ))}
          </section>
        )}

        {post.publications.length > 1 && <Publications post={post} now={now} collapsed={phone} />}
      </div>
      <div className="bottombar">
        <a className="btn primary" href={post.permalink} target="_blank" rel="noopener noreferrer">
          למודעה המקורית
        </a>
        {mobile?.whatsapp && (
          <a className="btn wa" href={mobile.whatsapp} target="_blank" rel="noopener noreferrer">
            וואטסאפ
          </a>
        )}
        {foot}
      </div>
    </>
  )
}

/** Every publication, the earliest first (#75 A, #122): relative and in Israel time. */
function Publications({ post, now, collapsed }: { post: PostData; now: Date; collapsed: boolean }) {
  const items = (
    <ol className="pubs">
      {post.publications.map((publication) => (
        <li key={publication.id}>
          {relativeTime(publication.posted_at, now)}{' '}
          <span className="meta">({israelTime(publication.posted_at)})</span>
        </li>
      ))}
    </ol>
  )
  const title = `פורסם ${post.publications.length} פעמים`
  if (collapsed) {
    return (
      <details className="log">
        <summary>{title}</summary>
        {items}
      </details>
    )
  }
  return (
    <section className="log">
      <h3>{title}</h3>
      {items}
    </section>
  )
}

function Row({ label, value, colour, fixed }: { label: string; value: StatText; colour: Colour; fixed: boolean }) {
  return (
    <div className="row">
      <dt>{label}</dt>
      <dd>
        <span className={value.missing ? 'ns' : `c-${colour}`}>{value.text}</span>
        {fixed && <Fixed long />}
      </dd>
    </div>
  )
}

function areaText(post: PostData): StatText {
  if (post.areas.length) return { text: post.areas.map((area) => area.name).join(', ') }
  if (post.streets.length || post.stated_area_names.length) return { text: 'האזור לא ברור' }
  return { text: NOT_STATED, missing: true }
}

function listOrMissing(values: string[]): StatText {
  return values.length ? { text: values.join(', ') } : { text: NOT_STATED, missing: true }
}
