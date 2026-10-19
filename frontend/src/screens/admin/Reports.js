import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The reports grouped by field (#173, #254, #401) and the corrections (#256, #284), as read in build
// steps 1 and 2: a post stands under every field one of its reports names, with the two derived
// marks (3.8 (c)). Correct, restore and leave out are steps 4 and 5; until then a post opens its
// detail.
import { useState } from 'react';
import { adminApi } from '../../admin/api';
import { MARK_WORDS, valueWords } from '../../admin/words';
import { israelTime } from '../../format';
import { PostRow, useLoad, Waiting, when } from './ui';
const TABS = [
    { status: 'open', label: 'פתוחים' },
    { status: 'left_out', label: 'הושארו בחוץ' },
    { status: 'restored', label: 'שוחזרו' },
];
const EMPTY = {
    open: 'אין דיווחים פתוחים.',
    left_out: 'אין מודעות שהושארו בחוץ.',
    restored: 'עוד לא שוחזרה מודעה שדווחה.',
};
export function Reports({ now }) {
    const [status, setStatus] = useState('open');
    const [load] = useLoad((signal) => adminApi.reports(status, signal), status);
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: "\u05D3\u05D9\u05D5\u05D5\u05D7\u05D9\u05DD \u05E9\u05DC \u05DE\u05E9\u05EA\u05DE\u05E9\u05D9\u05DD \u05E2\u05DC \u05E1\u05D9\u05D5\u05D5\u05D2 \u05E9\u05D2\u05D5\u05D9, \u05DC\u05E4\u05D9 \u05D4\u05E9\u05D3\u05D4 \u05E9\u05D3\u05D5\u05D5\u05D7. \u05DE\u05D5\u05D3\u05E2\u05D4 \u05E9\u05D3\u05D5\u05D5\u05D7\u05D4 \u05E2\u05DC \u05DB\u05DE\u05D4 \u05E9\u05D3\u05D5\u05EA \u05DE\u05D5\u05E4\u05D9\u05E2\u05D4 \u05EA\u05D7\u05EA \u05DB\u05DC \u05D0\u05D7\u05D3 \u05DE\u05D4\u05DD." }), _jsx("div", { className: "tabs", role: "tablist", "aria-label": "\u05DE\u05E6\u05D1 \u05D4\u05D3\u05D9\u05D5\u05D5\u05D7", children: TABS.map((tab) => (_jsx("button", { type: "button", role: "tab", "aria-selected": status === tab.status, className: `tab${status === tab.status ? ' is-on' : ''}`, onClick: () => setStatus(tab.status), children: tab.label }, tab.status))) }), _jsx(Waiting, { load: load, children: (answer) => answer.groups.length === 0 ? (_jsx("p", { className: "adm-empty", children: EMPTY[status] })) : (_jsxs(_Fragment, { children: [_jsxs("p", { className: "adm-count", children: [answer.count === 1 ? 'דיווח אחד' : `${answer.count} דיווחים`, " \u05E2\u05DC", ' ', answer.posts === 1 ? 'מודעה אחת' : `${answer.posts} מודעות`] }), answer.groups.map((group) => (_jsxs("section", { className: "fieldgroup", "aria-labelledby": `g-${group.field}`, children: [_jsxs("h2", { id: `g-${group.field}`, children: [group.label, " ", _jsx("span", { className: "rcount", children: group.posts.length })] }), _jsx("ul", { className: "arows", children: group.posts.map((entry) => entry.post ? (_jsx(PostRow, { row: entry.post, now: now, children: _jsxs("div", { className: "arow-extra", children: [entry.marks.map((mark) => (_jsx("p", { className: "apost-mark", children: MARK_WORDS[mark] }, mark))), entry.reports.map((report) => (_jsxs("p", { className: "arow-report", children: [_jsx("bdi", { dir: "ltr", children: report.reporter }), ", ", when(report.reported_at, now), ":", ' ', report.fields.map((f) => f.label).join(', '), report.note && (_jsx("span", { className: "report-note", dir: "auto", children: report.note }))] }, report.report_id)))] }) }, entry.listing_id)) : (_jsx("li", { className: "arow arow-gone", children: "\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05DB\u05D1\u05E8 \u05DC\u05D0 \u05E9\u05DE\u05D5\u05E8\u05D4." }, entry.listing_id))) })] }, group.field)))] })) })] }));
}
export function Corrections({ names, now }) {
    const [inForce, setInForce] = useState(true);
    const [load] = useLoad((signal) => adminApi.corrections(inForce, signal), String(inForce));
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: "\u05EA\u05D9\u05E7\u05D5\u05DF \u05E9\u05DC\u05DA \u05D2\u05D5\u05D1\u05E8 \u05E2\u05DC \u05EA\u05E9\u05D5\u05D1\u05EA \u05D4\u05DE\u05D5\u05D3\u05DC \u05D1\u05DB\u05DC \u05DE\u05E7\u05D5\u05DD \u05E9\u05DE\u05E9\u05EA\u05DE\u05E9 \u05E7\u05D5\u05E8\u05D0 \u05D0\u05EA \u05D4\u05DE\u05D5\u05D3\u05E2\u05D4, \u05E2\u05D3 \u05E9\u05EA\u05E1\u05D9\u05E8 \u05D0\u05D5\u05EA\u05D5. \u05EA\u05E9\u05D5\u05D1\u05EA \u05D4\u05DE\u05D5\u05D3\u05DC \u05E0\u05E9\u05DE\u05E8\u05EA \u05DC\u05D9\u05D3\u05D5." }), _jsx("div", { className: "tabs", role: "tablist", "aria-label": "\u05EA\u05D9\u05E7\u05D5\u05E0\u05D9\u05DD", children: [true, false].map((value) => (_jsx("button", { type: "button", role: "tab", "aria-selected": inForce === value, className: `tab${inForce === value ? ' is-on' : ''}`, onClick: () => setInForce(value), children: value ? 'בתוקף' : 'הוסרו' }, String(value)))) }), _jsx(Waiting, { load: load, children: (answer) => answer.corrections.length === 0 ? (_jsx("p", { className: "adm-empty", children: inForce ? 'אין תיקונים בתוקף.' : 'לא הוסר אף תיקון.' })) : (_jsx("ul", { className: "arows", children: answer.corrections.map((c) => c.post ? (_jsx(PostRow, { row: c.post, now: now, children: _jsxs("p", { className: "arow-extra arow-correction", children: [_jsx("strong", { children: c.label }), ": ", valueWords(c.model_value, names, c.field), " \u2190", ' ', valueWords(c.corrected_value, names, c.field), _jsxs("span", { className: "facts-sub", children: [_jsx("bdi", { dir: "ltr", children: c.corrected_by }), ", ", israelTime(c.corrected_at), c.removed_at && `, הוסר ${israelTime(c.removed_at)}`] })] }) }, c.correction_id)) : (_jsxs("li", { className: "arow arow-gone", children: ["\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05DB\u05D1\u05E8 \u05DC\u05D0 \u05E9\u05DE\u05D5\u05E8\u05D4 (\u05E0\u05DE\u05D7\u05E7\u05D4 \u05D1\u05E9\u05DE\u05D9\u05E8\u05EA \u05D4\u05E0\u05EA\u05D5\u05E0\u05D9\u05DD). ", _jsx("strong", { children: c.label }), ":", ' ', valueWords(c.model_value, names, c.field), " \u2190 ", valueWords(c.corrected_value, names, c.field)] }, c.correction_id))) })) })] }));
}
