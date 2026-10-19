import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The filter bar, as redesigned in round 9 (PHASE_3.md 3.7 (e)(ii); #329, #333–#336, #317): sticky
// under the header. Row 1: the two kinds and the profile's one sublet switch, disabled with its line
// when both kinds are off; then the status line, the count and where the bar stands, in words, with
// "ההעדפות שלי" to reset it when it differs from the saved preferences (#335). One values row per
// kind that is on, labelled with the kind's name: areas, price, rooms and "עוד", each a pill that
// fills with its value in words. No save in the bar (#335). On a phone (point 39, option A): the three
// switches on one row, one dense row with the status and "סינון (N)", and a full-screen sheet with
// the same rows and "הצגת N מודעות". Hiding (#465, #468, point 15): on the saved preferences, for a
// signed-in user, the status line carries "הצגת מוסתרים" and, with it off, "· M מוסתרות"; the
// switch is the tab's, never saved, and absent in a temporary filter, where it would change nothing.
import { useEffect, useState } from 'react';
import { OPTIONS, OPTION_NAMES, areasWords, barHeldCount, moreCount, priceWords, roomsWords, withOption, } from '../bar';
import { Popover, Switch } from './controls';
import { AreasField, MoreFields, PriceField, RangeField } from './fields';
export function FilterBar(props) {
    const { bar, onChange, phone } = props;
    const [sheet, setSheet] = useState(false);
    const noKind = !bar.room.enabled && !bar.whole_apartment.enabled;
    const kinds = (_jsxs("div", { className: "kinds", children: [OPTIONS.map((name) => (_jsx(Switch, { label: OPTION_NAMES[name], checked: bar[name].enabled, onChange: (enabled) => onChange(withOption(bar, name, { enabled })) }, name))), _jsx(Switch, { label: "\u05D2\u05DD \u05E1\u05D0\u05D1\u05DC\u05D8", checked: bar.include_sublets, disabled: noKind, describedBy: noKind ? 'no-kind-line' : undefined, onChange: (include_sublets) => onChange({ ...bar, include_sublets }) })] }));
    const noKindLine = noKind && (_jsx("p", { className: "bar-note", id: "no-kind-line", children: "\u05D1\u05D7\u05E8\u05D5 \u05D7\u05D3\u05E8 \u05D0\u05D5 \u05D3\u05D9\u05E8\u05D4 \u05E9\u05DC\u05DE\u05D4 \u05DB\u05D3\u05D9 \u05DC\u05E8\u05D0\u05D5\u05EA \u05E1\u05D0\u05D1\u05DC\u05D8\u05D9\u05DD" }));
    const error = props.error && (_jsx("p", { className: "bar-error", role: "alert", children: props.error }));
    if (phone) {
        const held = barHeldCount(bar);
        return (_jsxs("div", { className: "filterbar is-phone", children: [_jsxs("div", { className: "shell", children: [kinds, noKindLine, _jsxs("div", { className: "bar-statusrow", children: [_jsx(Status, { ...props }), _jsx("button", { type: "button", className: "barbtn", onClick: () => setSheet(true), "aria-haspopup": "dialog", children: held ? `סינון (${held})` : 'סינון' })] }), error] }), sheet && _jsx(Sheet, { ...props, noKind: noKind, onClose: () => setSheet(false) })] }));
    }
    return (_jsx("div", { className: "filterbar", children: _jsxs("div", { className: "shell", children: [_jsxs("div", { className: "bar-row", children: [kinds, _jsx(Status, { ...props })] }), noKindLine, OPTIONS.filter((name) => bar[name].enabled).map((name) => (_jsx(ValuesRow, { name: name, ...props }, name))), error] }) }));
}
function Status({ standing, count, onReset, hidden }) {
    return (_jsxs("div", { className: "bar-status", children: [_jsxs("span", { "aria-live": "polite", children: [_jsx("strong", { children: count === null ? 'טוען מודעות…' : `${count} מודעות` }), standing === 'saved' && _jsx("span", { className: "status-long", children: " \u00B7 \u05DC\u05E4\u05D9 \u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05D4\u05E9\u05DE\u05D5\u05E8\u05D5\u05EA" }), hidden && !hidden.show && hidden.count > 0 && ` · ${hidden.count} מוסתרות`, standing === 'changed' && (_jsxs(_Fragment, { children: [' · סינון זמני', _jsx("span", { className: "status-long", children: ", \u05E9\u05D5\u05E0\u05D4 \u05DE\u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05E9\u05DC\u05DA" })] }))] }), standing === 'changed' && (_jsx("button", { type: "button", className: "barbtn is-reset", onClick: onReset, children: "\u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05E9\u05DC\u05D9" })), hidden && _jsx(Switch, { label: "\u05D4\u05E6\u05D2\u05EA \u05DE\u05D5\u05E1\u05EA\u05E8\u05D9\u05DD", checked: hidden.show, onChange: hidden.onShow })] }));
}
function ValuesRow({ name, bar, onChange, groups, names }) {
    const [open, setOpen] = useState(null);
    const option = bar[name];
    const change = (values) => onChange(withOption(bar, name, values));
    const more = moreCount(option);
    const toggle = (control) => setOpen((current) => (current === control ? null : control));
    const close = () => setOpen(null);
    const label = (control) => `${control}, ${OPTION_NAMES[name]}`;
    return (_jsxs("div", { className: "values", role: "group", "aria-label": OPTION_NAMES[name], children: [_jsxs("span", { className: "values-name", children: [OPTION_NAMES[name], ":"] }), _jsx(ValueChip, { label: "\u05D0\u05D6\u05D5\u05E8\u05D9\u05DD", words: areasWords(option.areas, names), open: open === 'areas', onToggle: () => toggle('areas'), onClear: () => change({ areas: [] }), children: _jsx(Popover, { label: label('אזורים'), onClose: close, wide: true, children: _jsx(AreasField, { option: option, groups: groups, names: names, onChange: change }) }) }), _jsx(ValueChip, { label: "\u05DE\u05D7\u05D9\u05E8", words: priceWords(option), open: open === 'price', onToggle: () => toggle('price'), onClear: () => change({ price_min: null, price_max: null }), children: _jsx(Popover, { label: label('מחיר'), onClose: close, children: _jsx(PriceField, { option: option, onChange: change }) }) }), _jsx(ValueChip, { label: "\u05D7\u05D3\u05E8\u05D9\u05DD", words: roomsWords(option.rooms), open: open === 'rooms', onToggle: () => toggle('rooms'), onClear: () => change({ rooms: null }), children: _jsx(Popover, { label: label('חדרים'), onClose: close, children: _jsx(RangeField, { title: "\u05D7\u05D3\u05E8\u05D9\u05DD", scale: "rooms", range: option.rooms, onChange: (rooms) => change({ rooms }) }) }) }), _jsx(ValueChip, { label: "\u05E2\u05D5\u05D3", words: more ? `עוד (${more})` : null, open: open === 'more', onToggle: () => toggle('more'), children: _jsx(Popover, { label: label('עוד'), onClose: close, wide: true, children: _jsx("div", { className: "more-grid", children: _jsx(MoreFields, { name: name, option: option, onChange: change }) }) }) })] }));
}
function ValueChip({ label, words, open, onToggle, onClear, children, }) {
    return (_jsxs("div", { className: "bchip-wrap", children: [_jsx("button", { type: "button", className: words ? 'bchip is-held' : 'bchip', "aria-expanded": open, "aria-haspopup": "dialog", onClick: onToggle, children: words ?? label }), words && onClear && (_jsx("button", { type: "button", className: "bchip-clear", onClick: onClear, "aria-label": `ניקוי: ${words}`, children: "\u05E0\u05E7\u05D4" })), open && children] }));
}
/** The phone's full-screen sheet (3.7 (e)(ii)): the kind rows, labelled as on a desktop, and
 *  "הצגת N מודעות" at its foot. The list behind it follows every change. */
function Sheet(props) {
    const { bar, onChange, groups, names, count, onClose } = props;
    useEffect(() => {
        document.body.classList.add('locked');
        const onKey = (event) => event.key === 'Escape' && onClose();
        document.addEventListener('keydown', onKey);
        return () => {
            document.body.classList.remove('locked');
            document.removeEventListener('keydown', onKey);
        };
    }, [onClose]);
    return (_jsxs("div", { className: "barsheet", role: "dialog", "aria-modal": "true", "aria-label": "\u05E1\u05D9\u05E0\u05D5\u05DF", children: [_jsxs("div", { className: "barsheet-top", children: [_jsx("h2", { children: "\u05E1\u05D9\u05E0\u05D5\u05DF" }), _jsx("button", { type: "button", className: "barbtn", onClick: onClose, children: "\u05E1\u05D2\u05D9\u05E8\u05D4" })] }), _jsxs("div", { className: "barsheet-body", children: [props.noKind && _jsx("p", { className: "bar-note", children: "\u05D1\u05D7\u05E8\u05D5 \u05D7\u05D3\u05E8 \u05D0\u05D5 \u05D3\u05D9\u05E8\u05D4 \u05E9\u05DC\u05DE\u05D4 \u05D1\u05E9\u05D5\u05E8\u05D4 \u05D4\u05E2\u05DC\u05D9\u05D5\u05E0\u05D4." }), OPTIONS.filter((name) => bar[name].enabled).map((name) => {
                        const option = bar[name];
                        const change = (values) => onChange(withOption(bar, name, values));
                        const chosen = option.areas.length;
                        return (_jsxs("section", { className: "sheet-kind", children: [_jsx("h3", { children: OPTION_NAMES[name] }), _jsxs("details", { className: "sheet-areas", children: [_jsx("summary", { children: chosen ? `אזורים: ${chosen} נבחרו` : 'אזורים: כל האזורים' }), _jsx(AreasField, { option: option, groups: groups, names: names, onChange: change })] }), _jsx(PriceField, { option: option, onChange: change }), _jsx(RangeField, { title: "\u05D7\u05D3\u05E8\u05D9\u05DD", scale: "rooms", range: option.rooms, onChange: (rooms) => change({ rooms }) }), _jsx(MoreFields, { name: name, option: option, onChange: change })] }, name));
                    }), props.error && (_jsx("p", { className: "bar-error", role: "alert", children: props.error }))] }), _jsx("div", { className: "barsheet-foot", children: _jsx("button", { type: "button", className: "mainbtn", onClick: onClose, children: count === null ? 'טוען…' : `הצגת ${count} מודעות` }) })] }));
}
