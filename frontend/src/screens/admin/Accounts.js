import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// Keys ("קודי הזמנה", the sign-up form's own word) and users (3.8 (c); build step 3): issue a key with a label and see it once (#266), cancel an
// unused one (#243); reset a user's password to a temporary one (#262, #263), disable and enable a
// user (#265). The admin's own row takes none of them (R8). Until 3.9 all of it lands in the site's
// dated copy (#400).
import { useState } from 'react';
import { ApiError } from '../../api';
import { adminApi } from '../../admin/api';
import { israelTime } from '../../format';
import { Announce, useLoad, Waiting } from './ui';
const REFUSALS = {
    label_empty: 'כתבו למי הקוד, כדי לזהות אותו ברשימה.',
    key_used: 'הקוד כבר שימש לפתיחת חשבון, ואי אפשר לבטל אותו.',
    unknown_key: 'הקוד לא נמצא. רעננו את הדף.',
    password_too_short: 'סיסמה זמנית צריכה לפחות 8 תווים.',
    admin_row: 'את הסיסמה שלך מחליפים בדף ההעדפות.',
    admin_cannot_be_disabled: 'אי אפשר להשבית את חשבון המנהל.',
    unknown_user: 'המשתמש לא נמצא. רעננו את הדף.',
    changed: 'הרשומה השתנתה בינתיים. רעננו את הדף ונסו שוב.',
};
function problem(error) {
    if (error instanceof ApiError && error.refusal)
        return REFUSALS[error.refusal] ?? 'הפעולה נדחתה.';
    if (error instanceof ApiError && error.status === 422)
        return 'הערך לא תקין.';
    return 'הפעולה לא נשמרה. בדקו את החיבור ונסו שוב.';
}
const KEY_STATE = { usable: 'פנוי', used: 'שומש', cancelled: 'בוטל' };
export function Keys({ onChanged }) {
    const [load, reload] = useLoad(() => adminApi.keys(), 'keys');
    const [label, setLabel] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [issued, setIssued] = useState(null);
    const [copied, setCopied] = useState(false);
    const issue = (event) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        adminApi
            .issueKey(label)
            .then((answer) => {
            setIssued({ label: answer.label, key: answer.key });
            setCopied(false);
            setLabel('');
            reload();
            onChanged();
        })
            .catch((e) => setError(problem(e)))
            .finally(() => setBusy(false));
    };
    const cancel = (key) => {
        if (!window.confirm(`לבטל את קוד ההזמנה "${key.label}"? קוד שבוטל לא חוזר.`))
            return;
        setError(null);
        adminApi
            .cancelKey(key.key_id)
            .then(() => {
            reload();
            onChanged();
        })
            .catch((e) => setError(problem(e)));
    };
    const copy = () => {
        if (!issued || !navigator.clipboard)
            return;
        navigator.clipboard
            .writeText(issued.key)
            .then(() => setCopied(true))
            .catch(() => setCopied(false));
    };
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: "\u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4 \u05E4\u05D5\u05EA\u05D7 \u05D7\u05E9\u05D1\u05D5\u05DF \u05D0\u05D7\u05D3. \u05DB\u05EA\u05D1\u05D5 \u05DC\u05DE\u05D9 \u05D4\u05D5\u05D0, \u05E6\u05E8\u05D5 \u05D0\u05D5\u05EA\u05D5 \u05D5\u05E9\u05DC\u05D7\u05D5 \u05D0\u05D5\u05EA\u05D5. \u05D4\u05E7\u05D5\u05D3 \u05DE\u05D5\u05E6\u05D2 \u05E4\u05E2\u05DD \u05D0\u05D7\u05EA \u05D1\u05DC\u05D1\u05D3: \u05D4\u05D0\u05EA\u05E8 \u05E9\u05D5\u05DE\u05E8 \u05E8\u05E7 \u05D8\u05D1\u05D9\u05E2\u05D4 \u05E9\u05DC\u05D5." }), _jsxs("form", { className: "apanel issue", onSubmit: issue, children: [_jsx("label", { htmlFor: "key-label", children: "\u05DC\u05DE\u05D9 \u05D4\u05E7\u05D5\u05D3" }), _jsxs("div", { className: "issue-row", children: [_jsx("input", { id: "key-label", value: label, onChange: (event) => setLabel(event.target.value), placeholder: "\u05DC\u05DE\u05E9\u05DC: \u05D3\u05E0\u05D4, \u05D4\u05E9\u05D5\u05EA\u05E4\u05D4 \u05E9\u05DC \u05E0\u05D5\u05E2\u05D4", maxLength: 80, autoComplete: "off" }), _jsx("button", { type: "submit", className: "mainbtn", disabled: busy || !label.trim(), children: "\u05D9\u05E6\u05D9\u05E8\u05EA \u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4" })] }), _jsx("p", { className: "formerror", role: "alert", children: error })] }), issued && (_jsxs("section", { className: "keyonce", "aria-labelledby": "key-once", children: [_jsxs("h2", { id: "key-once", children: ["\u05E7\u05D5\u05D3 \u05D4\u05D4\u05D6\u05DE\u05E0\u05D4 \u05E9\u05DC ", issued.label] }), _jsx("p", { children: "\u05D4\u05E2\u05EA\u05D9\u05E7\u05D5 \u05D0\u05D5\u05EA\u05D5 \u05E2\u05DB\u05E9\u05D9\u05D5. \u05D0\u05D7\u05E8\u05D9 \u05E9\u05EA\u05E2\u05D6\u05D1\u05D5 \u05D0\u05EA \u05D4\u05D3\u05E3 \u05D0\u05D9 \u05D0\u05E4\u05E9\u05E8 \u05DC\u05E8\u05D0\u05D5\u05EA \u05D0\u05D5\u05EA\u05D5 \u05E9\u05D5\u05D1." }), _jsxs("div", { className: "keyonce-row", children: [_jsx("code", { dir: "ltr", children: issued.key }), _jsx("button", { type: "button", className: "barbtn", onClick: copy, children: copied ? 'הועתק' : 'העתקה' })] }), _jsx("p", { className: "facts-sub", children: "\u05D4\u05D4\u05E8\u05E9\u05DE\u05D4: \u05D1\u05D3\u05E3 \"\u05D4\u05D9\u05E8\u05E9\u05DD\", \u05D1\u05E9\u05D3\u05D4 \"\u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4\"." })] })), _jsx(Waiting, { load: load, children: ({ keys }) => keys.length === 0 ? (_jsx("p", { className: "adm-empty", children: "\u05E2\u05D5\u05D3 \u05DC\u05D0 \u05E0\u05D5\u05E6\u05E8 \u05E7\u05D5\u05D3 \u05D4\u05D6\u05DE\u05E0\u05D4." })) : (_jsx("div", { className: "ftable-wrap", children: _jsxs("table", { className: "ftable", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { scope: "col", children: "\u05DC\u05DE\u05D9" }), _jsx("th", { scope: "col", children: "\u05DE\u05E6\u05D1" }), _jsx("th", { scope: "col", children: "\u05E0\u05D5\u05E6\u05E8" }), _jsx("th", { scope: "col", children: _jsx("span", { className: "sr-only", children: "\u05E4\u05E2\u05D5\u05DC\u05D4" }) })] }) }), _jsx("tbody", { children: keys.map((key) => (_jsxs("tr", { children: [_jsx("th", { scope: "row", children: key.label }), _jsxs("td", { children: [_jsx("span", { className: `kstate kstate-${key.state}`, children: KEY_STATE[key.state] }), key.used_by && (_jsxs("span", { className: "facts-sub", children: [_jsx("bdi", { dir: "ltr", children: key.used_by }), key.used_at && `, ${israelTime(key.used_at)}`] })), key.cancelled_at && _jsx("span", { className: "facts-sub", children: israelTime(key.cancelled_at) })] }), _jsx("td", { children: israelTime(key.created_at) }), _jsx("td", { children: key.state === 'usable' && (_jsx("button", { type: "button", className: "linkbtn danger", "aria-label": `ביטול קוד ההזמנה של ${key.label}`, onClick: () => cancel(key), children: "\u05D1\u05D9\u05D8\u05D5\u05DC" })) })] }, key.key_id))) })] }) })) })] }));
}
export function Users({ onChanged }) {
    const [load, reload] = useLoad(() => adminApi.users(), 'users');
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState(null);
    const [resetting, setResetting] = useState(null);
    const run = (action, done) => {
        setError(null);
        setNotice(null);
        action()
            .then(() => {
            setNotice(done);
            reload();
            onChanged();
        })
            .catch((e) => setError(problem(e)));
    };
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: "\u05DE\u05E9\u05EA\u05DE\u05E9\u05D9\u05DD \u05DC\u05D0 \u05E0\u05DE\u05D7\u05E7\u05D9\u05DD. \u05D4\u05E9\u05D1\u05EA\u05D4 \u05DE\u05E0\u05EA\u05E7\u05EA \u05D0\u05EA \u05D4\u05D7\u05E9\u05D1\u05D5\u05DF \u05DE\u05DB\u05DC \u05D4\u05DE\u05DB\u05E9\u05D9\u05E8\u05D9\u05DD \u05D5\u05E9\u05D5\u05DE\u05E8\u05EA \u05D0\u05EA \u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA. \u05D0\u05D9\u05E4\u05D5\u05E1 \u05E0\u05D5\u05EA\u05DF \u05E1\u05D9\u05E1\u05DE\u05D4 \u05D6\u05DE\u05E0\u05D9\u05EA, \u05E9\u05EA\u05D5\u05D7\u05DC\u05E3 \u05D1\u05DB\u05E0\u05D9\u05E1\u05D4 \u05D4\u05D1\u05D0\u05D4." }), _jsx(Announce, { message: error ? { ok: false, text: error } : notice ? { ok: true, text: notice } : null }), _jsx(Waiting, { load: load, children: ({ users }) => (_jsx("ul", { className: "ulist", children: users.map((user) => (_jsxs("li", { className: `urow${user.disabled_at ? ' is-disabled' : ''}`, children: [_jsxs("div", { className: "urow-who", children: [_jsx("span", { className: "urow-name", dir: "ltr", children: user.username }), user.is_admin && _jsx("span", { className: "tag", children: "\u05DE\u05E0\u05D4\u05DC" }), user.disabled_at && _jsx("span", { className: "kstate kstate-cancelled", children: "\u05DE\u05D5\u05E9\u05D1\u05EA" }), user.must_change_password && _jsx("span", { className: "kstate kstate-used", children: "\u05E6\u05E8\u05D9\u05DA \u05DC\u05D4\u05D7\u05DC\u05D9\u05E3 \u05E1\u05D9\u05E1\u05DE\u05D4" })] }), _jsxs("p", { className: "urow-facts", children: ["\u05D4\u05D7\u05E9\u05D1\u05D5\u05DF \u05E0\u05D5\u05E6\u05E8 ", israelTime(user.created_at), user.key_label && `, בקוד ההזמנה "${user.key_label}"`, user.failed_sign_ins > 0 && `, ${user.failed_sign_ins} כניסות שנכשלו ברצף`] }), !user.is_admin && (_jsxs("div", { className: "urow-actions", children: [_jsx("button", { type: "button", className: "barbtn", "aria-expanded": resetting === user.username, "aria-label": `איפוס סיסמה ל־${user.username}`, onClick: () => setResetting(resetting === user.username ? null : user.username), children: "\u05D0\u05D9\u05E4\u05D5\u05E1 \u05E1\u05D9\u05E1\u05DE\u05D4" }), user.disabled_at ? (_jsx("button", { type: "button", className: "barbtn", "aria-label": `הפעלה של ${user.username}`, onClick: () => run(() => adminApi.enable(user.username), `החשבון של ${user.username} פעיל שוב.`), children: "\u05D4\u05E4\u05E2\u05DC\u05D4" })) : (_jsx("button", { type: "button", className: "barbtn danger", "aria-label": `השבתה של ${user.username}`, onClick: () => window.confirm(`להשבית את ${user.username}? כל החיבורים של החשבון יתנתקו.`) &&
                                            run(() => adminApi.disable(user.username), `החשבון של ${user.username} הושבת.`), children: "\u05D4\u05E9\u05D1\u05EA\u05D4" }))] })), resetting === user.username && (_jsx(ResetForm, { username: user.username, onCancel: () => setResetting(null), onDone: () => {
                                    setResetting(null);
                                    setNotice(`הסיסמה של ${user.username} אופסה. מסרו את הסיסמה הזמנית; בכניסה הבאה תתבקש בחירת סיסמה חדשה.`);
                                    reload();
                                } }))] }, user.username))) })) })] }));
}
function ResetForm({ username, onCancel, onDone }) {
    const [password, setPassword] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const submit = (event) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        adminApi
            .resetPassword(username, password)
            .then(onDone)
            .catch((e) => setError(problem(e)))
            .finally(() => setBusy(false));
    };
    const id = `temp-${username}`;
    return (_jsxs("form", { className: "resetform", onSubmit: submit, children: [_jsxs("label", { htmlFor: id, children: ["\u05E1\u05D9\u05E1\u05DE\u05D4 \u05D6\u05DE\u05E0\u05D9\u05EA \u05DC\u05BE", username] }), _jsxs("div", { className: "issue-row", children: [_jsx("input", { id: id, type: "text", dir: "ltr", value: password, onChange: (event) => setPassword(event.target.value), minLength: 8, autoComplete: "off" }), _jsx("button", { type: "submit", className: "mainbtn", disabled: busy || password.length < 8, children: "\u05D0\u05D9\u05E4\u05D5\u05E1" }), _jsx("button", { type: "button", className: "linkbtn", onClick: onCancel, children: "\u05D1\u05D9\u05D8\u05D5\u05DC" })] }), _jsx("p", { className: "tfield-hint", children: "\u05DC\u05E4\u05D7\u05D5\u05EA 8 \u05EA\u05D5\u05D5\u05D9\u05DD. \u05DB\u05DC \u05D4\u05D7\u05D9\u05D1\u05D5\u05E8\u05D9\u05DD \u05E9\u05DC \u05D4\u05D7\u05E9\u05D1\u05D5\u05DF \u05D9\u05EA\u05E0\u05EA\u05E7\u05D5." }), _jsx("p", { className: "formerror", role: "alert", children: error })] }));
}
