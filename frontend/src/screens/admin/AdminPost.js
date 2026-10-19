import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The admin's opened post (3.8 (c), "Post detail"), read fresh from the store: the photos, the text
// as stored, the record (state, reason, the flag, the failures), what a restore would leave now
// (#406), the city's ruling and its source (#214, #296), the model's answer beside the value users
// see field by field (#256), the reports, the corrections, the publications and the phones.
//
// Build steps 4 and 5, the writes, each sending the `version` the page showed (#391): restore (the
// reports first, then the record, #392), leave out (#286), remove from the list (#402), retry
// (#139), correct a field from a report (#395) and remove a correction (#394). A write answers the
// post's fresh detail; "changed" reloads it and says so: nothing is retried behind the admin's back.
import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api';
import { adminApi } from '../../admin/api';
import { MARK_WORDS, SOURCE_WORDS, valueWords } from '../../admin/words';
import { Carousel } from '../../components/Carousel';
import { israelTime, phoneLabel } from '../../format';
import { Announce, ReasonChip, useLoad, Waiting, when } from './ui';
import { ValueForm } from './ValueForm';
const STATUS_WORDS = { open: 'פתוח', left_out: 'הושאר בחוץ', restored: 'שוחזר' };
const REFUSALS = {
    changed: 'המודעה השתנתה מאז שנטענה, והדף נטען מחדש. בדקו ונסו שוב.',
    not_restorable: 'אין במודעה סימון או דיווח לשחזר.',
    no_open_report: 'אין דיווח פתוח להשאיר בחוץ.',
    not_applicable: 'המודעה כבר לא ברשימה של המשתמשים.',
    not_retryable: 'אין סיווג שנכשל לנסות שוב.',
    no_report: 'תיקון נעשה מתוך דיווח, ואין דיווח פתוח או מושאר בחוץ על המודעה.',
    not_in_force: 'התיקון כבר הוסר.',
    not_classified: 'המודעה עוד לא סווגה, אין מה לתקן.',
};
/** A field whose correction can make an active post's state wrong when removed (#394). */
const STATE_FIELDS = new Set(['post_nature', 'other_city']);
export function AdminPost({ id, names, groups, now }) {
    const [load, reload] = useLoad((signal) => adminApi.post(id, signal), id);
    return (_jsx(Waiting, { load: load, children: (post) => _jsx(PostDetail, { loaded: post, reload: reload, names: names, groups: groups, now: now }, post.id) }));
}
function PostDetail({ loaded, reload, names, groups, now, }) {
    const [post, setPost] = useState(loaded);
    const [busy, setBusy] = useState(false);
    const [notice, setNotice] = useState(null);
    const [correcting, setCorrecting] = useState(null);
    const [formError, setFormError] = useState(null);
    const announce = useRef(null);
    useEffect(() => setPost(loaded), [loaded]);
    /** Where the focus goes after a write (#408, #411): the message, or the field's "תיקון" button
     * the correction form was opened from. */
    const focusAfter = (target) => requestAnimationFrame(() => {
        const element = target === 'message'
            ? announce.current
            : document.querySelector(`button[aria-label="תיקון ${target}"]`);
        element?.focus();
    });
    const life = post.lifecycle;
    const resolvable = post.reports.filter((r) => r.status === 'open' || r.status === 'left_out');
    const open = post.reports.filter((r) => r.status === 'open');
    const restorable = life.flag !== null || resolvable.length > 0;
    const reportFor = resolvable[0] ?? null;
    const reported = [...new Set(resolvable.flatMap((r) => r.fields.map((f) => f.field)))];
    /** The post read again in place, so the notice of the write stays on the page. */
    const refresh = () => adminApi
        .post(post.id)
        .then(setPost)
        .catch(() => reload());
    /** A write: the answer is the post's fresh detail (or none: then it is read again); "changed"
     * reads it again and says so. */
    const run = (write, done, onError, focus = 'message') => {
        setBusy(true);
        setNotice(null);
        write()
            .then((fresh) => {
            if (fresh)
                setPost(fresh);
            else
                void refresh();
            setNotice({ kind: 'ok', text: done });
            setCorrecting(null);
            focusAfter(focus);
        })
            .catch((error) => {
            const text = problem(error);
            if (onError && error instanceof ApiError && error.status === 422)
                onError(text);
            else
                setNotice({ kind: 'error', text });
            if (error instanceof ApiError && error.refusal === 'changed')
                void refresh();
        })
            .finally(() => setBusy(false));
    };
    const restore = () => {
        const after = post.restore_preview;
        const question = after
            ? `לשחזר? המודעה תחזור ל"${after.reason_words ?? after.state_words}", והדיווחים יסומנו כמשוחזרים.`
            : 'לשחזר? הדיווחים יסומנו כמשוחזרים; המודעה עצמה נשארת כפי שהיא.';
        if (!window.confirm(question))
            return;
        run(async () => {
            const { results } = await adminApi.restore([{ listing_id: post.id, version: post.version }]);
            if (results[0]?.outcome === 'changed')
                throw new ApiError(409, { refusal: 'changed' });
            if (results[0]?.outcome === 'not_restorable')
                throw new ApiError(409, { refusal: 'not_restorable' });
            return null;
        }, 'המודעה שוחזרה. אם היא פעילה, היא תופיע ברשימה של המשתמשים בעוד כמה שניות.');
    };
    const leaveOut = () => {
        if (!window.confirm('להשאיר בחוץ? המודעה נשארת דחויה ונשמרת; אפשר לשחזר אותה גם אחר כך.'))
            return;
        run(() => adminApi.leaveOut(post.id, post.version), 'המודעה הושארה בחוץ.');
    };
    const removeCorrection = (correction) => {
        const warn = STATE_FIELDS.has(correction.field) && life.state === 'active'
            ? ' המודעה פעילה: מצבה לא יחושב מחדש, והמשתמשים יראו שוב את תשובת המודל.'
            : '';
        if (!window.confirm(`להסיר את התיקון של "${correction.label}"?${warn}`))
            return;
        run(() => adminApi.removeCorrection(correction.correction_id, post.version), 'התיקון הוסר.');
    };
    const correct = (field, label, value) => {
        if (!reportFor)
            return;
        setFormError(null);
        run(() => adminApi.correct(post.id, field, value, reportFor.report_id, post.version), 'התיקון נשמר. המודעה נשארת כפי שהיא עד שתשחזרו אותה.', setFormError, label);
    };
    const editing = correcting ? post.fields.find((f) => f.field === correcting) : undefined;
    return (_jsxs("div", { className: "apost", children: [_jsxs("div", { className: "apost-main", children: [_jsxs("section", { className: "apanel apost-state", "aria-label": "\u05DE\u05E6\u05D1 \u05D4\u05DE\u05D5\u05D3\u05E2\u05D4", children: [_jsxs("div", { className: "apost-statehead", children: [_jsx(ReasonChip, { row: life }), life.reason && _jsx("span", { className: "apost-statewords", children: life.state_words }), _jsx("a", { className: "apost-fb", href: post.permalink, target: "_blank", rel: "noopener noreferrer", children: "\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05D1\u05E4\u05D9\u05D9\u05E1\u05D1\u05D5\u05E7" })] }), _jsxs("dl", { className: "facts", children: [_jsx("dt", { children: "\u05E4\u05D5\u05E8\u05E1\u05DE\u05D4" }), _jsx("dd", { children: when(post.posted_at, now) }), _jsx("dt", { children: "\u05E4\u05E8\u05E1\u05D5\u05DD \u05D0\u05D7\u05E8\u05D5\u05DF" }), _jsx("dd", { children: when(life.last_published_at, now) }), life.flag && (_jsxs(_Fragment, { children: [_jsx("dt", { children: life.reason === 'misclassified' ? 'דווחה על ידי' : 'סומנה על ידי' }), _jsxs("dd", { children: [_jsx("bdi", { dir: "ltr", children: life.flag.by }), ", ", when(life.flag.at, now), life.flag.note && (_jsx("span", { className: "facts-note", dir: "auto", children: life.flag.note }))] })] })), life.failures > 0 && (_jsxs(_Fragment, { children: [_jsx("dt", { children: "\u05DB\u05E9\u05DC\u05D5\u05E0\u05D5\u05EA \u05E1\u05D9\u05D5\u05D5\u05D2" }), _jsxs("dd", { children: [life.failures, life.last_error ? `, האחרון: ${life.last_error}` : ''] })] })), post.city?.name && (_jsxs(_Fragment, { children: [_jsx("dt", { children: "\u05E2\u05D9\u05E8" }), _jsxs("dd", { children: [post.city.name, post.city.source && _jsx("span", { className: "facts-sub", children: SOURCE_WORDS[post.city.source] })] })] })), post.classified && (_jsxs(_Fragment, { children: [_jsx("dt", { children: "\u05E1\u05D5\u05D5\u05D2\u05D4" }), _jsxs("dd", { children: ["\u05D2\u05E8\u05E1\u05EA \u05D4\u05E0\u05D7\u05D9\u05D5\u05EA ", post.classified.prompt_version, ", ", israelTime(post.classified.classified_at)] })] }))] }), post.restore_preview && (_jsxs("p", { className: "apost-preview", children: ["\u05E9\u05D7\u05D6\u05D5\u05E8 \u05D9\u05D7\u05D6\u05D9\u05E8 \u05D0\u05D5\u05EA\u05D4 \u05DC: ", _jsx("strong", { children: post.restore_preview.reason_words ?? post.restore_preview.state_words }), post.restore_preview.reason && ` (${post.restore_preview.state_words})`] })), post.marks.map((mark) => (_jsx("p", { className: "apost-mark", children: MARK_WORDS[mark] }, mark))), _jsxs("div", { className: "apost-actions", children: [post.marks.includes('not_removed') && (_jsx("button", { type: "button", className: "mainbtn", disabled: busy, onClick: () => run(() => adminApi.applyReports(post.id, post.version), 'המודעה הוסרה מהרשימה של המשתמשים.'), children: "\u05D4\u05E1\u05E8\u05D4 \u05DE\u05D4\u05E8\u05E9\u05D9\u05DE\u05D4" })), restorable && (_jsx("button", { type: "button", className: "mainbtn", disabled: busy, onClick: restore, children: post.marks.includes('restore_unfinished') ? 'השלמת השחזור' : 'שחזור' })), open.length > 0 && life.state !== 'active' && (_jsx("button", { type: "button", className: "barbtn", disabled: busy, onClick: leaveOut, children: "\u05D4\u05E9\u05D0\u05E8\u05D4 \u05D1\u05D7\u05D5\u05E5" })), life.state === 'pending' && life.failures > 0 && (_jsx("button", { type: "button", className: "mainbtn", disabled: busy, onClick: () => run(() => adminApi.retry(post.id, post.version), 'הסיווג ינוסה שוב בהרצה הבאה של classify_pending.'), children: "\u05E0\u05D9\u05E1\u05D9\u05D5\u05DF \u05E1\u05D9\u05D5\u05D5\u05D2 \u05D7\u05D5\u05D6\u05E8" }))] }), _jsx(Announce, { ref: announce, message: notice && { ok: notice.kind === 'ok', text: notice.text } })] }), post.reports.length > 0 && (_jsxs("section", { className: "apanel", "aria-labelledby": "reports-head", children: [_jsx("h2", { id: "reports-head", children: "\u05D3\u05D9\u05D5\u05D5\u05D7\u05D9\u05DD \u05E2\u05DC \u05E1\u05D9\u05D5\u05D5\u05D2 \u05E9\u05D2\u05D5\u05D9" }), _jsx("ul", { className: "reports", children: post.reports.map((report) => (_jsxs("li", { className: "report", children: [_jsxs("p", { className: "report-head", children: [_jsx("bdi", { dir: "ltr", children: report.reporter }), ", ", when(report.reported_at, now), _jsx("span", { className: `report-status report-${report.status}`, children: STATUS_WORDS[report.status] })] }), _jsx("p", { className: "report-fields", children: report.fields.map((f) => f.label).join(', ') }), report.note && (_jsx("p", { className: "report-note", dir: "auto", children: report.note }))] }, report.report_id))) })] })), post.fields.length > 0 && (_jsxs("section", { className: "apanel", "aria-labelledby": "fields-head", children: [_jsx("h2", { id: "fields-head", children: "\u05D4\u05E1\u05D9\u05D5\u05D5\u05D2, \u05E9\u05D3\u05D4 \u05D0\u05D7\u05E8\u05D9 \u05E9\u05D3\u05D4" }), _jsx("p", { className: "apanel-lead", children: reportFor
                                    ? 'תשובת המודל כפי שנשמרה, ומה שהמשתמשים רואים אחרי התיקונים שלך. השדות שדווחו מסומנים; אפשר לתקן כל שדה.'
                                    : 'תשובת המודל כפי שנשמרה, ומה שהמשתמשים רואים אחרי התיקונים שלך. תיקון נעשה מתוך דיווח.' }), editing && (_jsx(ValueForm, { field: editing.field, label: editing.label, value: editing.seen, phones: post.phones.map((p) => p.phone), groups: groups, names: names, busy: busy, error: formError, onSubmit: (value) => correct(editing.field, editing.label, value), onCancel: () => {
                                    setCorrecting(null);
                                    setFormError(null);
                                    focusAfter(editing.label);
                                } }, editing.field)), _jsx("div", { className: "ftable-wrap", children: _jsxs("table", { className: "ftable", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { scope: "col", children: "\u05E9\u05D3\u05D4" }), _jsx("th", { scope: "col", children: "\u05D4\u05DE\u05D5\u05D3\u05DC" }), _jsx("th", { scope: "col", children: "\u05DE\u05D4 \u05E9\u05E8\u05D5\u05D0\u05D9\u05DD" }), reportFor && (_jsx("th", { scope: "col", children: _jsx("span", { className: "sr-only", children: "\u05EA\u05D9\u05E7\u05D5\u05DF" }) }))] }) }), _jsx("tbody", { children: post.fields.map((row) => (_jsxs("tr", { className: [row.corrected ? 'is-corrected' : '', reported.includes(row.field) ? 'is-reported' : '']
                                                    .join(' ')
                                                    .trim() || undefined, children: [_jsxs("th", { scope: "row", children: [row.label, reported.includes(row.field) && _jsx("span", { className: "tag tag-reported", children: "\u05D3\u05D5\u05D5\u05D7" })] }), _jsx("td", { dir: "auto", children: valueWords(row.model, names, row.field) }), _jsx("td", { dir: "auto", children: row.corrected ? (_jsxs(_Fragment, { children: [valueWords(row.seen, names, row.field), " ", _jsx("span", { className: "tag", children: "\u05EA\u05D5\u05E7\u05DF \u05D1\u05D9\u05D3" })] })) : (_jsx("span", { className: "same", children: "\u05DB\u05DE\u05D5 \u05D4\u05DE\u05D5\u05D3\u05DC" })) }), reportFor && (_jsx("td", { children: _jsx("button", { type: "button", className: "linkbtn", "aria-label": `תיקון ${row.label}`, disabled: busy, onClick: () => {
                                                                setFormError(null);
                                                                setCorrecting(row.field);
                                                            }, children: "\u05EA\u05D9\u05E7\u05D5\u05DF" }) }))] }, row.field))) })] }) })] })), post.corrections.length > 0 && (_jsxs("section", { className: "apanel", "aria-labelledby": "corr-head", children: [_jsx("h2", { id: "corr-head", children: "\u05EA\u05D9\u05E7\u05D5\u05E0\u05D9\u05DD" }), _jsx("ul", { className: "corrlist", children: post.corrections.map((c) => (_jsxs("li", { className: c.removed_at ? 'is-removed' : undefined, children: [_jsxs("span", { className: "corr-text", children: [_jsx("strong", { children: c.label }), ": ", valueWords(c.model_value, names, c.field), " \u2190", ' ', valueWords(c.corrected_value, names, c.field)] }), _jsx("span", { className: "facts-sub", children: c.removed_at ? `הוסר ${israelTime(c.removed_at)}` : `בתוקף מ־${israelTime(c.corrected_at)}` }), !c.removed_at && (_jsx("button", { type: "button", className: "linkbtn danger", "aria-label": `הסרת התיקון של ${c.label}`, disabled: busy, onClick: () => removeCorrection(c), children: "\u05D4\u05E1\u05E8\u05D4" }))] }, c.correction_id))) })] })), _jsxs("section", { className: "apanel", "aria-labelledby": "text-head", children: [_jsx("h2", { id: "text-head", children: "\u05D4\u05D8\u05E7\u05E1\u05D8" }), _jsx("p", { className: "apost-text", dir: "auto", children: post.text?.trim() || 'אין טקסט' })] })] }), _jsxs("aside", { className: "apost-side", children: [_jsx("div", { className: "apanel apost-photos", children: _jsx(Carousel, { photos: post.photos, videos: post.videos, variant: "open", eager: true }) }), post.phones.length > 0 && (_jsxs("section", { className: "apanel", "aria-labelledby": "phones-head", children: [_jsx("h2", { id: "phones-head", children: "\u05D8\u05DC\u05E4\u05D5\u05E0\u05D9\u05DD" }), _jsx("ul", { className: "plainlist", children: post.phones.map((p) => (_jsx("li", { dir: "auto", children: phoneLabel(p.phone, p.name) }, p.phone))) })] })), _jsxs("section", { className: "apanel", "aria-labelledby": "pubs-head", children: [_jsx("h2", { id: "pubs-head", children: post.publications.length === 1 ? 'פרסום אחד' : `${post.publications.length} פרסומים` }), _jsx("ul", { className: "plainlist", children: post.publications.map((p) => (_jsxs("li", { children: [israelTime(p.posted_at), p.id === post.id && _jsx("span", { className: "facts-sub", children: "\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05D4\u05D6\u05D5" })] }, p.id))) })] }), life.image_errors.length > 0 && _jsxs("p", { className: "apanel-lead", children: [life.image_errors.length, " \u05EA\u05DE\u05D5\u05E0\u05D5\u05EA \u05DC\u05D0 \u05D9\u05E8\u05D3\u05D5."] })] })] }));
}
function problem(error) {
    if (error instanceof ApiError && error.refusal === 'invalid_value') {
        // the server names the rule in plain Hebrew (#410)
        return typeof error.detail === 'string' && error.detail ? error.detail : 'הערך לא תקין.';
    }
    if (error instanceof ApiError && error.refusal)
        return REFUSALS[error.refusal] ?? 'הפעולה נדחתה.';
    return 'הפעולה לא נשמרה. בדקו את החיבור ונסו שוב.';
}
