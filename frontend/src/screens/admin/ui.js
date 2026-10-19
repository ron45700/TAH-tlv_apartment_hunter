import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The admin's shared pieces (3.8 (c)): the reason chip, a post's row, a load that waits out the
// site's first grouping (#380), and a link inside the site.
import { forwardRef, useEffect, useState } from 'react';
import { ApiError } from '../../api';
import { REASON_FAMILY } from '../../admin/words';
import { formatPrice, israelTime, relativeTime } from '../../format';
import { adminPath, navigate } from '../../route';
const LOADING_RETRY_MS = 2000;
export function go(path) {
    return (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0)
            return;
        event.preventDefault();
        navigate(path);
    };
}
export function Link({ to, className, current = false, children, }) {
    return (_jsx("a", { href: to, className: className, onClick: go(to), "aria-current": current ? 'page' : undefined, children: children }));
}
/** A read that waits out "loading" (#380): asked again every 2 s. `again` reloads by hand. */
export function useLoad(fetcher, key) {
    const [load, setLoad] = useState({ state: 'loading' });
    const [tries, setTries] = useState(0);
    useEffect(() => {
        const controller = new AbortController();
        let retry = 0;
        fetcher(controller.signal)
            .then((data) => setLoad({ state: 'ready', data }))
            .catch((error) => {
            if (error instanceof DOMException)
                return;
            if (error instanceof ApiError && error.refusal === 'loading') {
                retry = window.setTimeout(() => setTries((n) => n + 1), LOADING_RETRY_MS);
            }
            else
                setLoad({ state: 'failed', status: error instanceof ApiError ? error.status : 0 });
        });
        return () => {
            window.clearTimeout(retry);
            controller.abort();
        };
    }, [key, tries]); // the fetcher follows `key`
    return [load, () => setTries((n) => n + 1)];
}
export function Waiting({ load, children }) {
    if (load.state === 'loading')
        return _jsx("p", { className: "adm-empty", children: "\u05D8\u05D5\u05E2\u05DF\u2026" });
    if (load.state === 'failed') {
        return (_jsx("p", { className: "adm-empty", children: load.status === 403
                ? 'הדף הזה למנהל בלבד.'
                : load.status === 404
                    ? 'לא נמצא: המודעה כבר לא שמורה (מודעה נמחקת 40 יום אחרי הפרסום האחרון).'
                    : 'הטעינה נכשלה. בדקו שהאתר פועל ורעננו את הדף.' }));
    }
    return _jsx(_Fragment, { children: children(load.data) });
}
export function ReasonChip({ row }) {
    if (!row.reason)
        return _jsx("span", { className: "rchip rchip-state", children: row.state_words });
    return _jsx("span", { className: `rchip rchip-${REASON_FAMILY[row.reason]}`, children: row.reason_words });
}
export function when(iso, now) {
    return iso ? `${relativeTime(iso, now)} (${israelTime(iso)})` : '—';
}
/** One post in a list: its first photo, its first lines, its reason and what the admin needs at a
 * glance. The whole row opens the post's detail. */
export function PostRow({ row, now, children }) {
    const price = row.listing ? formatPrice(row.listing.price) : null;
    const to = adminPath('post', row.id);
    return (_jsxs("li", { className: "arow", children: [_jsxs("a", { className: "arow-open", href: to, onClick: go(to), children: [_jsx("span", { className: "arow-thumb", "aria-hidden": "true", children: row.photo ? _jsx("img", { src: row.photo, alt: "", loading: "lazy" }) : _jsx("span", { className: "arow-nophoto", children: "\u05D0\u05D9\u05DF \u05EA\u05DE\u05D5\u05E0\u05D4" }) }), _jsxs("span", { className: "arow-body", children: [_jsxs("span", { className: "arow-head", children: [_jsx(ReasonChip, { row: row }), row.city && _jsx("span", { className: "arow-city", children: row.city }), price && _jsx("span", { className: "arow-price", children: price }), _jsx("span", { className: "arow-time", children: relativeTime(row.last_published_at, now) })] }), _jsx("span", { className: "arow-text", dir: "auto", children: (row.text ?? '').trim() || 'אין טקסט' }), (row.publications > 1 || row.failures > 0 || row.corrected.length > 0) && (_jsxs("span", { className: "arow-meta", children: [row.publications > 1 && _jsxs("span", { children: ["\u05E4\u05D5\u05E8\u05E1\u05DE\u05D4 ", row.publications, " \u05E4\u05E2\u05DE\u05D9\u05DD"] }), row.failures > 0 && (_jsxs("span", { className: "arow-fail", children: ["\u05E0\u05DB\u05E9\u05DC\u05D4 \u05D1\u05E1\u05D9\u05D5\u05D5\u05D2 ", row.failures === 1 ? 'פעם אחת' : `${row.failures} פעמים`, row.last_error ? `: ${row.last_error}` : ''] })), row.corrected.length > 0 && _jsx("span", { children: "\u05EA\u05D5\u05E7\u05E0\u05D4 \u05D1\u05D9\u05D3" })] }))] })] }), children] }));
}
/** Where the admin's pages say what a write did (#409, #411): a polite status and an alert, both in
 * the page before anything fills them, so a screen reader announces each message. The box takes
 * the focus after a write that removed the button pressed (a restore, a leave-out). */
export const Announce = forwardRef(function Announce({ message }, ref) {
    const ok = message?.ok ? message.text : '';
    const error = message && !message.ok ? message.text : '';
    return (_jsxs("div", { ref: ref, className: "announce", tabIndex: -1, children: [_jsx("p", { role: "status", className: ok ? 'formok' : undefined, children: ok }), _jsx("p", { role: "alert", className: error ? 'formerror' : undefined, children: error })] }));
});
