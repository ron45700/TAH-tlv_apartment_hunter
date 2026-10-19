import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// A signed-in user's actions on a post (PHASE_3.md 3.7 (c) rows 31–33, (i); build step 6): the
// report button's small menu (#328, #338), the confirmation before "המודעה משקרת" (#300), the "wrong
// classification" form (#254, #277: the fields as Hebrew labels, a note of up to 500 characters),
// and the notice that says, in words, what a write did (#330 point 21). Colour plus words only
// (#323): no glyphs.
import { useEffect, useId, useRef, useState } from 'react';
import { ApiError } from '../api';
export const NOTE_LIMIT = 500; // characters (#277)
/** A button and its small menu: on the card the outlined "דיווח" (#338), opening upward; in the
 *  opened post the same; on a phone's opened post the top bar's "פעולות", opening downward. */
export function ActionMenu({ label, items, className, placement = 'up', }) {
    const [open, setOpen] = useState(false);
    const box = useRef(null);
    const button = useRef(null);
    useDismiss(open, setOpen, box, button);
    return (_jsxs("div", { className: "actmenu", ref: box, children: [_jsx("button", { ref: button, type: "button", className: className, "aria-haspopup": "menu", "aria-expanded": open, onClick: () => setOpen((value) => !value), children: label }), open && (_jsx("div", { className: `actmenu-list is-${placement}`, role: "menu", children: items.map((item) => (_jsx("button", { type: "button", role: "menuitem", onClick: () => {
                        setOpen(false);
                        item.onSelect();
                    }, children: item.label }, item.label))) }))] }));
}
/** Closes on a press outside `box` and on Escape (the focus back on `button`); Escape stops there,
 *  so an opened post behind the menu stays open. */
function useDismiss(open, setOpen, box, button) {
    useEffect(() => {
        if (!open)
            return;
        const onDown = (event) => {
            if (!box.current?.contains(event.target))
                setOpen(false);
        };
        const onKey = (event) => {
            if (event.key !== 'Escape')
                return;
            event.stopPropagation();
            setOpen(false);
            button.current?.focus();
        };
        document.addEventListener('pointerdown', onDown);
        document.addEventListener('keydown', onKey, true);
        return () => {
            document.removeEventListener('pointerdown', onDown);
            document.removeEventListener('keydown', onKey, true);
        };
    }, [open, setOpen, box, button]);
}
/** A small modal over everything: the focus starts on the `data-initial` control; Escape and the
 *  backdrop cancel; the focus goes back where it was. */
