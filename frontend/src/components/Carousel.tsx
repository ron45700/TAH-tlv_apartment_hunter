// The photo carousel, on the closed card and in the opened post (#327, #332 point 30): a scroll-snap
// track the finger swipes, arrows on hover (drawn in CSS: controls, not state glyphs), dots and a
// "1/5" count. Photos load lazily, as they come near the view (#330 point 12). A post with no photo
// but a video shows the link to the video in the photo's place, never "no photos" (round 9).
import { useRef, useState } from 'react'
import { photoPosition } from '../format'
import type { Source } from '../types'

interface Props {
  photos: string[]
  videos: string[]
  variant: 'card' | 'open'
  /** The first photo loads at once in the opened post; on a card it waits for the card's view. */
  eager?: boolean
  /** Where the video plays (#534): Facebook's page or Yad2's listing. */
  source?: Source
}

export function Carousel({ photos, videos, variant, eager = false, source = 'facebook' }: Props) {
  const track = useRef<HTMLDivElement>(null)
  const [index, setIndex] = useState(0)
  const total = photos.length

  if (total === 0) {
    return (
      <div className={`car car-${variant} car-empty`}>
        {videos.length > 0 ? (
          <a className="vlink" href={videos[0]} target="_blank" rel="noopener noreferrer">
            {source === 'yad2' ? 'צפייה בסרטון ביד2' : 'צפייה בסרטון בפייסבוק'}
          </a>
        ) : (
          <span className="car-none">אין תמונות</span>
        )}
      </div>
    )
  }

  const onScroll = () => {
    const el = track.current
    if (!el || el.clientWidth === 0) return
    setIndex(Math.min(total - 1, Math.round(Math.abs(el.scrollLeft) / el.clientWidth)))
  }

  // The page is right to left: the next photo lies to the left.
  const step = (direction: 1 | -1) => (event: React.MouseEvent) => {
    event.preventDefault()
    event.stopPropagation()
    const el = track.current
    if (!el) return
    const rtl = getComputedStyle(el).direction === 'rtl'
    el.scrollBy({ left: direction * el.clientWidth * (rtl ? -1 : 1), behavior: 'smooth' })
  }

  return (
    <div className={`car car-${variant}`}>
      <div className="track" ref={track} onScroll={onScroll} tabIndex={0} aria-label="תמונות המודעה">
        {photos.map((src, i) => (
          <img
            key={src}
            src={src}
            alt={`תמונה ${i + 1} מתוך ${total}`}
            loading={eager && i === 0 ? 'eager' : 'lazy'}
            decoding="async"
            draggable={false}
          />
        ))}
      </div>
      {total > 1 && (
        <>
          {index > 0 && (
            <button className="nav prev" type="button" aria-label="התמונה הקודמת" onClick={step(-1)} />
          )}
          {index < total - 1 && (
            <button className="nav next" type="button" aria-label="התמונה הבאה" onClick={step(1)} />
          )}
          <div className="dots" aria-hidden="true">
            {photos.slice(0, 8).map((src, i) => (
              <i key={src} className={i === Math.min(index, 7) ? 'on' : undefined} />
            ))}
          </div>
          <span className="count" aria-hidden="true">
            {photoPosition(index, total)}
          </span>
        </>
      )}
      {videos.length > 0 && <span className="vchip">וידאו</span>}
    </div>
  )
}
