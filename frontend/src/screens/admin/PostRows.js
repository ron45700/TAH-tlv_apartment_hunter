import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The admin's post lists (3.8 (c)): rejected (with the reason chips and their counts, #403), pending,
// archive and flags (by user and flag action, #393). Canonicals only (#75 B). They come in pages as
// the users' list does (#376): the whole order with the first rows, the rest as the admin scrolls.
import { useCallback, useEffect, useRef, useState } from 'react';
import { adminApi } from '../../admin/api';
import { REASON_FAMILY, REASON_NAMES, REASON_ORDER, flagActions, restoreLabel } from '../../admin/words';
import { ApiError } from '../../api';
import { PAGE, firstLoad, nextIds, withPage, withoutCard } from '../../paging';
import { Announce, PostRow, useLoad, Waiting, when } from './ui';
const RETRY_MS = 2000;
const EMPTY = {
    rejected: 'אין מודעות שנדחו.',
    pending: 'אין מודעות שממתינות לסיווג.',
    archive: 'הארכיון ריק. מודעות עוברות לארכיון רק משלב 5.',
    flags: 'אף משתמש לא סימן מודעה כמשקרת.',
};
const LEADS = {
    rejected: 'כל מודעה שנדחתה, מכל סיבה. רק המודעה המקורית, בלי הפרסומים החוזרים שלה.',
    pending: 'מודעות שעוד לא סווגו. ההרצה הבאה של classify_pending תסווג אותן.',
    archive: 'מודעות שעברו לארכיון, עם הסיבה שהייתה להן.',
    flags: 'מודעות שמשתמשים סימנו כמשקרות, לפי המשתמש ולפי הסימון. סימון אחד על מודעה שפורסמה כמה פעמים חל על כל הפרסומים.',
};
export function PostRows({ list, now, onChanged }) {
    const [reason, setReason] = useState(null);
    const [loaded, setLoaded] = useState(null);
    const [reasons, setReasons] = useState({});
    const [notice, setNotice] = useState(null);
    const announce = useRef(null);
    const [busy, setBusy] = useState(false);
    const [load] = useLoad((signal) => adminApi.rows(list, reason, PAGE, signal), `${list}:${reason ?? ''}`);
    useEffect(() => {
        setReason(null);
        setLoaded(null);
    }, [list]);
    useEffect(() => {
        if (load.state !== 'ready')
            return;
        setLoaded(firstLoad(load.data));
        if (load.data.reasons)
            setReasons(load.data.reasons);
    }, [load]);
    const paging = useRef(false);
    const [retries, setRetries] = useState(0);
    const sentinel = useRef(null);
    const more = useCallback(() => {
        if (!loaded || paging.current)
            return;
        const ids = nextIds(loaded);
        if (ids.length === 0)
            return;
        paging.current = true;
        const from = loaded.order;
        adminApi
            .rowsById(list, reason, ids)
            .then((page) => setLoaded((current) => (current && current.order === from ? withPage(current, ids, page) : current)))
            .catch(() => window.setTimeout(() => setRetries((n) => n + 1), RETRY_MS))
            .finally(() => {
            paging.current = false;
        });
    }, [loaded, list, reason]);
    useEffect(() => {
        const target = sentinel.current;
        if (!target || !loaded || loaded.next >= loaded.order.length)
            return;
        const observer = new IntersectionObserver((entries) => entries.some((e) => e.isIntersecting) && more(), {
            rootMargin: '0px 0px 150% 0px',
        });
        observer.observe(target);
        return () => observer.disconnect();
    }, [loaded, more, retries]);
    /** A flag action's posts restored together (#393), each by its own compare and set: the
     * restored rows leave the list in place; a post that changed meanwhile stays, and the page says so. */
    const restoreRows = (rows) => {
        const words = rows.length === 1 ? 'את המודעה' : `את ${rows.length} הפרסומים`;
        if (!window.confirm(`לשחזר ${words}? הסימון יוסר, והמצב יחושב מחדש מהסיווג.`))
            return;
        setBusy(true);
        setNotice(null);
        adminApi
            .restore(rows.map((row) => ({ listing_id: row.id, version: row.version })))
            .then(({ results }) => {
            const restored = results.filter((r) => r.outcome === 'restored').map((r) => r.listing_id);
            setLoaded((current) => restored.reduce((acc, id) => (acc ? withoutCard(acc, id) : acc), current));
            const left = results.length - restored.length;
            setNotice(left === 0
                ? { ok: true, text: restored.length === 1 ? 'המודעה שוחזרה.' : `${restored.length} פרסומים שוחזרו.` }
                : { ok: false, text: `שוחזרו ${restored.length} מתוך ${results.length}: השאר השתנו בינתיים. רעננו את הדף ונסו שוב.` });
            onChanged();
            requestAnimationFrame(() => announce.current?.focus()); // the button pressed is gone (#411)
        })
            .catch((error) => setNotice({ ok: false, text: error instanceof ApiError ? 'השחזור נדחה.' : 'השחזור לא נשמר. בדקו את החיבור ונסו שוב.' }))
            .finally(() => setBusy(false));
    };
    const total = Object.values(reasons).reduce((sum, n) => sum + (n ?? 0), 0);
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: LEADS[list] }), list === 'rejected' && total > 0 && (_jsxs("div", { className: "reasonbar", role: "group", "aria-label": "\u05E1\u05D9\u05E0\u05D5\u05DF \u05DC\u05E4\u05D9 \u05E1\u05D9\u05D1\u05D4", children: [_jsxs("button", { type: "button", className: "rfilter", "aria-pressed": reason === null, onClick: () => setReason(null), children: ["\u05D4\u05DB\u05DC ", _jsx("span", { className: "rcount", children: total })] }), REASON_ORDER.filter((name) => reasons[name]).map((name) => (_jsxs("button", { type: "button", className: `rfilter rfilter-${REASON_FAMILY[name]}`, "aria-pressed": reason === name, onClick: () => setReason(name), children: [REASON_NAMES[name], " ", _jsx("span", { className: "rcount", children: reasons[name] })] }, name)))] })), _jsx(Announce, { ref: announce, message: notice }), _jsx(Waiting, { load: load, children: () => !loaded ? (_jsx("p", { className: "adm-empty", children: "\u05D8\u05D5\u05E2\u05DF\u2026" })) : loaded.count === 0 ? (_jsx("p", { className: "adm-empty", children: EMPTY[list] })) : (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-count", children: loaded.count === 1 ? 'מודעה אחת' : `${loaded.count} מודעות` }), list === 'flags' ? (_jsx(Flags, { rows: loaded.cards, now: now, busy: busy, onRestore: restoreRows })) : (_jsx(Rows, { rows: loaded.cards, now: now })), loaded.next < loaded.order.length && _jsx("div", { ref: sentinel, className: "sentinel", "aria-hidden": "true" })] })) })] }));
}
function Rows({ rows, now }) {
    return (_jsx("ul", { className: "arows", children: rows.map((row) => (_jsx(PostRow, { row: row, now: now }, row.id))) }));
}
function Flags({ rows, now, busy, onRestore, }) {
    return (_jsx(_Fragment, { children: flagActions(rows).map((action) => (_jsxs("section", { className: "flagaction", children: [_jsxs("h2", { children: ["\u05E1\u05D9\u05DE\u05D5\u05DF \u05E9\u05DC ", _jsx("bdi", { dir: "ltr", children: action.flag.by }), ":", ' ', action.rows.length === 1 ? 'מודעה אחת' : `${action.rows.length} פרסומים של אותה מודעה`, _jsx("span", { className: "flagaction-time", children: when(action.flag.at, now) })] }), _jsx("button", { type: "button", className: "barbtn flagaction-restore", disabled: busy, "aria-label": restoreLabel(action.rows).label, onClick: () => onRestore(action.rows), children: restoreLabel(action.rows).text }), action.flag.note && (_jsx("p", { className: "flagaction-note", dir: "auto", children: action.flag.note })), _jsx(Rows, { rows: action.rows, now: now })] }, action.key))) }));
}