function Modal({ label, onCancel, children, wide = false, }) {
    const box = useRef(null);
    const cancel = useRef(onCancel);
    cancel.current = onCancel;
    useEffect(() => {
        const previous = document.activeElement;
        // the heading stays in view: focusing a button at the foot must not scroll the box
        box.current?.querySelector('[data-initial]')?.focus({ preventScroll: true });
        const onKey = (event) => {
            if (event.key !== 'Escape')
                return;
            event.stopPropagation();
            cancel.current();
        };
        document.addEventListener('keydown', onKey, true);
        return () => {
            document.removeEventListener('keydown', onKey, true);
            previous?.focus?.();
        };
    }, []);
    return (_jsxs("div", { className: "modal", role: "dialog", "aria-modal": "true", "aria-label": label, children: [_jsx("div", { className: "modal-backdrop", onClick: onCancel, "aria-hidden": "true" }), _jsx("div", { className: wide ? 'modal-box is-wide' : 'modal-box', ref: box, children: children })] }));
}
/** The confirmation before a "lied" flag (3.7 (c) row 32). */
export function ConfirmFlag({ busy, onConfirm, onCancel, }) {
    return (_jsxs(Modal, { label: "\u05E1\u05D9\u05DE\u05D5\u05DF \u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05DB\u05DE\u05E9\u05E7\u05E8\u05EA", onCancel: onCancel, children: [_jsx("h2", { className: "modal-title", children: "\u05DC\u05E1\u05DE\u05DF \u05E9\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05DE\u05E9\u05E7\u05E8\u05EA?" }), _jsx("p", { className: "modal-text", children: "\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05EA\u05D5\u05E1\u05E8 \u05DE\u05D4\u05E8\u05E9\u05D9\u05DE\u05D4 \u05E9\u05DC \u05DB\u05DC \u05D4\u05DE\u05E9\u05EA\u05DE\u05E9\u05D9\u05DD \u05D5\u05EA\u05E2\u05D1\u05D5\u05E8 \u05DC\u05D1\u05D3\u05D9\u05E7\u05EA \u05D4\u05DE\u05E0\u05D4\u05DC. \u05D0\u05DD \u05D4\u05D9\u05D0 \u05E4\u05D5\u05E8\u05E1\u05DE\u05D4 \u05DB\u05DE\u05D4 \u05E4\u05E2\u05DE\u05D9\u05DD, \u05DB\u05DC \u05D4\u05E4\u05E8\u05E1\u05D5\u05DE\u05D9\u05DD \u05E9\u05DC\u05D4 \u05D9\u05E1\u05D5\u05DE\u05E0\u05D5." }), _jsxs("div", { className: "modal-actions", children: [_jsx("button", { type: "button", className: "btn danger", onClick: onConfirm, disabled: busy, children: busy ? 'מסמן…' : 'כן, המודעה משקרת' }), _jsx("button", { type: "button", className: "btn", onClick: onCancel, "data-initial": true, children: "\u05D1\u05D9\u05D8\u05D5\u05DC" })] })] }));
}
/** The "wrong classification" form (3.7 (c) row 33): one or more fields and an optional note. */
export function ReportForm({ fields, onSend, onCancel, }) {
    const [picked, setPicked] = useState([]);
    const [note, setNote] = useState('');
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null);
    const noteId = useId();
    const toggle = (field) => setPicked((current) => (current.includes(field) ? current.filter((f) => f !== field) : [...current, field]));
    const send = () => {
        if (!picked.length) {
            setProblem('בחרו לפחות פרט אחד שסווג לא נכון.');
            return;
        }
        setBusy(true);
        setProblem(null);
        const inOrder = fields.map((f) => f.field).filter((f) => picked.includes(f));
        onSend(inOrder, note.trim() ? note.trim() : null)
            .catch((error) => setProblem(reportProblem(error)))
            .finally(() => setBusy(false));
    };
    return (_jsxs(Modal, { label: "\u05D3\u05D9\u05D5\u05D5\u05D7 \u05E2\u05DC \u05E1\u05D9\u05D5\u05D5\u05D2 \u05E9\u05D2\u05D5\u05D9", onCancel: onCancel, wide: true, children: [_jsx("h2", { className: "modal-title", children: "\u05D3\u05D9\u05D5\u05D5\u05D7 \u05E2\u05DC \u05E1\u05D9\u05D5\u05D5\u05D2 \u05E9\u05D2\u05D5\u05D9" }), _jsx("p", { className: "modal-text", children: "\u05E1\u05DE\u05E0\u05D5 \u05DE\u05D4 \u05E1\u05D5\u05D5\u05D2 \u05DC\u05D0 \u05E0\u05DB\u05D5\u05DF. \u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05EA\u05D5\u05E1\u05E8 \u05DE\u05D4\u05E8\u05E9\u05D9\u05DE\u05D4 \u05E2\u05D3 \u05E9\u05D4\u05DE\u05E0\u05D4\u05DC \u05D9\u05D1\u05D3\u05D5\u05E7 \u05D5\u05D9\u05EA\u05E7\u05DF \u05D0\u05D5\u05EA\u05D4." }), _jsxs("fieldset", { className: "report-fields", children: [_jsx("legend", { children: "\u05DE\u05D4 \u05DC\u05D0 \u05E0\u05DB\u05D5\u05DF?" }), _jsx("div", { className: "rtiles", children: fields.map(({ field, label }) => (_jsxs("label", { className: picked.includes(field) ? 'rtile is-picked' : 'rtile', children: [_jsx("input", { type: "checkbox", name: `report-${field}`, checked: picked.includes(field), onChange: () => toggle(field) }), _jsx("span", { children: label })] }, field))) })] }), _jsxs("div", { className: "report-note", children: [_jsx("label", { htmlFor: noteId, children: "\u05D4\u05E2\u05E8\u05D4 (\u05DC\u05D0 \u05D7\u05D5\u05D1\u05D4)" }), _jsx("textarea", { id: noteId, name: "report-note", dir: "auto", rows: 3, maxLength: NOTE_LIMIT, value: note, onChange: (event) => setNote(event.target.value), placeholder: "\u05DC\u05DE\u05E9\u05DC: \u05D4\u05DE\u05D7\u05D9\u05E8 \u05D1\u05DE\u05D5\u05D3\u05E2\u05D4 \u05D4\u05D5\u05D0 \u05DC\u05D7\u05D3\u05E8, \u05DC\u05D0 \u05DC\u05D3\u05D9\u05E8\u05D4" }), _jsxs("span", { className: "report-count", children: [note.length, "/", NOTE_LIMIT] })] }), problem && (_jsx("p", { className: "formerror", role: "alert", children: problem })), _jsxs("div", { className: "modal-actions", children: [_jsx("button", { type: "button", className: "btn danger", onClick: send, disabled: busy, children: busy ? 'שולח…' : picked.length ? `שליחת הדיווח (${picked.length})` : 'שליחת הדיווח' }), _jsx("button", { type: "button", className: "btn", onClick: onCancel, "data-initial": true, children: "\u05D1\u05D9\u05D8\u05D5\u05DC" })] })] }));
}
export function reportProblem(error) {
    if (error instanceof ApiError) {
        if (error.refusal === 'already_reported')
            return 'כבר דיווחת על המודעה הזו, והדיווח עדיין פתוח אצל המנהל.';
        if (error.status === 422)
            return 'הדיווח לא תקין: בחרו פרט אחד לפחות, והערה של עד 500 תווים.';
        if (error.status === 401)
            return 'צריך להתחבר כדי לדווח.';
    }
    return 'הדיווח לא נשלח. בדקו את החיבור ונסו שוב.';
}
/** What a write did, in words, at the foot of the screen. It leaves by itself after a while,
 *  unless it offers a retry of a failed write. */
export function NoticeBar({ notice, onDismiss }) {
    useEffect(() => {
        if (!notice || (notice.retry && !notice.undo))
            return;
        const timer = window.setTimeout(onDismiss, 7000);
        return () => window.clearTimeout(timer);
    }, [notice, onDismiss]);
    return (_jsx("div", { className: "notice-slot", role: "status", "aria-live": "polite", children: notice && (_jsxs("div", { className: "notice", children: [_jsx("span", { className: "notice-text", children: notice.text }), notice.retry && (_jsx("button", { type: "button", className: "notice-btn", onClick: notice.retry.run, children: notice.retry.label })), _jsx("button", { type: "button", className: "notice-btn is-quiet", onClick: onDismiss, children: "\u05E1\u05D2\u05D9\u05E8\u05D4" })] })) }));
}
