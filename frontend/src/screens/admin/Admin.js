import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { adminApi } from '../../admin/api';
import { REASON_FAMILY, REASON_NAMES, REASON_ORDER } from '../../admin/words';
import { ADMIN_PAGES, adminPath } from '../../route';
import { Keys, Users } from './Accounts';
import { AdminPost } from './AdminPost';
import { PostRows } from './PostRows';
import { Corrections, Reports } from './Reports';
import { Schedule } from './Schedule';
import { Link, useLoad } from './ui';
const TITLES = {
    overview: 'סקירה',
    rejected: 'נדחו',
    pending: 'ממתינות לסיווג',
    flags: 'סומנו כמשקרות',
    reports: 'דיווחים',
    corrections: 'תיקונים',
    archive: 'ארכיון',
    keys: 'קודי הזמנה',
    users: 'משתמשים',
    schedule: 'תזמון',
};
function railCount(page, summary) {
    if (!summary)
        return null;
    const counts = {
        rejected: summary.rejected,
        pending: summary.pending,
        flags: summary.flag_actions,
        reports: summary.open_reports,
        corrections: summary.corrections,
        archive: summary.archive,
        keys: summary.usable_keys,
        users: summary.users,
    };
    return counts[page] ?? null;
}
export function Admin({ user, page, id, names, groups, now }) {
    if (user === undefined) {
        return (_jsx("main", { className: "shell adm-solo", children: _jsx("p", { className: "adm-empty", children: "\u05D8\u05D5\u05E2\u05DF\u2026" }) }));
    }
    if (!user?.is_admin) {
        return (_jsx("main", { className: "shell adm-solo", children: _jsxs("p", { className: "adm-empty", children: ["\u05D4\u05D3\u05E4\u05D9\u05DD \u05D4\u05D0\u05DC\u05D4 \u05DC\u05DE\u05E0\u05D4\u05DC \u05D1\u05DC\u05D1\u05D3. ", _jsx(Link, { to: "/", children: "\u05DC\u05E8\u05E9\u05D9\u05DE\u05EA \u05D4\u05DE\u05D5\u05D3\u05E2\u05D5\u05EA" })] }) }));
    }
    return _jsx(Desk, { page: page, id: id, names: names, groups: groups, now: now });
}
function Desk({ page, id, names, groups, now }) {
    const [summary, recount] = useLoad((signal) => adminApi.summary(signal), `${page}:${id ?? ''}`);
    const counts = summary.state === 'ready' ? summary.data : null;
    const current = page === 'post' ? 'overview' : page;
    return (_jsxs("div", { className: "shell adm", children: [_jsx("nav", { className: "rail", "aria-label": "\u05D3\u05E4\u05D9 \u05D4\u05DE\u05E0\u05D4\u05DC", children: _jsx("ul", { children: ADMIN_PAGES.map((name) => {
                        const count = railCount(name, counts);
                        const on = page !== 'post' && name === current;
                        return (_jsx("li", { children: _jsxs(Link, { to: adminPath(name), className: `rail-link${on ? ' is-on' : ''}`, current: on, children: [_jsx("span", { children: TITLES[name] }), count !== null && _jsx("span", { className: "rail-count", children: count })] }) }, name));
                    }) }) }), _jsx("main", { className: "adm-main", children: page === 'post' && id ? (_jsxs(_Fragment, { children: [_jsx(Head, { title: "\u05DE\u05D5\u05D3\u05E2\u05D4", children: _jsx("button", { type: "button", className: "linkbtn", onClick: () => history.back(), children: "\u05D7\u05D6\u05E8\u05D4" }) }), _jsx(AdminPost, { id: id, names: names, groups: groups, now: now })] })) : (_jsxs(_Fragment, { children: [_jsx(Head, { title: TITLES[current] }), current === 'overview' && _jsx(Overview, { summary: counts }), (current === 'rejected' || current === 'pending' || current === 'archive' || current === 'flags') && (_jsx(PostRows, { list: current, now: now, onChanged: recount }, current)), current === 'reports' && _jsx(Reports, { now: now }), current === 'corrections' && _jsx(Corrections, { names: names, now: now }), current === 'keys' && _jsx(Keys, { onChanged: recount }), current === 'users' && _jsx(Users, { onChanged: recount }), current === 'schedule' && _jsx(Schedule, { now: now })] })) })] }));
}
function Head({ title, children }) {
    return (_jsxs("div", { className: "adm-head", children: [_jsx("h1", { children: title }), children] }));
}
/** One line per list with its count (3.8 (c), "Overview"). */
function Overview({ summary }) {
    if (!summary)
        return _jsx("p", { className: "adm-empty", children: "\u05D8\u05D5\u05E2\u05DF\u2026" });
    const lines = [
        { to: 'reports', text: `${summary.not_removed} דיווחים שהמודעה שלהם עדיין ברשימה`, alert: summary.not_removed },
        { to: 'reports', text: `${summary.restore_unfinished} שחזורים שלא הושלמו`, alert: summary.restore_unfinished },
        {
            to: 'rejected',
            text: `${summary.rejected} מודעות נדחו`,
            detail: (_jsx("span", { className: "ov-reasons", children: REASON_ORDER.filter((name) => summary.rejected_by_reason[name]).map((name) => (_jsxs("span", { className: `rchip rchip-${REASON_FAMILY[name]}`, children: [REASON_NAMES[name], " ", summary.rejected_by_reason[name]] }, name))) })),
        },
        {
            to: 'pending',
            text: `${summary.pending} ממתינות לסיווג`,
            detail: summary.pending_failed > 0 ? `${summary.pending_failed} מהן נכשלו בסיווג` : undefined,
        },
        {
            to: 'flags',
            text: `${summary.flag_actions} סימונים כמשקרות`,
            detail: summary.flagged_posts ? `על ${summary.flagged_posts} פרסומים` : undefined,
        },
        { to: 'reports', text: `${summary.open_reports} דיווחים פתוחים על סיווג שגוי` },
        { to: 'corrections', text: `${summary.corrections} תיקונים בתוקף` },
        { to: 'archive', text: `${summary.archive} מודעות בארכיון` },
        { to: 'keys', text: `${summary.usable_keys} קודי הזמנה פנויים` },
        { to: 'users', text: `${summary.users} משתמשים` },
    ];
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: "\u05E2\u05D3 \u05E9\u05D4\u05D0\u05EA\u05E8 \u05D9\u05D5\u05D2\u05E9 \u05DE\u05D4\u05DE\u05D0\u05D2\u05E8 \u05E2\u05E6\u05DE\u05D5 (\u05E9\u05DC\u05D1 3.9), \u05DB\u05DC \u05DE\u05D4 \u05E9\u05E0\u05E2\u05E9\u05D4 \u05DB\u05D0\u05DF \u05E0\u05E9\u05DE\u05E8 \u05E8\u05E7 \u05D1\u05E2\u05D5\u05EA\u05E7 \u05D4\u05DE\u05EA\u05D5\u05D0\u05E8\u05DA \u05E9\u05D4\u05D0\u05EA\u05E8 \u05DE\u05D2\u05D9\u05E9, \u05D5\u05E0\u05E2\u05DC\u05DD \u05D1\u05E2\u05D5\u05EA\u05E7 \u05D4\u05D1\u05D0." }), _jsx("ul", { className: "ov", children: lines
                    .filter((line) => line.alert === undefined || line.alert > 0)
                    .map((line) => (_jsxs("li", { className: line.alert ? 'is-alert' : undefined, children: [_jsx(Link, { to: adminPath(line.to), className: "ov-link", children: line.text }), line.detail && _jsx("span", { className: "ov-detail", children: line.detail })] }, line.text))) })] }));
}
