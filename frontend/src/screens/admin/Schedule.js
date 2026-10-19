import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The schedule (Phase 5, PHASE_5.md points 8 and 11; DECISIONS.md #61, #471): the interval and the
// quiet hours, "run now", what runs and what ran. The site has no Apify key: it only writes the
// settings and the request; the scheduler reads them every few seconds and starts the runs.
import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api';
import { adminApi } from '../../admin/api';
import { israelTime, relativeTime } from '../../format';
import { Announce, useLoad, Waiting } from './ui';
const REFRESH_MS = 15000;
const REFUSALS = {
    changed: 'ההגדרות השתנו בינתיים. רעננו את הדף ונסו שוב.',
    invalid_schedule: 'המרווח הוא בין 5 ל-1440 דקות, והשעות בצורה שעה:דקות.',
    run_in_progress: 'ריצה כבר רצה עכשיו. אפשר לבקש עוד אחת כשהיא תסתיים.',
    already_asked: 'כבר ביקשת ריצה. המתזמן יתחיל אותה בתוך שניות.',
};
const STATUS = { running: 'רצה', succeeded: 'הצליחה', failed: 'נכשלה' };
const TRIGGER = { scheduled: 'מתוזמנת', manual: 'ידנית' };
function problem(error) {
    if (error instanceof ApiError && error.refusal)
        return REFUSALS[error.refusal] ?? 'הפעולה נדחתה.';
    return 'הפעולה לא נשמרה. בדקו את החיבור ונסו שוב.';
}
export function Schedule({ now }) {
    const [tick, setTick] = useState(0);
    const [load, reload] = useLoad((signal) => adminApi.schedule(signal), `schedule:${tick}`);
    useEffect(() => {
        const timer = window.setInterval(() => setTick((n) => n + 1), REFRESH_MS);
        return () => window.clearInterval(timer);
    }, []);
    return _jsx(Waiting, { load: load, children: (answer) => _jsx(Desk, { answer: answer, now: now, reload: reload }) });
}
function Desk({ answer, now, reload }) {
    const [interval, setIntervalMinutes] = useState(String(answer.interval_minutes));
    const [from, setFrom] = useState(answer.quiet_from);
    const [until, setUntil] = useState(answer.quiet_until);
    const [busy, setBusy] = useState(false);
    const [confirming, setConfirming] = useState(false);
    const [message, setMessage] = useState(null);
    const box = useRef(null);
    // A save elsewhere (another tab) brings the stored values back into the form.
    useEffect(() => {
        setIntervalMinutes(String(answer.interval_minutes));
        setFrom(answer.quiet_from);
        setUntil(answer.quiet_until);
    }, [answer.version]); // eslint-disable-line react-hooks/exhaustive-deps
    const changed = interval !== String(answer.interval_minutes) || from !== answer.quiet_from || until !== answer.quiet_until;
    const save = (event) => {
        event.preventDefault();
        setBusy(true);
        setMessage(null);
        adminApi
            .saveSchedule({ interval_minutes: Number(interval), quiet_from: from, quiet_until: until, version: answer.version })
            .then(() => {
            setMessage({ ok: true, text: 'נשמר. המתזמן עובד לפי ההגדרות החדשות מהבדיקה הבאה שלו, בתוך שניות.' });
            reload();
        })
            .catch((error) => setMessage({ ok: false, text: problem(error) }))
            .finally(() => setBusy(false));
    };
    const runNow = () => {
        setBusy(true);
        setMessage(null);
        adminApi
            .runNow()
            .then(() => {
            setMessage({ ok: true, text: 'הבקשה נשלחה. המתזמן יתחיל ריצה בתוך שניות.' });
            setConfirming(false);
            reload();
        })
            .catch((error) => {
            setMessage({ ok: false, text: problem(error) });
            setConfirming(false);
        })
            .finally(() => {
            setBusy(false);
            box.current?.focus();
        });
    };
    const blocked = answer.running !== null || answer.run_now_waiting;
    return (_jsxs(_Fragment, { children: [_jsx("p", { className: "adm-lead", children: "\u05D4\u05DE\u05EA\u05D6\u05DE\u05DF \u05DE\u05E8\u05D9\u05E5 \u05D0\u05D9\u05E1\u05D5\u05E3 \u05D5\u05D0\u05D7\u05E8\u05D9\u05D5 \u05E1\u05D9\u05D5\u05D5\u05D2 \u05E4\u05E2\u05DD \u05D1\u05DB\u05DC \u05DE\u05E8\u05D5\u05D5\u05D7, \u05DE\u05EA\u05D7\u05D9\u05DC\u05EA \u05D4\u05E8\u05D9\u05E6\u05D4 \u05D4\u05E7\u05D5\u05D3\u05DE\u05EA, \u05D5\u05DC\u05D0 \u05DE\u05EA\u05D7\u05D9\u05DC \u05E8\u05D9\u05E6\u05D4 \u05D1\u05E9\u05E2\u05D5\u05EA \u05D4\u05E9\u05E7\u05D8\u05D5\u05EA (\u05E9\u05E2\u05D5\u05DF \u05D9\u05E9\u05E8\u05D0\u05DC). \u05E8\u05D9\u05E6\u05D4 \u05D9\u05D3\u05E0\u05D9\u05EA \u05DE\u05D5\u05EA\u05E8\u05EA \u05D2\u05DD \u05D1\u05E9\u05E2\u05D5\u05EA \u05D4\u05E9\u05E7\u05D8\u05D5\u05EA." }), _jsxs("section", { className: "apanel", "aria-labelledby": "sched-now", children: [_jsx("h2", { id: "sched-now", children: "\u05E2\u05DB\u05E9\u05D9\u05D5" }), answer.running ? (_jsxs("p", { children: ["\u05E8\u05D9\u05E6\u05D4 ", TRIGGER[answer.running.trigger], " \u05E8\u05E6\u05D4 \u05E2\u05DB\u05E9\u05D9\u05D5, \u05D4\u05EA\u05D7\u05D9\u05DC\u05D4 ", relativeTime(answer.running.started_at, now), " (", israelTime(answer.running.started_at), ")."] })) : answer.next_run ? (_jsxs("p", { children: ["\u05D4\u05E8\u05D9\u05E6\u05D4 \u05D4\u05D1\u05D0\u05D4: ", israelTime(answer.next_run), answer.in_quiet_hours && ' (עכשיו שעות שקטות)', "."] })) : null, answer.run_now_waiting && _jsx("p", { children: "\u05E8\u05D9\u05E6\u05D4 \u05D9\u05D3\u05E0\u05D9\u05EA \u05DE\u05D7\u05DB\u05D4 \u05DC\u05DE\u05EA\u05D6\u05DE\u05DF \u05D5\u05EA\u05EA\u05D7\u05D9\u05DC \u05D1\u05EA\u05D5\u05DA \u05E9\u05E0\u05D9\u05D5\u05EA." }), confirming ? (_jsxs("div", { className: "issue-row", children: [_jsx("span", { children: "\u05E8\u05D9\u05E6\u05D4 \u05E2\u05D5\u05DC\u05D4 \u05DB\u05E9\u05E0\u05D9\u05D9\u05DD-\u05E9\u05DC\u05D5\u05E9\u05D4 \u05E1\u05E0\u05D8 (Apify \u05D5-OpenAI). \u05DC\u05D4\u05E8\u05D9\u05E5 \u05E2\u05DB\u05E9\u05D9\u05D5?" }), _jsx("button", { type: "button", className: "mainbtn", onClick: runNow, disabled: busy, children: "\u05DB\u05DF, \u05DC\u05D4\u05E8\u05D9\u05E5" }), _jsx("button", { type: "button", className: "linkbtn", onClick: () => setConfirming(false), disabled: busy, children: "\u05D1\u05D9\u05D8\u05D5\u05DC" })] })) : (_jsx("button", { type: "button", className: "barbtn", onClick: () => setConfirming(true), disabled: busy || blocked, children: "\u05D4\u05E8\u05E6\u05D4 \u05E2\u05DB\u05E9\u05D9\u05D5" }))] }), _jsxs("form", { className: "apanel", onSubmit: save, "aria-labelledby": "sched-settings", children: [_jsx("h2", { id: "sched-settings", children: "\u05D4\u05D2\u05D3\u05E8\u05D5\u05EA" }), !answer.stored && _jsx("p", { className: "facts-sub", children: "\u05D4\u05DE\u05EA\u05D6\u05DE\u05DF \u05E2\u05D5\u05D3 \u05DC\u05D0 \u05E9\u05DE\u05E8 \u05D4\u05D2\u05D3\u05E8\u05D5\u05EA: \u05D0\u05DC\u05D4 \u05D1\u05E8\u05D9\u05E8\u05D5\u05EA \u05D4\u05DE\u05D7\u05D3\u05DC \u05E9\u05DC\u05D5." }), _jsx("label", { htmlFor: "sched-interval", children: "\u05DE\u05E8\u05D5\u05D5\u05D7 \u05D1\u05D9\u05DF \u05E8\u05D9\u05E6\u05D5\u05EA (\u05D3\u05E7\u05D5\u05EA, 5 \u05E2\u05D3 1440)" }), _jsx("input", { id: "sched-interval", type: "number", inputMode: "numeric", min: 5, max: 1440, value: interval, onChange: (event) => setIntervalMinutes(event.target.value), required: true }), _jsx("label", { htmlFor: "sched-from", children: "\u05E9\u05E2\u05D5\u05EA \u05E9\u05E7\u05D8\u05D5\u05EA: \u05DE-" }), _jsx("input", { id: "sched-from", type: "time", value: from, onChange: (event) => setFrom(event.target.value), required: true }), _jsx("label", { htmlFor: "sched-until", children: "\u05E2\u05D3" }), _jsx("input", { id: "sched-until", type: "time", value: until, onChange: (event) => setUntil(event.target.value), required: true }), _jsx("p", { className: "facts-sub", children: "\u05D0\u05D5\u05EA\u05D4 \u05E9\u05E2\u05D4 \u05D1\u05E9\u05E0\u05D9 \u05D4\u05E9\u05D3\u05D5\u05EA: \u05D1\u05DC\u05D9 \u05E9\u05E2\u05D5\u05EA \u05E9\u05E7\u05D8\u05D5\u05EA." }), _jsx("button", { type: "submit", className: "mainbtn", disabled: busy || !changed, children: "\u05E9\u05DE\u05D9\u05E8\u05D4" }), answer.updated_at && (_jsxs("p", { className: "facts-sub", children: ["\u05E0\u05E9\u05DE\u05E8 \u05DC\u05D0\u05D7\u05E8\u05D5\u05E0\u05D4 ", israelTime(answer.updated_at), answer.updated_by && (_jsxs(_Fragment, { children: [' ', "\u05E2\u05DC \u05D9\u05D3\u05D9 ", _jsx("bdi", { dir: "ltr", children: answer.updated_by })] }))] }))] }), _jsx(Announce, { ref: box, message: message }), _jsx("h2", { className: "sched-runs", children: "\u05D4\u05E8\u05D9\u05E6\u05D5\u05EA \u05D4\u05D0\u05D7\u05E8\u05D5\u05E0\u05D5\u05EA" }), answer.runs.length === 0 ? (_jsx("p", { className: "adm-empty", children: "\u05E2\u05D5\u05D3 \u05DC\u05D0 \u05E0\u05E8\u05E9\u05DE\u05D4 \u05E8\u05D9\u05E6\u05D4." })) : (_jsx("div", { className: "ftable-wrap", children: _jsxs("table", { className: "ftable", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { scope: "col", children: "\u05D4\u05EA\u05D7\u05D9\u05DC\u05D4" }), _jsx("th", { scope: "col", children: "\u05E1\u05D5\u05D2" }), _jsx("th", { scope: "col", children: "\u05DE\u05E6\u05D1" }), _jsx("th", { scope: "col", children: "\u05E9\u05D5\u05E8\u05D5\u05EA" }), _jsx("th", { scope: "col", children: "\u05E2\u05DC\u05D5\u05EA Apify" })] }) }), _jsx("tbody", { children: answer.runs.map((run) => (_jsxs("tr", { children: [_jsx("th", { scope: "row", children: israelTime(run.started_at) }), _jsx("td", { children: TRIGGER[run.trigger] }), _jsxs("td", { children: [STATUS[run.status], run.failure_kind && (_jsx("span", { className: "facts-sub", dir: "ltr", children: run.failure_kind }))] }), _jsx("td", { children: run.rows_fetched ?? '—' }), _jsx("td", { children: run.cost_usd === null ? 'עוד לא סופית' : `$${run.cost_usd.toFixed(4)}` })] }, run.run_id))) })] }) }))] }));
}
