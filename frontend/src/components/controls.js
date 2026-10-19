import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// Small controls the bar and the preferences page share (PHASE_3.md 3.7 (e)). A switch reads on or
// off by its track and position, its label always in words; the level is a two-way switch,
// "העדפה" or "חובה" (BASELINE.md §8); no glyph carries a state (#323).
import { useEffect, useId, useRef } from 'react';
export function Switch({ label, checked, onChange, disabled = false, describedBy, }) {
    const name = useId();
    return (_jsxs("label", { className: `switch${disabled ? ' is-disabled' : ''}`, children: [_jsx("input", { name: name, type: "checkbox", role: "switch", checked: checked, disabled: disabled, "aria-describedby": describedBy, onChange: (event) => onChange(event.target.checked) }), _jsx("span", { className: "track", "aria-hidden": "true" }), _jsx("span", { className: "switch-label", children: label })] }));
}
export const LEVEL_WORDS = { preference: 'העדפה', critical: 'חובה' };
export const MUST_HIDES = 'חובה: מודעה שלא עומדת בזה לא תוצג. העדפה: משפיעה רק על הסדר והצבעים.';
export function LevelSwitch({ value, onChange, label, }) {
    const name = useId();
    return (_jsx("div", { className: "levels", role: "radiogroup", "aria-label": `רמה: ${label}`, children: ['preference', 'critical'].map((level) => (_jsxs("label", { className: value === level ? 'level is-on' : 'level', children: [_jsx("input", { type: "radio", name: name, checked: value === level, onChange: () => onChange(level) }), LEVEL_WORDS[level]] }, level))) }));
}
/** A panel under its button: closes on a click outside it and on Esc, and gives the focus back. */
export function Popover({ label, onClose, children, wide = false, }) {
    const panel = useRef(null);
    const close = useRef(onClose);
    close.current = onClose;
    useEffect(() => {
        const opener = document.activeElement;
        panel.current?.focus();
        const onKey = (event) => {
            if (event.key === 'Escape') {
                event.stopPropagation();
                close.current();
            }
        };
        const onDown = (event) => {
            const target = event.target;
            if (panel.current?.contains(target) || opener?.contains(target))
                return; // the opener toggles
            close.current();
        };
        document.addEventListener('keydown', onKey);
        document.addEventListener('pointerdown', onDown);
        return () => {
            document.removeEventListener('keydown', onKey);
            document.removeEventListener('pointerdown', onDown);
            opener?.focus?.();
        };
    }, []);
    return (_jsx("div", { className: wide ? 'popover is-wide' : 'popover', role: "dialog", "aria-label": label, ref: panel, tabIndex: -1, children: children }));
}
/** A number box; an empty box is "don't care" (`null`). */
export function NumberBox({ label, value, onChange, min, max, step, placeholder, }) {
    const name = useId();
    return (_jsxs("label", { className: "numbox", children: [_jsx("span", { className: "numbox-label", children: label }), _jsx("input", { name: name, type: "number", inputMode: "decimal", dir: "ltr", value: value ?? '', min: min, max: max, step: step, placeholder: placeholder, onChange: (event) => {
                    const text = event.target.value;
                    const parsed = text === '' ? null : Number(text);
                    onChange(parsed === null || Number.isNaN(parsed) ? null : parsed);
                } })] }));
}
/** Two thumbs on one track (the preferences page's ranges, 3.7 (e)(iii)). A thumb at its end of the
 *  track is an open end (`null`). */
export function DualSlider({ label, low, high, min, max, step, onChange, }) {
    const id = useId();
    const lowValue = Math.max(min, Math.min(low ?? min, max));
    const highValue = Math.max(min, Math.min(high ?? max, max));
    const percent = (value) => ((value - min) / (max - min)) * 100;
    const style = { '--lo': `${percent(lowValue)}%`, '--hi': `${percent(highValue)}%` };
    return (_jsxs("div", { className: low === null && high === null ? 'dual is-open' : 'dual', style: style, dir: "rtl", children: [_jsx("span", { className: "dual-fill", "aria-hidden": "true" }), _jsx("input", { name: `${id}-low`, type: "range", "aria-label": `${label}: מינימום`, min: min, max: max, step: step, value: lowValue, onChange: (event) => {
                    const value = Math.min(Number(event.target.value), highValue);
                    onChange(value <= min ? null : value, high);
                } }), _jsx("input", { name: `${id}-high`, type: "range", "aria-label": `${label}: מקסימום`, min: min, max: max, step: step, value: highValue, onChange: (event) => {
                    const value = Math.max(Number(event.target.value), lowValue);
                    onChange(low, value >= max ? null : value);
                } })] }));
}
