import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import { featureChips, formatEntry, formatFee, formatFloor, formatPrice, israelTime, kindLine, phoneLabel, relativeTime, roomsOpen, sizeOpen, NOT_STATED, } from '../format';
import { ActionMenu, ReportForm } from './actions';
import { Carousel } from './Carousel';
import { hideOffer } from '../paging';
import { COLOUR_WORDS, Fixed } from './Card';
export function PostView({ id, card, now, phone, onClose, actions }) {
    const [post, setPost] = useState(null);
    const [failed, setFailed] = useState(null);
    const [viewed, setViewed] = useState(false);
    const [reporting, setReporting] = useState(false);
    const sheet = useRef(null);
    const latest = useRef(actions);
    latest.current = actions;
    useEffect(() => {
        const controller = new AbortController();
        setPost(null);
        setFailed(null);
        api
            .post(id, controller.signal)
            .then(setPost)
            .catch((error) => {
            if (error instanceof ApiError)
                setFailed(error.status);
        });
        return () => controller.abort();
    }, [id]);
    // Opening marks the card viewed for a signed-in user (#253); the first time is kept (#276).
    const signedIn = actions !== undefined;
    useEffect(() => {
        if (!post || !signedIn)
            return;
        let live = true;
        api
            .markViewed(post.id)
            .then(() => {
            if (!live)
                return;
            setViewed(true);
            latest.current?.onViewed(post.post_ids, true);
        })
            .catch(() => undefined); // the card simply stays unviewed (3.7 (i))
        if (latest.current?.startReport)
            setReporting(true);
        return () => {
            live = false;
        };
    }, [post, signedIn]);
    const unview = () => {
        if (!post)
            return;
        api
            .unmarkViewed(post.id)
            .then(() => {
            setViewed(false);
            latest.current?.onViewed(post.post_ids, false);
        })
            .catch((error) => {
            if (error instanceof ApiError && error.refusal === 'gone')
                latest.current?.onGone();
        });
    };
    const items = post
        ? [
            { label: 'המודעה משקרת', onSelect: () => actions?.onFlag(post.id) },
            { label: 'דיווח על סיווג שגוי', onSelect: () => setReporting(true) },
        ]
        : [];
    // "הסתר" / "בטל הסתרה" by the list's card (the opened post carries no tier): none for a post
    // opened by its own address, which has no card in the list.
    const listed = post && card?.id === post.id ? card : undefined;
    const offer = actions && listed ? hideOffer(listed, viewed || listed.viewed === true) : null;
    const hideItems = offer && post
        ? [
            offer === 'hide'
                ? { label: 'הסתר', onSelect: () => actions?.onHide(post.id) }
                : { label: 'בטל הסתרה', onSelect: () => actions?.onUnhide(post.id) },
        ]
        : [];
    useEffect(() => {
        const previous = document.activeElement;
        sheet.current?.focus();
        document.body.classList.add('locked');
        const onKey = (event) => event.key === 'Escape' && onClose();
        document.addEventListener('keydown', onKey);
        return () => {
            document.body.classList.remove('locked');
            document.removeEventListener('keydown', onKey);
            previous?.focus?.();
        };
    }, [onClose]);
    return (_jsxs("div", { className: "post", role: "dialog", "aria-modal": "true", "aria-label": "\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4", children: [!phone && _jsx("div", { className: "backdrop", onClick: onClose, "aria-hidden": "true" }), _jsxs("div", { className: "sheet", ref: sheet, tabIndex: -1, children: [_jsx("div", { className: "topbar", children: phone ? (_jsxs(_Fragment, { children: [_jsx("button", { className: "back", type: "button", onClick: onClose, children: "\u05D7\u05D6\u05E8\u05D4" }), actions && post && (_jsx(ActionMenu, { label: "\u05E4\u05E2\u05D5\u05DC\u05D5\u05EA", className: "btn-o btn-act", placement: "down", items: [...(viewed ? [{ label: 'סימון כלא נצפה', onSelect: unview }] : []), ...hideItems, ...items] }))] })) : (_jsx("button", { className: "close", type: "button", onClick: onClose, "aria-label": "\u05E1\u05D2\u05D9\u05E8\u05D4" })) }), post ? (_jsx(Body, { post: post, card: card?.id === post.id ? card : undefined, now: now, phone: phone, foot: actions && !phone ? (_jsxs("div", { className: "bottombar-end", children: [viewed && (_jsx("button", { type: "button", className: "btn quiet", onClick: unview, children: "\u05E1\u05D9\u05DE\u05D5\u05DF \u05DB\u05DC\u05D0 \u05E0\u05E6\u05E4\u05D4" })), hideItems.map((item) => (_jsx("button", { type: "button", className: "btn quiet", onClick: item.onSelect, children: item.label }, item.label))), _jsx(ActionMenu, { label: "\u05D3\u05D9\u05D5\u05D5\u05D7", className: "btn rep", items: items })] })) : null })) : (_jsx("p", { className: "sheet-state", children: failed === 404
                            ? 'המודעה כבר לא מוצגת: היא הוסרה או עברה לארכיון.'
                            : failed !== null
                                ? 'לא הצלחנו לטעון את המודעה. נסו שוב.'
                                : 'טוען…' }))] }), reporting && post && actions && (_jsx(ReportForm, { fields: actions.reportFields, onCancel: () => setReporting(false), onSend: (fields, note) => api
                    .report(post.id, fields, note)
                    .then((answer) => {
                    setReporting(false);
                    latest.current?.onReported(answer.removed);
                })
                    .catch((error) => {
                    if (error instanceof ApiError && error.refusal === 'gone') {
                        setReporting(false);
                        latest.current?.onGone();
                        return;
                    }
                    throw error;
                }) }))] }));
}
function Body({ post, card, now, phone, foot, }) {
    const colours = card?.colours ?? post.own_colours;
    const corrected = new Set(post.corrected);
    const kind = post.apartment_kind.value;
    const line = kindLine(kind, card?.evaluation.kind_marked ?? post.apartment_kind.state !== 'written', card?.evaluation.option ?? null, post.post_nature === 'sublet_offer');
    const price = formatPrice(post.price);
    const entry = formatEntry(post);
    const mobile = post.phones.find((phoneEntry) => phoneEntry.whatsapp);
    const sizeField = kind === 'room' && post.room_size_sqm.state === 'written' ? 'room_size_sqm' : 'size_sqm';
    return (_jsxs(_Fragment, { children: [_jsx(Carousel, { photos: post.photos, videos: post.videos, variant: "open", eager: true }), _jsxs("div", { className: "content", children: [_jsxs("div", { className: "pblock", children: [card?.tier_label && _jsx("p", { className: `tierline t-${card.glow ?? 'none'}`, children: card.tier_label }), _jsx("span", { className: line.unclear ? 'kind kind-unclear' : 'kind', children: line.text }), _jsxs("div", { className: "pricerow big", children: [price === null ? (_jsx("span", { className: "missing", children: "\u05D0\u05D9\u05DF \u05DE\u05D7\u05D9\u05E8" })) : (_jsx("span", { className: `price c-${colours.price}`, children: price })), corrected.has('price') && _jsx(Fixed, { long: true })] }), post.gender !== 'no_restriction' && (_jsx("div", { className: "gender", children: post.gender === 'women_only' ? (_jsx("span", { className: "chip chip-women", children: "\u05E0\u05E9\u05D9\u05DD \u05D1\u05DC\u05D1\u05D3" })) : (_jsx("span", { className: "chip c-plain", children: "\u05E2\u05D3\u05D9\u05E4\u05D5\u05EA \u05DC\u05D1\u05E0\u05D5\u05EA" })) })), _jsxs("p", { className: "meta", children: ["\u05E4\u05D5\u05E8\u05E1\u05DD ", relativeTime(post.last_published_at, now)] })] }), _jsx("div", { className: "feats feats-open", children: featureChips(post).map((chip) => {
                            const colour = colours[chip.field] ?? 'plain';
                            const words = COLOUR_WORDS[colour];
                            return (_jsxs("span", { className: `chip c-${colour}`, "aria-label": words ? `${chip.text}, ${words}` : chip.text, children: [chip.text, corrected.has(chip.field) && _jsx(Fixed, { long: true })] }, chip.field));
                        }) }), _jsxs("dl", { className: "rows", children: [_jsx(Row, { label: "\u05D7\u05D3\u05E8\u05D9\u05DD", value: roomsOpen(kind, post.rooms), colour: colours.rooms, fixed: corrected.has('rooms') }), _jsx(Row, { label: "\u05D2\u05D5\u05D3\u05DC", value: sizeOpen(kind, post.size_sqm, post.room_size_sqm), colour: colours[sizeField], fixed: corrected.has('size_sqm') || corrected.has('room_size_sqm') }), _jsx(Row, { label: "\u05E7\u05D5\u05DE\u05D4", value: formatFloor(post.floor, post.building_floors), colour: colours.floor, fixed: corrected.has('floor') }), _jsxs("div", { className: "row", children: [_jsx("dt", { children: "\u05EA\u05D0\u05E8\u05D9\u05DA \u05DB\u05E0\u05D9\u05E1\u05D4" }), _jsxs("dd", { children: [entry === null ? (_jsx("span", { className: "missing sm", children: "\u05D0\u05D9\u05DF \u05EA\u05D0\u05E8\u05D9\u05DA \u05DB\u05E0\u05D9\u05E1\u05D4" })) : (_jsx("span", { className: `c-${colours.entry_date}`, children: entry })), corrected.has('entry_date') && _jsx(Fixed, { long: true })] })] }), _jsx(Row, { label: "\u05D0\u05E8\u05E0\u05D5\u05E0\u05D4", value: formatFee(post.arnona), colour: colours.arnona, fixed: corrected.has('arnona') }), _jsx(Row, { label: "\u05D5\u05E2\u05D3 \u05D1\u05D9\u05EA", value: formatFee(post.house_committee), colour: colours.house_committee, fixed: corrected.has('house_committee') }), _jsx(Row, { label: "\u05D0\u05D6\u05D5\u05E8", value: areaText(post), colour: colours.areas, fixed: corrected.has('areas') }), _jsx(Row, { label: "\u05E8\u05D7\u05D5\u05D1", value: listOrMissing(post.streets), colour: "plain", fixed: corrected.has('streets') }), _jsx(Row, { label: "\u05DB\u05E4\u05D9 \u05E9\u05E0\u05DB\u05EA\u05D1 \u05D1\u05DE\u05D5\u05D3\u05E2\u05D4", value: listOrMissing(post.stated_area_names), colour: "plain", fixed: false })] }), _jsxs("section", { children: [_jsx("h3", { children: "\u05D4\u05D8\u05E7\u05E1\u05D8 \u05D4\u05DE\u05DC\u05D0" }), _jsx("p", { className: "txt full", dir: "auto", children: post.text })] }), post.phones.length > 0 && (_jsxs("section", { children: [_jsx("h3", { children: "\u05D8\u05DC\u05E4\u05D5\u05E0\u05D9\u05DD" }), _jsx("ul", { className: "phones", children: post.phones.map((phoneEntry) => (_jsxs("li", { children: [_jsx("a", { href: `tel:${phoneEntry.phone}`, dir: "ltr", children: phoneLabel(phoneEntry.phone, phoneEntry.name) }), phoneEntry.whatsapp && (_jsx("a", { className: "btn-o btn-wa", href: phoneEntry.whatsapp, target: "_blank", rel: "noopener noreferrer", children: "\u05D5\u05D5\u05D0\u05D8\u05E1\u05D0\u05E4" }))] }, phoneEntry.phone))) })] })), post.videos.length > 0 && (_jsx("section", { className: "videos", children: post.videos.map((video, i) => (_jsx("a", { className: "lk", href: video, target: "_blank", rel: "noopener noreferrer", children: post.videos.length > 1 ? `צפייה בסרטון ${i + 1} בפייסבוק` : 'צפייה בסרטון בפייסבוק' }, video))) })), post.publications.length > 1 && _jsx(Publications, { post: post, now: now, collapsed: phone })] }), _jsxs("div", { className: "bottombar", children: [_jsx("a", { className: "btn primary", href: post.permalink, target: "_blank", rel: "noopener noreferrer", children: "\u05DC\u05DE\u05D5\u05D3\u05E2\u05D4 \u05D4\u05DE\u05E7\u05D5\u05E8\u05D9\u05EA" }), mobile?.whatsapp && (_jsx("a", { className: "btn wa", href: mobile.whatsapp, target: "_blank", rel: "noopener noreferrer", children: "\u05D5\u05D5\u05D0\u05D8\u05E1\u05D0\u05E4" })), foot] })] }));
}
/** Every publication, the earliest first (#75 A, #122): relative and in Israel time. */
function Publications({ post, now, collapsed }) {
    const items = (_jsx("ol", { className: "pubs", children: post.publications.map((publication) => (_jsxs("li", { children: [relativeTime(publication.posted_at, now), ' ', _jsxs("span", { className: "meta", children: ["(", israelTime(publication.posted_at), ")"] })] }, publication.id))) }));
    const title = `פורסם ${post.publications.length} פעמים`;
    if (collapsed) {
        return (_jsxs("details", { className: "log", children: [_jsx("summary", { children: title }), items] }));
    }
    return (_jsxs("section", { className: "log", children: [_jsx("h3", { children: title }), items] }));
}
function Row({ label, value, colour, fixed }) {
    return (_jsxs("div", { className: "row", children: [_jsx("dt", { children: label }), _jsxs("dd", { children: [_jsx("span", { className: value.missing ? 'ns' : `c-${colour}`, children: value.text }), fixed && _jsx(Fixed, { long: true })] })] }));
}
function areaText(post) {
    if (post.areas.length)
        return { text: post.areas.map((area) => area.name).join(', ') };
    if (post.streets.length || post.stated_area_names.length)
        return { text: 'האזור לא ברור' };
    return { text: NOT_STATED, missing: true };
}
function listOrMissing(values) {
    return values.length ? { text: values.join(', ') } : { text: NOT_STATED, missing: true };
}
