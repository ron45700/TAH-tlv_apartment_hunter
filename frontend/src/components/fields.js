import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The values of one search option, as fields (PHASE_3.md 3.7 (e)): the areas grouped as §6 with
// "select all" per group and the non-residential group collapsed at the bottom (#248, #249, #261);
// the price (critical, no level, BASELINE.md §8); the ranges with their level; the features with a
// fixed wanted value (#269); the entry date with "immediate" as a quick chip (#270); "women only".
// The bar's popovers and phone sheet show them compact; the preferences page shows them in full,
// each range with a slider (`full`). Every field's "נקה" clears it to "don't care".
import { useEffect, useRef } from 'react';
import { FEATURES, FEATURE_NAMES, setDateEnd, setEarliest, immediateEntry, setRangeEnd, toggleAreas, } from '../bar';
import { DualSlider, LevelSwitch, NumberBox, Switch } from './controls';
export function Field({ title, onClear, children, hint, }) {
    return (_jsxs("fieldset", { className: "field", children: [_jsxs("div", { className: "field-head", children: [_jsx("legend", { children: title }), onClear && (_jsx("button", { type: "button", className: "linkbtn", onClick: onClear, children: "\u05E0\u05E7\u05D4" }))] }), hint && _jsx("p", { className: "field-hint", children: hint }), children] }));
}
// --- areas ---
export function AreaPicker({ selected, groups, names, onChange, }) {
    const chosen = new Set(selected);
    return (_jsx("div", { className: "areas", children: groups.map((group) => {
            const inGroup = group.areas.filter((n) => chosen.has(n)).length;
            const all = (_jsx(GroupCheck, { heading: group.heading, count: inGroup, total: group.areas.length, onChange: (on) => onChange(toggleAreas(selected, group.areas, on)) }));
            const list = (_jsx("ul", { className: "area-list", children: group.areas.map((number) => (_jsx("li", { children: _jsxs("label", { className: "check", children: [_jsx("input", { name: `area-${number}`, type: "checkbox", checked: chosen.has(number), onChange: (event) => onChange(toggleAreas(selected, [number], event.target.checked)) }), _jsx("span", { children: names.get(number) ?? number })] }) }, number))) }));
            if (group.collapsed) {
                return (_jsxs("details", { className: "area-group is-collapsed", open: inGroup > 0 || undefined, children: [_jsxs("summary", { children: [_jsx("span", { className: "area-heading", children: group.heading }), inGroup > 0 && _jsxs("span", { className: "area-count", children: [inGroup, " \u05E0\u05D1\u05D7\u05E8\u05D5"] })] }), _jsx("div", { className: "area-all", children: all }), list] }, group.heading));
            }
            return (_jsxs("section", { className: "area-group", children: [_jsxs("div", { className: "area-head", children: [_jsx("h3", { className: "area-heading", children: group.heading }), all] }), list] }, group.heading));
        }) }));
}
function GroupCheck({ heading, count, total, onChange, }) {
    const box = useRef(null);
    useEffect(() => {
        if (box.current)
            box.current.indeterminate = count > 0 && count < total;
    }, [count, total]);
    return (_jsxs("label", { className: "check check-all", children: [_jsx("input", { ref: box, name: `group-${heading}`, type: "checkbox", "aria-label": `כל האזורים ב${heading}`, checked: count === total, onChange: (event) => onChange(event.target.checked) }), _jsx("span", { children: "\u05D1\u05D7\u05D9\u05E8\u05EA \u05D4\u05DB\u05DC" })] }));
}
export function AreasField({ option, groups, names, onChange, }) {
    const count = option.areas.length;
    return (_jsx(Field, { title: "\u05D0\u05D6\u05D5\u05E8\u05D9\u05DD", onClear: count ? () => onChange({ areas: [] }) : undefined, hint: count ? `${count} נבחרו. מודעה מחוץ לאזורים שנבחרו לא תוצג.` : 'בלי בחירה: כל האזורים.', children: _jsx(AreaPicker, { selected: option.areas, groups: groups, names: names, onChange: (areas) => onChange({ areas }) }) }));
}
// --- price and ranges ---
const SCALES = {
    price: { min: 0, max: 15000, step: 100 },
    rooms: { min: 1, max: 8, step: 0.5 },
    floor: { min: -1, max: 30, step: 1 },
    size: { min: 0, max: 250, step: 5 },
};
export function PriceField({ option, onChange, full = false }) {
    const held = option.price_min !== null || option.price_max !== null;
    return (_jsxs(Field, { title: "\u05DE\u05D7\u05D9\u05E8 \u05DC\u05D7\u05D5\u05D3\u05E9 (\u20AA)", onClear: held ? () => onChange({ price_min: null, price_max: null }) : undefined, hint: full ? 'מודעה מחוץ לטווח לא תוצג. תיבה ריקה: ללא הגבלה.' : undefined, children: [_jsxs("div", { className: "pair", children: [_jsx(NumberBox, { label: "\u05DE-", value: option.price_min, min: 0, step: 100, onChange: (v) => onChange({ price_min: v }) }), _jsx(NumberBox, { label: "\u05E2\u05D3", value: option.price_max, min: 0, step: 100, onChange: (v) => onChange({ price_max: v }) })] }), full && (_jsx(DualSlider, { label: "\u05DE\u05D7\u05D9\u05E8", ...SCALES.price, low: option.price_min, high: option.price_max, onChange: (low, high) => onChange({ price_min: low, price_max: high }) }))] }));
}
export function RangeField({ title, scale, range, onChange, full = false, hint, }) {
    const { min, max, step } = SCALES[scale];
    return (_jsxs(Field, { title: title, onClear: range ? () => onChange(null) : undefined, hint: hint, children: [_jsxs("div", { className: "pair", children: [_jsx(NumberBox, { label: "\u05DE-", value: range?.min ?? null, min: min, step: step, onChange: (v) => onChange(setRangeEnd(range, 'min', v)) }), _jsx(NumberBox, { label: "\u05E2\u05D3", value: range?.max ?? null, min: min, step: step, onChange: (v) => onChange(setRangeEnd(range, 'max', v)) })] }), full && (_jsx(DualSlider, { label: title, min: min, max: max, step: step, low: range?.min ?? null, high: range?.max ?? null, onChange: (low, high) => onChange(low === null && high === null ? null : { min: low, max: high, level: range?.level ?? 'preference' }) })), range && _jsx(LevelSwitch, { label: title, value: range.level, onChange: (level) => onChange({ ...range, level }) })] }));
}
// --- features, entry date, women only ---
function FeatureControl({ feature, level, onChange, tile, }) {
    const name = FEATURE_NAMES[feature];
    return (_jsxs("div", { className: `feature${level ? ' is-on' : ''}`, children: [tile ? (_jsx("button", { type: "button", className: "tile", "aria-pressed": level !== null, onClick: () => onChange(level ? null : 'preference'), children: name })) : (_jsx(Switch, { label: name, checked: level !== null, onChange: (on) => onChange(on ? 'preference' : null) })), level && _jsx(LevelSwitch, { label: name, value: level, onChange: onChange })] }));
}
export function FeaturesField({ option, onChange, tiles = false }) {
    const held = FEATURES.some((feature) => option[feature] !== null);
    return (_jsx(Field, { title: "\u05DE\u05D0\u05E4\u05D9\u05D9\u05E0\u05D9\u05DD", onClear: held ? () => onChange({ broker: null, parking: null, balcony: null }) : undefined, children: _jsx("div", { className: tiles ? 'features is-tiles' : 'features', children: FEATURES.map((feature) => (_jsx(FeatureControl, { feature: feature, level: option[feature], tile: tiles, onChange: (level) => onChange({ [feature]: level }) }, feature))) }) }));
}
export function EntryField({ entry, onChange, }) {
    const immediate = entry?.immediate === true;
    return (_jsxs(Field, { title: "\u05EA\u05D0\u05E8\u05D9\u05DA \u05DB\u05E0\u05D9\u05E1\u05D4", onClear: entry ? () => onChange(null) : undefined, children: [_jsx("div", { className: "quick", children: _jsx("button", { type: "button", className: immediate ? 'qchip is-on' : 'qchip', "aria-pressed": immediate, onClick: () => onChange(immediate ? null : immediateEntry(entry)), children: "\u05DE\u05D9\u05D9\u05D3\u05D9" }) }), _jsxs("div", { className: "pair", children: [_jsxs("label", { className: "numbox", children: [_jsx("span", { className: "numbox-label", children: "\u05DE\u05EA\u05D0\u05E8\u05D9\u05DA" }), _jsx("input", { name: "entry-earliest", type: "date", value: entry?.earliest ?? '', onChange: (event) => onChange(setEarliest(entry, event.target.value)) })] }), _jsxs("label", { className: "numbox", children: [_jsx("span", { className: "numbox-label", children: "\u05E2\u05D3 \u05EA\u05D0\u05E8\u05D9\u05DA" }), _jsx("input", { name: "entry-latest", type: "date", value: entry?.latest ?? '', onChange: (event) => onChange(setDateEnd(entry, 'latest', event.target.value)) })] })] }), entry && _jsx(LevelSwitch, { label: "\u05EA\u05D0\u05E8\u05D9\u05DA \u05DB\u05E0\u05D9\u05E1\u05D4", value: entry.level, onChange: (level) => onChange({ ...entry, level }) })] }));
}
export function WomenField({ option, onChange }) {
    return (_jsx(Field, { title: "\u05E0\u05E9\u05D9\u05DD \u05D1\u05DC\u05D1\u05D3", children: _jsx(Switch, { label: "\u05D4\u05E1\u05EA\u05E8\u05EA \u05DE\u05D5\u05D3\u05E2\u05D5\u05EA \u05DC\u05E0\u05E9\u05D9\u05DD \u05D1\u05DC\u05D1\u05D3", checked: option.hide_women_only, onChange: (hide) => onChange({ hide_women_only: hide }) }) }));
}
/** Everything inside "עוד" (3.7 (e)(ii)): floor, sqm in the whole apartment only (#247), the
 *  features, the entry date and "women only", each category with its level (#330 point 15). */
export function MoreFields({ name, option, onChange, }) {
    return (_jsxs(_Fragment, { children: [_jsx(RangeField, { title: "\u05E7\u05D5\u05DE\u05D4", scale: "floor", range: option.floor, hint: "-1 \u05DE\u05E8\u05EA\u05E3, 0 \u05E7\u05E8\u05E7\u05E2", onChange: (floor) => onChange({ floor }) }), name === 'whole_apartment' && (_jsx(RangeField, { title: "\u05D2\u05D5\u05D3\u05DC (\u05DE\u05F4\u05E8)", scale: "size", range: option.size_sqm, onChange: (size_sqm) => onChange({ size_sqm }) })), _jsx(FeaturesField, { option: option, onChange: onChange }), _jsx(EntryField, { entry: option.entry_date, onChange: (entry_date) => onChange({ entry_date }) }), _jsx(WomenField, { option: option, onChange: onChange })] }));
}
