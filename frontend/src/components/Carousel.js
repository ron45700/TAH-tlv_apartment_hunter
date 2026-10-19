import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The photo carousel, on the closed card and in the opened post (#327, #332 point 30): a scroll-snap
// track the finger swipes, arrows on hover (drawn in CSS: controls, not state glyphs), dots and a
// "1/5" count. Photos load lazily, as they come near the view (#330 point 12). A post with no photo
// but a video shows the link to the video in the photo's place, never "no photos" (round 9).
import { useRef, useState } from 'react';
import { photoPosition } from '../format';
export function Carousel({ photos, videos, variant, eager = false }) {
    const track = useRef(null);
    const [index, setIndex] = useState(0);
    const total = photos.length;
    if (total === 0) {
        return (_jsx("div", { className: `car car-${variant} car-empty`, children: videos.length > 0 ? (_jsx("a", { className: "vlink", href: videos[0], target: "_blank", rel: "noopener noreferrer", children: "\u05E6\u05E4\u05D9\u05D9\u05D4 \u05D1\u05E1\u05E8\u05D8\u05D5\u05DF \u05D1\u05E4\u05D9\u05D9\u05E1\u05D1\u05D5\u05E7" })) : (_jsx("span", { className: "car-none", children: "\u05D0\u05D9\u05DF \u05EA\u05DE\u05D5\u05E0\u05D5\u05EA" })) }));
    }
    const onScroll = () => {
        const el = track.current;
        if (!el || el.clientWidth === 0)
            return;
        setIndex(Math.min(total - 1, Math.round(Math.abs(el.scrollLeft) / el.clientWidth)));
    };
    // The page is right to left: the next photo lies to the left.
    const step = (direction) => (event) => {
        event.preventDefault();
        event.stopPropagation();
        const el = track.current;
        if (!el)
            return;
        const rtl = getComputedStyle(el).direction === 'rtl';
        el.scrollBy({ left: direction * el.clientWidth * (rtl ? -1 : 1), behavior: 'smooth' });
    };
    return (_jsxs("div", { className: `car car-${variant}`, children: [_jsx("div", { className: "track", ref: track, onScroll: onScroll, tabIndex: 0, "aria-label": "\u05EA\u05DE\u05D5\u05E0\u05D5\u05EA \u05D4\u05DE\u05D5\u05D3\u05E2\u05D4", children: photos.map((src, i) => (_jsx("img", { src: src, alt: `תמונה ${i + 1} מתוך ${total}`, loading: eager && i === 0 ? 'eager' : 'lazy', decoding: "async", draggable: false }, src))) }), total > 1 && (_jsxs(_Fragment, { children: [index > 0 && (_jsx("button", { className: "nav prev", type: "button", "aria-label": "\u05D4\u05EA\u05DE\u05D5\u05E0\u05D4 \u05D4\u05E7\u05D5\u05D3\u05DE\u05EA", onClick: step(-1) })), index < total - 1 && (_jsx("button", { className: "nav next", type: "button", "aria-label": "\u05D4\u05EA\u05DE\u05D5\u05E0\u05D4 \u05D4\u05D1\u05D0\u05D4", onClick: step(1) })), _jsx("div", { className: "dots", "aria-hidden": "true", children: photos.slice(0, 8).map((src, i) => (_jsx("i", { className: i === Math.min(index, 7) ? 'on' : undefined }, src))) }), _jsx("span", { className: "count", "aria-hidden": "true", children: photoPosition(index, total) })] })), videos.length > 0 && _jsx("span", { className: "vchip", children: "\u05D5\u05D9\u05D3\u05D0\u05D5" })] }));
}
