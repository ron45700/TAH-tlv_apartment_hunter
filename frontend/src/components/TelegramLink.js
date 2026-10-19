import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// Linking Telegram from the preferences page (PHASE_4.md 4.4, point 5 A; DECISIONS.md #453). The
// page asks the server for a one-time code and shows it once: as a link that opens the bot with the
// code (t.me), and by itself to type to the bot. The code is valid for 15 minutes; while it is shown
// the page asks every few seconds whether the bot has linked the account. Unlinking stops the alerts.
// The link is a plain navigation the user makes: the page itself fetches nothing but the site.
import { useEffect, useState } from 'react';
import { ApiError, api } from '../api';
import { israelTime } from '../format';
const POLL_MS = 4000;
function viewOf(found) {
    return found.linked && found.linked_at ? { state: 'linked', since: found.linked_at } : { state: 'unlinked' };
}
export function TelegramLink() {
    const [view, setView] = useState({ state: 'loading' });
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState(null);
    useEffect(() => {
        api
            .telegram()
            .then((found) => setView(viewOf(found)))
            .catch(() => setView({ state: 'failed' }));
    }, []);
    // While a code is shown: has the bot linked the account yet? Stops when the code expires.
    useEffect(() => {
        if (view.state !== 'code')
            return;
        const expires = new Date(view.code.expires_at).getTime();
        const timer = window.setInterval(() => {
            if (Date.now() > expires) {
                window.clearInterval(timer);
                setView({ state: 'unlinked' });
                setProblem('הקוד פג. צרו קוד חדש.');
                return;
            }
            api
                .telegram()
                .then((found) => {
                if (found.linked)
                    setView(viewOf(found));
            })
                .catch(() => undefined);
        }, POLL_MS);
        return () => window.clearInterval(timer);
    }, [view]);
    const makeCode = async () => {
        setBusy(true);
        setProblem(null);
        try {
            setView({ state: 'code', code: await api.telegramLink() });
        }
        catch (error) {
            setProblem(error instanceof ApiError && error.status === 401 ? 'יש להתחבר מחדש.' : 'הקוד לא נוצר. נסו שוב.');
        }
        finally {
            setBusy(false);
        }
    };
    const unlink = async () => {
        setBusy(true);
        setProblem(null);
        try {
            setView(viewOf(await api.telegramUnlink()));
        }
        catch {
            setProblem('הקישור לא בוטל. נסו שוב.');
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("section", { className: "pcard telegram", "aria-labelledby": "telegram-title", children: [_jsx("h2", { id: "telegram-title", children: "\u05D4\u05EA\u05E8\u05D0\u05D5\u05EA \u05D1\u05D8\u05DC\u05D2\u05E8\u05DD" }), view.state === 'loading' && _jsx("p", { className: "pline", children: "\u05D8\u05D5\u05E2\u05DF\u2026" }), view.state === 'failed' && _jsx("p", { className: "pline", children: "\u05DE\u05E6\u05D1 \u05D4\u05E7\u05D9\u05E9\u05D5\u05E8 \u05DC\u05D0 \u05E0\u05D8\u05E2\u05DF." }), view.state === 'linked' && (_jsxs(_Fragment, { children: [_jsxs("p", { className: "pline", children: ["\u05DE\u05E7\u05D5\u05E9\u05E8 \u05DE\u05D0\u05D6 ", israelTime(view.since), ". \u05D4\u05EA\u05E8\u05D0\u05D4 \u05E2\u05DC \u05DB\u05DC \u05DE\u05D5\u05D3\u05E2\u05D4 \u05D7\u05D3\u05E9\u05D4 \u05E9\u05DE\u05EA\u05D0\u05D9\u05DE\u05D4 \u05DC\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05EA\u05D2\u05D9\u05E2 \u05DC\u05D8\u05DC\u05D2\u05E8\u05DD."] }), _jsx("button", { type: "button", className: "barbtn", disabled: busy, onClick: unlink, children: "\u05D1\u05D9\u05D8\u05D5\u05DC \u05D4\u05E7\u05D9\u05E9\u05D5\u05E8" })] })), view.state === 'unlinked' && (_jsxs(_Fragment, { children: [_jsx("p", { className: "pline", children: "\u05E7\u05D1\u05DC\u05D5 \u05D4\u05EA\u05E8\u05D0\u05D4 \u05D1\u05D8\u05DC\u05D2\u05E8\u05DD \u05E2\u05DC \u05DB\u05DC \u05DE\u05D5\u05D3\u05E2\u05D4 \u05D7\u05D3\u05E9\u05D4 \u05E9\u05DE\u05EA\u05D0\u05D9\u05DE\u05D4 \u05DC\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA." }), _jsx("button", { type: "button", className: "mainbtn", disabled: busy, onClick: makeCode, children: "\u05E7\u05D9\u05E9\u05D5\u05E8 \u05DC\u05D8\u05DC\u05D2\u05E8\u05DD" })] })), view.state === 'code' && (_jsxs(_Fragment, { children: [_jsx("a", { className: "mainbtn tg-open", href: view.code.link, target: "_blank", rel: "noopener noreferrer", children: "\u05E4\u05EA\u05D9\u05D7\u05EA \u05D4\u05D1\u05D5\u05D8 \u05D1\u05D8\u05DC\u05D2\u05E8\u05DD" }), _jsx("p", { className: "pline", children: "\u05D1\u05D8\u05DC\u05D2\u05E8\u05DD \u05DC\u05D5\u05D7\u05E6\u05D9\u05DD \"\u05D4\u05EA\u05D7\u05DC\" (Start). \u05D0\u05E4\u05E9\u05E8 \u05D2\u05DD \u05DC\u05E9\u05DC\u05D5\u05D7 \u05DC\u05D1\u05D5\u05D8 \u05D0\u05EA \u05D4\u05E7\u05D5\u05D3:" }), _jsx("p", { className: "tg-code", dir: "ltr", children: _jsx("code", { children: view.code.code }) }), _jsx("p", { className: "pline", role: "status", children: "\u05D4\u05E7\u05D5\u05D3 \u05D1\u05EA\u05D5\u05E7\u05E3 15 \u05D3\u05E7\u05D5\u05EA. \u05D4\u05D3\u05E3 \u05D9\u05EA\u05E2\u05D3\u05DB\u05DF \u05DB\u05E9\u05D4\u05E7\u05D9\u05E9\u05D5\u05E8 \u05D9\u05D5\u05E9\u05DC\u05DD." })] })), problem && (_jsx("p", { className: "savestate is-failed", role: "alert", children: problem }))] }));
}
