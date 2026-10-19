import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { closedChips, formatEntry, formatFloor, formatPrice, kindLine, locationLine, publishedTimes, relativeTime, roomsClosed, sizeClosed, } from '../format';
import { hideOffer } from '../paging';
import { postPath } from '../route';
import { ActionMenu } from './actions';
import { Carousel } from './Carousel';
import { InfoButton } from './InfoButton';
/** How a colour reads to a screen reader: the state in words (#323). */
export const COLOUR_WORDS = {
    green: 'חיובי',
    red: 'לא מתאים להעדפה שלך',
    grey: 'לא צוין במודעה',
    orange: 'לא ברור',
    plain: '',
    missing: 'חסר',
};
export function Card({ card, now, onOpen, actions }) {
    const kind = card.apartment_kind.value;
    const corrected = new Set(card.evaluation.corrected);
    const line = kindLine(kind, card.evaluation.kind_marked, card.evaluation.option, card.post_nature === 'sublet_offer');
    const price = formatPrice(card.price);
    const entry = formatEntry(card);
    const chips = closedChips(card, card.colours);
    const reposts = publishedTimes(card.publications);
    const sizeField = kind === 'room' && card.room_size_sqm.state === 'written' ? 'room_size_sqm' : 'size_sqm';
    const offer = actions ? hideOffer(card) : null;
    const open = (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0)
            return;
        event.preventDefault();
        onOpen(card.id);
    };
    return (_jsxs("article", { className: `card ${card.glow ? `glow-${card.glow}` : 'glow-none'}${card.viewed ? ' is-viewed' : ''}${card.hidden ? ' is-hidden' : ''}`, children: [_jsx("a", { className: "open", href: postPath(card.id), onClick: open, "aria-label": `פתיחת המודעה${card.viewed ? ', נצפתה' : ''}${card.hidden ? ', מוסתרת' : ''}${card.tier_label ? `. ${card.tier_label}` : ''}` }), _jsxs("div", { className: "media", children: [_jsx(Carousel, { photos: card.photos, videos: card.videos, variant: "card" }), card.tier_label && _jsx(InfoButton, { label: card.tier_label }), offer && actions && (_jsx("button", { type: "button", className: "hidepill", onClick: (event) => {
                            event.preventDefault();
                            event.stopPropagation();
                            if (offer === 'hide')
                                actions.onHide(card.id);
                            else
                                actions.onUnhide(card.id);
                        }, children: offer === 'hide' ? 'הסתר' : 'בטל הסתרה' }))] }), _jsxs("div", { className: "body", children: [_jsxs("div", { className: "kindrow", children: [_jsx("span", { className: line.unclear ? 'kind kind-unclear' : 'kind', children: line.text }), card.hidden && _jsx("span", { className: "seen hidden-tag", children: "\u05DE\u05D5\u05E1\u05EA\u05E8\u05EA" }), card.viewed && _jsx("span", { className: "seen", children: "\u05E0\u05E6\u05E4\u05D4" })] }), _jsxs("div", { className: "pricerow", children: [price === null ? (_jsx("span", { className: "missing", children: "\u05D0\u05D9\u05DF \u05DE\u05D7\u05D9\u05E8" })) : (_jsx("span", { className: `price c-${card.colours.price}`, children: price })), corrected.has('price') && _jsx(Fixed, {})] }), _jsx("p", { className: "txt clamp", dir: "auto", children: card.text }), _jsxs("p", { className: `loc c-${card.colours.areas}`, children: [locationLine(card), corrected.has('areas') && _jsx(Fixed, {})] }), _jsxs("dl", { className: "stats", children: [_jsx(Stat, { label: "\u05D7\u05D3\u05E8\u05D9\u05DD", value: roomsClosed(kind, card.rooms), colour: card.colours.rooms, fixed: corrected.has('rooms') }), _jsx(Stat, { label: "\u05DE\u05F4\u05E8", value: sizeClosed(kind, card.size_sqm, card.room_size_sqm), colour: card.colours[sizeField], fixed: corrected.has('size_sqm') || corrected.has('room_size_sqm') }), _jsx(Stat, { label: "\u05E7\u05D5\u05DE\u05D4", value: formatFloor(card.floor, card.building_floors), colour: card.colours.floor, fixed: corrected.has('floor') }), _jsxs("div", { className: "stat", children: [_jsx("dt", { children: "\u05DB\u05E0\u05D9\u05E1\u05D4" }), _jsxs("dd", { children: [entry === null ? (_jsx("span", { className: "missing sm", children: "\u05D0\u05D9\u05DF \u05EA\u05D0\u05E8\u05D9\u05DA \u05DB\u05E0\u05D9\u05E1\u05D4" })) : (_jsx("span", { className: `one c-${card.colours.entry_date}`, children: entry })), corrected.has('entry_date') && _jsx(Fixed, {})] })] })] }), _jsxs("p", { className: "phoneline", children: [_jsx("span", { className: `c-${card.colours.rooms}`, children: roomsLine(kind, card) }), _jsx("span", { className: "sep", "aria-hidden": "true" }), entry === null ? (_jsx("span", { className: "missing sm", children: "\u05D0\u05D9\u05DF \u05EA\u05D0\u05E8\u05D9\u05DA \u05DB\u05E0\u05D9\u05E1\u05D4" })) : (_jsx("span", { className: `one c-${card.colours.entry_date}`, children: entry.startsWith('כניסה') ? entry : `כניסה: ${entry}` }))] }), _jsxs("div", { className: "feats", children: [card.evaluation.women_only_icon && _jsx("span", { className: "chip chip-women", children: "\u05E0\u05E9\u05D9\u05DD \u05D1\u05DC\u05D1\u05D3" }), chips.map((chip) => (_jsxs("span", { className: "chip c-green", "aria-label": `${chip.text}, ${COLOUR_WORDS.green}`, children: [chip.text, corrected.has(chip.field) && _jsx(Fixed, {})] }, chip.field)))] }), _jsxs("div", { className: "foot", children: [_jsx("span", { className: "when", children: relativeTime(card.last_published_at, now) }), _jsxs("div", { className: "acts", children: [_jsx("a", { className: "btn-o btn-fb", href: card.permalink, target: "_blank", rel: "noopener noreferrer", children: "\u05E4\u05D9\u05D9\u05E1\u05D1\u05D5\u05E7" }), card.whatsapp && (_jsx("a", { className: "btn-o btn-wa", href: card.whatsapp, target: "_blank", rel: "noopener noreferrer", children: "\u05D5\u05D5\u05D0\u05D8\u05E1\u05D0\u05E4" })), actions && (_jsx(ActionMenu, { label: "\u05D3\u05D9\u05D5\u05D5\u05D7", className: "btn-o btn-rep", items: [
                                            { label: 'המודעה משקרת', onSelect: () => actions.onFlag(card.id) },
                                            { label: 'סיווג שגוי', onSelect: () => actions.onReport(card.id) },
                                        ] }))] }), _jsx("span", { className: "reposts", children: reposts })] })] })] }));
}
function Stat({ label, value, colour, fixed }) {
    return (_jsxs("div", { className: "stat", children: [_jsx("dt", { children: label }), _jsxs("dd", { children: [_jsx("span", { className: value.missing ? 'ns' : `c-${colour}`, children: value.text }), fixed && _jsx(Fixed, {}), value.note && _jsx("span", { className: "note", children: value.note })] })] }));
}
/** The phone's line beside the photo (3.7 (c), rows 7 and 18): the rooms, then the entry date. */
function roomsLine(kind, card) {
    const rooms = roomsClosed(kind, card.rooms);
    if (kind === 'room')
        return rooms.note ? `חדר · ${rooms.note}` : `${rooms.text} חדרים`;
    return rooms.missing ? 'חדרים: לא צוין' : `${rooms.text} חדרים`;
}
/** "Corrected by hand" beside a corrected item (#256): "תוקן" on the card, "תוקן ידנית" inside. */
export function Fixed({ long = false }) {
    return _jsx("span", { className: "fixed", children: long ? 'תוקן ידנית' : 'תוקן' });
}
