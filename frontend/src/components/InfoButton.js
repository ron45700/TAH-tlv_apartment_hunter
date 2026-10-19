import { jsx as _jsx } from "react/jsx-runtime";
// The "i" over the photo's top-left corner, inside the card, on a faded background (#323, #337): it
// shows the tier's words on hover or focus (desktop) and on tap (phone). It is a button whose
// accessible name is the label, so a screen reader reads the tier without the colour. The "i" is drawn
// by CSS, an icon and not text, so the name holds the tier's words only (WCAG 2.5.3, #374).
import { useEffect, useRef, useState } from 'react';
export function InfoButton({ label }) {
    const [open, setOpen] = useState(false);
    const button = useRef(null);
    useEffect(() => {
        if (!open)
            return;
        const close = (event) => {
            if (!button.current?.contains(event.target))
                setOpen(false);
        };
        document.addEventListener('pointerdown', close);
        return () => document.removeEventListener('pointerdown', close);
    }, [open]);
    return (_jsx("button", { ref: button, className: open ? 'info is-open' : 'info', type: "button", "aria-label": label, "aria-expanded": open, onClick: (event) => {
            event.preventDefault();
            event.stopPropagation();
            setOpen((value) => !value);
        }, onKeyDown: (event) => event.key === 'Escape' && setOpen(false), children: _jsx("span", { className: "tip", role: "tooltip", children: label }) }));
}
