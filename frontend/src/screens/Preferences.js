import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The preferences page (PHASE_3.md 3.7 (e)(iii)): the only place preferences are saved (#335). At the
// top the profile's one sublet switch (#317); two tabs, "חדר בדירת שותפים" and "דירה שלמה" (#339),
// each with its on/off switch and "copy from the other option" (#272: every value but on/off; never
// the sqm range into the room option; the sublet switch is not copied). Sections as cards; each
// range two number boxes with a slider and "נקה" for "don't care"; each category its level. A
// summary and the live count "with these preferences: N posts" (#330 point 24); the save sticky at
// the right on a desktop, at the bottom on a phone; leaving with unsaved changes asks first.
import { useEffect, useRef, useState } from 'react';
import { ApiError, api } from '../api';
import { OPTIONS, OPTION_NAMES, barOf, copyFromOther, optionSummary, other, refusalWords, sameBar, withOption, } from '../bar';
import { MUST_HIDES, Switch } from '../components/controls';
import { TelegramLink } from '../components/TelegramLink';
import { AreasField, EntryField, FeaturesField, PriceField, RangeField, WomenField } from '../components/fields';
import { navigate, setLeaveGuard } from '../route';
export function Preferences({ saved, onSaved, groups, names }) {
    const [draft, setDraft] = useState(saved);
    const [tab, setTab] = useState('room');
    const [count, setCount] = useState(null);
    const [countProblem, setCountProblem] = useState(null);
    const [saving, setSaving] = useState({ state: 'idle' });
    const dirty = !sameBar(draft, saved);
    const dirtyRef = useRef(dirty);
    dirtyRef.current = dirty;
    useEffect(() => {
        setLeaveGuard(() => dirtyRef.current);
        return () => setLeaveGuard(null);
    }, []);
    // The live count follows the draft, a moment after the last change.
    useEffect(() => {
        const controller = new AbortController();
        const timer = window.setTimeout(() => {
            api
                .cards(draft, 0, controller.signal) // the count alone (#378)
                .then((list) => {
                setCount(list.count);
                setCountProblem(null);
            })
                .catch((error) => {
                if (error instanceof DOMException)
                    return;
                setCount(null);
                setCountProblem(error instanceof ApiError && error.status === 422 ? refusalWords(error.detail) : 'הספירה לא נטענה.');
            });
        }, 350);
        return () => {
            window.clearTimeout(timer);
            controller.abort();
        };
    }, [draft]);
    const edit = (next) => {
        setDraft(next);
        setSaving((current) => (current.state === 'saving' ? current : { state: 'idle' }));
    };
    const change = (name) => (values) => edit(withOption(draft, name, values));
    const save = async () => {
        setSaving({ state: 'saving' });
        try {
            const next = barOf(await api.saveProfile(draft));
            onSaved(next);
            setDraft(next);
            setSaving({ state: 'saved' });
        }
        catch (error) {
            const words = error instanceof ApiError && error.status === 422
                ? refusalWords(error.detail).replace('הסינון', 'ההעדפות')
                : 'לא נשמר. נסו שוב.';
            setSaving({ state: 'failed', words });
        }
    };
    const option = draft[tab];
    const saveRow = (_jsxs("div", { className: "saverow", children: [_jsx("p", { className: "livecount", "aria-live": "polite", children: countProblem ?? (count === null ? 'סופר מודעות…' : `עם ההעדפות האלה: ${count} מודעות`) }), _jsx("button", { type: "button", className: "mainbtn", disabled: !dirty || saving.state === 'saving', onClick: save, children: saving.state === 'saving' ? 'שומר…' : 'שמירת ההעדפות' }), _jsxs("p", { className: saving.state === 'failed' ? 'savestate is-failed' : 'savestate', role: "status", children: [saving.state === 'saved' && !dirty && 'ההעדפות נשמרו.', saving.state === 'failed' && saving.words, saving.state === 'idle' && dirty && 'יש שינויים שלא נשמרו.'] })] }));
    return (_jsxs("main", { className: "shell prefs", children: [_jsxs("header", { className: "prefs-head", children: [_jsx("h1", { children: "\u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05E9\u05DC\u05D9" }), _jsx("p", { children: "\u05D4\u05E1\u05D9\u05E0\u05D5\u05DF \u05D1\u05E2\u05DE\u05D5\u05D3 \u05D4\u05E8\u05D0\u05E9\u05D9 \u05DE\u05EA\u05D7\u05D9\u05DC \u05DE\u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05D4\u05D0\u05DC\u05D4. \u05E9\u05D9\u05E0\u05D5\u05D9 \u05D1\u05E1\u05D9\u05E0\u05D5\u05DF \u05E9\u05DD \u05DC\u05D0 \u05DE\u05E9\u05E0\u05D4 \u05D0\u05D5\u05EA\u05DF: \u05E9\u05D5\u05DE\u05E8\u05D9\u05DD \u05E8\u05E7 \u05DB\u05D0\u05DF." })] }), _jsxs("div", { className: "prefs-layout", children: [_jsxs("aside", { className: "prefs-side", "aria-label": "\u05E1\u05D9\u05DB\u05D5\u05DD \u05D5\u05E9\u05DE\u05D9\u05E8\u05D4", children: [_jsxs("div", { className: "pcard summary", children: [_jsx("h2", { children: "\u05E1\u05D9\u05DB\u05D5\u05DD" }), OPTIONS.map((name) => {
                                        const lines = optionSummary(draft[name], names);
                                        return (_jsxs("div", { className: "sum-kind", children: [_jsxs("h3", { children: [OPTION_NAMES[name], !draft[name].enabled && _jsx("span", { className: "off-tag", children: "\u05DB\u05D1\u05D5\u05D9" })] }), draft[name].enabled && (_jsx("ul", { children: lines.length ? lines.map((line) => _jsx("li", { children: line }, line)) : _jsx("li", { className: "none", children: "\u05D1\u05DC\u05D9 \u05E1\u05D9\u05E0\u05D5\u05DF" }) }))] }, name));
                                    }), _jsx("p", { className: "sum-sublet", children: draft.include_sublets ? 'כולל סאבלטים' : 'בלי סאבלטים' }), _jsx("div", { className: "side-save", children: saveRow })] }), _jsx(TelegramLink, {}), _jsx("p", { className: "side-link", children: _jsx("a", { href: "/password", onClick: (event) => {
                                        event.preventDefault();
                                        navigate('/password');
                                    }, children: "\u05E9\u05D9\u05E0\u05D5\u05D9 \u05E1\u05D9\u05E1\u05DE\u05D4" }) })] }), _jsxs("div", { className: "prefs-main", children: [_jsxs("section", { className: "pcard", children: [_jsx(Switch, { label: "\u05D2\u05DD \u05E1\u05D0\u05D1\u05DC\u05D8", checked: draft.include_sublets, onChange: (include_sublets) => edit({ ...draft, include_sublets }), describedBy: "sublet-line" }), _jsx("p", { className: "pline", id: "sublet-line", children: "\u05E1\u05D0\u05D1\u05DC\u05D8\u05D9\u05DD \u05DE\u05D5\u05E6\u05D2\u05D9\u05DD \u05D1\u05D7\u05D9\u05E4\u05D5\u05E9\u05D9\u05DD \u05E9\u05D4\u05E4\u05E2\u05DC\u05EA." })] }), _jsx("div", { className: "tabs", role: "tablist", "aria-label": "\u05E1\u05D5\u05D2 \u05D4\u05D7\u05D9\u05E4\u05D5\u05E9", children: OPTIONS.map((name) => (_jsxs("button", { type: "button", role: "tab", id: `tab-${name}`, "aria-selected": tab === name, "aria-controls": "tab-panel", className: tab === name ? 'tab is-on' : 'tab', onClick: () => setTab(name), children: [OPTION_NAMES[name], !draft[name].enabled && _jsx("span", { className: "off-tag", children: "\u05DB\u05D1\u05D5\u05D9" })] }, name))) }), _jsxs("div", { className: "tabpanel", role: "tabpanel", id: "tab-panel", "aria-labelledby": `tab-${tab}`, children: [_jsxs("section", { className: "pcard tabhead", children: [_jsxs("div", { className: "tabhead-row", children: [_jsx(Switch, { label: "\u05D4\u05D7\u05D9\u05E4\u05D5\u05E9 \u05D4\u05D6\u05D4 \u05E4\u05E2\u05D9\u05DC", checked: option.enabled, onChange: (enabled) => change(tab)({ enabled }) }), _jsxs("button", { type: "button", className: "barbtn", onClick: () => edit(copyFromOther(draft, tab)), children: ["\u05D4\u05E2\u05EA\u05E7\u05D4 \u05DE", OPTION_NAMES[other(tab)]] })] }), _jsx("p", { className: "pline", children: option.enabled
                                                    ? `ההעתקה לוקחת את כל הערכים מ${OPTION_NAMES[other(tab)]}, מלבד ההפעלה` +
                                                        (tab === 'room' ? ' והגודל במ״ר, שאין בחיפוש חדר.' : '. הגודל במ״ר של דירה שלמה נשאר כמו שהוא.')
                                                    : 'החיפוש כבוי: הערכים נשמרים, אבל מודעות מהסוג הזה לא יוצגו.' }), _jsx("p", { className: "pline", children: MUST_HIDES })] }), _jsx("section", { className: "pcard", children: _jsx(AreasField, { option: option, groups: groups, names: names, onChange: change(tab) }) }), _jsx("section", { className: "pcard", children: _jsx(PriceField, { option: option, onChange: change(tab), full: true }) }), _jsx("section", { className: "pcard", children: _jsx(RangeField, { title: "\u05D7\u05D3\u05E8\u05D9\u05DD", scale: "rooms", range: option.rooms, onChange: (rooms) => change(tab)({ rooms }), full: true }) }), _jsx("section", { className: "pcard", children: _jsx(RangeField, { title: "\u05E7\u05D5\u05DE\u05D4", scale: "floor", range: option.floor, onChange: (floor) => change(tab)({ floor }), hint: "-1 \u05DE\u05E8\u05EA\u05E3, 0 \u05E7\u05E8\u05E7\u05E2", full: true }) }), tab === 'whole_apartment' && (_jsx("section", { className: "pcard", children: _jsx(RangeField, { title: "\u05D2\u05D5\u05D3\u05DC (\u05DE\u05F4\u05E8)", scale: "size", range: option.size_sqm, onChange: (size_sqm) => change(tab)({ size_sqm }), full: true }) })), _jsx("section", { className: "pcard", children: _jsx(EntryField, { entry: option.entry_date, onChange: (entry_date) => change(tab)({ entry_date }) }) }), _jsx("section", { className: "pcard", children: _jsx(FeaturesField, { option: option, onChange: change(tab), tiles: true }) }), _jsx("section", { className: "pcard", children: _jsx(WomenField, { option: option, onChange: change(tab) }) })] })] })] }), _jsx("div", { className: "phone-save", children: saveRow })] }));
}
