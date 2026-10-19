import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The correction's value form (3.8 (h), step 5): one reportable field in its Gate B shape. A Marked
// field first asks its state (written, not stated, unclear), then the value; a closed list is a set
// of radio buttons; the areas are 3.7's area picker; the phones' names one box per phone of the
// post. The server checks the value by its Gate B type and as the whole post (#284, #405).
import { useEffect, useRef, useState } from 'react';
import { CHOICES, KINDS, draftOf, isMarked, valueOf } from '../../admin/values';
import { AreaPicker } from '../../components/fields';
const STATES = [
    ['written', 'כתוב במודעה'],
    ['not_written', 'לא צוין'],
    ['unclear', 'לא ברור'],
];
export function ValueForm({ field, label, value, phones, groups, names, busy, error, onSubmit, onCancel }) {
    const [draft, setDraft] = useState(() => draftOf(field, value, phones));
    const kind = KINDS[field];
    const result = valueOf(field, draft);
    const set = (change) => setDraft((current) => ({ ...current, ...change }));
    const submit = (event) => {
        event.preventDefault();
        if (result !== null)
            onSubmit(result);
    };
    const id = `vf-${field}`;
    const form = useRef(null);
    const heading = useRef(null);
    // Opened from a row far below, the form comes into view and takes the focus (#408).
    useEffect(() => {
        form.current?.scrollIntoView({ block: 'start' });
        heading.current?.focus({ preventScroll: true });
    }, []);
    return (_jsxs("form", { ref: form, className: "valueform", onSubmit: submit, "aria-labelledby": `${id}-title`, children: [_jsxs("h3", { id: `${id}-title`, ref: heading, tabIndex: -1, children: ["\u05EA\u05D9\u05E7\u05D5\u05DF: ", label] }), kind === 'enum' && (_jsx(Radios, { name: `${id}-choice`, legend: label, choices: CHOICES[field], value: draft.choice, onChange: (choice) => set({ choice }) })), isMarked(kind) && (_jsx(Radios, { name: `${id}-state`, legend: "\u05DE\u05D4 \u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05D0\u05D5\u05DE\u05E8\u05EA", choices: STATES, value: draft.state, onChange: (state) => set({ state: state }) })), isMarked(kind) && draft.state === 'written' && _jsx(MarkedValue, { id: id, field: field, draft: draft, set: set }), kind === 'areas' && (_jsx("div", { className: "valueform-areas", children: _jsx(AreaPicker, { selected: draft.areas, groups: groups, names: names, onChange: (areas) => set({ areas }) }) })), kind === 'lines' && (_jsx(Labelled, { id: `${id}-text`, label: "\u05E8\u05D7\u05D5\u05D1 \u05D1\u05DB\u05DC \u05E9\u05D5\u05E8\u05D4", children: _jsx("textarea", { id: `${id}-text`, rows: 3, value: draft.text, onChange: (event) => set({ text: event.target.value }) }) })), kind === 'city' && (_jsx(Labelled, { id: `${id}-text`, label: "\u05D4\u05E2\u05D9\u05E8", hint: "\u05D4\u05E9\u05D0\u05D9\u05E8\u05D5 \u05E8\u05D9\u05E7 \u05DB\u05E9\u05D4\u05DE\u05D5\u05D3\u05E2\u05D4 \u05D1\u05EA\u05DC \u05D0\u05D1\u05D9\u05D1-\u05D9\u05E4\u05D5.", children: _jsx("input", { id: `${id}-text`, value: draft.text, onChange: (event) => set({ text: event.target.value }) }) })), kind === 'phones' &&
                (phones.length === 0 ? (_jsx("p", { className: "tfield-hint", children: "\u05D0\u05D9\u05DF \u05D8\u05DC\u05E4\u05D5\u05E0\u05D9\u05DD \u05D1\u05DE\u05D5\u05D3\u05E2\u05D4." })) : (phones.map((phone) => (_jsx(Labelled, { id: `${id}-${phone}`, label: `השם ליד ${phone}`, children: _jsx("input", { id: `${id}-${phone}`, value: draft.names[phone] ?? '', onChange: (event) => set({ names: { ...draft.names, [phone]: event.target.value } }) }) }, phone))))), _jsx("p", { className: error ? 'formerror' : undefined, role: "alert", children: error }), _jsxs("div", { className: "valueform-actions", children: [_jsx("button", { type: "submit", className: "mainbtn", disabled: busy || result === null, children: "\u05E9\u05DE\u05D9\u05E8\u05EA \u05D4\u05EA\u05D9\u05E7\u05D5\u05DF" }), _jsx("button", { type: "button", className: "linkbtn", onClick: onCancel, children: "\u05D1\u05D9\u05D8\u05D5\u05DC" })] })] }));
}
function MarkedValue({ id, field, draft, set, }) {
    const kind = KINDS[field];
    const text = (label, hint, inputMode = 'text') => (_jsx(Labelled, { id: `${id}-text`, label: label, hint: hint, children: _jsx("input", { id: `${id}-text`, dir: "ltr", inputMode: inputMode, value: draft.text, onChange: (event) => set({ text: event.target.value }) }) }));
    const radios = (legend, choices) => (_jsx(Radios, { name: `${id}-choice`, legend: legend, choices: choices, value: draft.choice, onChange: (choice) => set({ choice }) }));
    switch (kind) {
        case 'marked-enum':
            return radios('הערך', CHOICES[field]);
        case 'marked-bool':
            return radios('הערך', CHOICES.bool);
        case 'marked-amounts':
            return text('הסכומים בשקלים', 'כמה סכומים: מופרדים ברווח.', 'numeric');
        case 'marked-float':
            return text('המספר', 'חצאים בנקודה, למשל 3.5.', 'decimal');
        case 'marked-int':
            return text('המספר', field === 'floor' ? 'קרקע 0, מרתף -1.' : undefined, 'numeric');
        case 'marked-date':
            return (_jsxs(_Fragment, { children: [radios('הכניסה', [
                        ['immediate', 'מיידית'],
                        ['date', 'בתאריך'],
                    ]), draft.choice === 'date' && (_jsx(Labelled, { id: `${id}-text`, label: "\u05D4\u05EA\u05D0\u05E8\u05D9\u05DA", children: _jsx("input", { id: `${id}-text`, type: "date", value: draft.text, onChange: (event) => set({ text: event.target.value }) }) }))] }));
        case 'marked-fee':
            return (_jsxs(_Fragment, { children: [radios('הסכום', [
                        ['amount', 'סכום'],
                        ['included', 'כלול במחיר'],
                    ]), draft.choice === 'amount' && text('הסכום בשקלים', undefined, 'numeric')] }));
        default:
            return null;
    }
}
function Radios({ name, legend, choices, value, onChange, }) {
    return (_jsxs("fieldset", { className: "radios", children: [_jsx("legend", { children: legend }), choices.map(([choice, words]) => (_jsxs("label", { className: "radio", children: [_jsx("input", { type: "radio", name: name, value: choice, checked: value === choice, onChange: () => onChange(choice) }), _jsx("span", { children: words })] }, choice)))] }));
}
function Labelled({ id, label, hint, children }) {
    return (_jsxs("div", { className: "tfield", children: [_jsx("label", { htmlFor: id, children: label }), children, hint && _jsx("p", { className: "tfield-hint", children: hint })] }));
}
