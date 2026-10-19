import { Fragment as _Fragment, jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The header (#333, #334, #342): its own cool tint, the user area at the right, the logo at the left,
// the one deliberate exception to "nothing on the left" (#324). A guest sees "התחבר" and "הירשם",
// pills of one height (#343). A signed-in user sees one pill (#343): a round avatar with the
// username's first letter on a sky-to-teal gradient, the username and a chevron (on a phone the
// avatar and the chevron); it opens a menu with "ההעדפות שלי" and under it "התנתק" (#334); the admin
// also has "ניהול" at the top, the admin's pages (3.8 (a)).
import { useEffect, useRef, useState } from 'react';
import { navigate } from '../route';
function go(path) {
    return (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0)
            return;
        event.preventDefault();
        navigate(path);
    };
}
export function Header({ user, onSignOut }) {
    return (_jsx("header", { className: "appbar", children: _jsxs("div", { className: "shell appbar-row", children: [_jsxs("div", { className: "userarea", children: [user === null && (_jsxs(_Fragment, { children: [_jsx("a", { className: "pill pill-primary", href: "/sign-in", onClick: go('/sign-in'), children: "\u05D4\u05EA\u05D7\u05D1\u05E8" }), _jsx("a", { className: "pill", href: "/sign-up", onClick: go('/sign-up'), children: "\u05D4\u05D9\u05E8\u05E9\u05DD" })] })), user && _jsx(UserMenu, { user: user, onSignOut: onSignOut })] }), _jsxs("a", { className: "logo", href: "/", onClick: go('/'), "aria-label": "TLV Apartment Hunter, \u05DC\u05E2\u05DE\u05D5\u05D3 \u05D4\u05E8\u05D0\u05E9\u05D9", dir: "ltr", children: [_jsx(LogoMark, {}), _jsxs("span", { className: "word", children: [_jsx("span", { className: "w1", children: "TLV" }), ' ', _jsx("span", { className: "w2", children: "Apartment Hunter" })] })] })] }) }));
}
function UserMenu({ user, onSignOut }) {
    const [open, setOpen] = useState(false);
    const box = useRef(null);
    const button = useRef(null);
    useEffect(() => {
        if (!open)
            return;
        const onDown = (event) => {
            if (!box.current?.contains(event.target))
                setOpen(false);
        };
        const onKey = (event) => {
            if (event.key === 'Escape') {
                setOpen(false);
                button.current?.focus();
            }
        };
        document.addEventListener('pointerdown', onDown);
        document.addEventListener('keydown', onKey);
        return () => {
            document.removeEventListener('pointerdown', onDown);
            document.removeEventListener('keydown', onKey);
        };
    }, [open]);
    const letter = user.username.slice(0, 1).toUpperCase();
    return (_jsxs("div", { className: "usermenu", ref: box, children: [_jsxs("button", { ref: button, type: "button", className: "userpill", "aria-haspopup": "menu", "aria-expanded": open, "aria-label": `${user.username}, תפריט החשבון`, onClick: () => setOpen((value) => !value), children: [_jsx("span", { className: "avatar", "aria-hidden": "true", "data-letter": letter }), _jsx("span", { className: "username", dir: "ltr", children: user.username }), _jsx("span", { className: "chev", "aria-hidden": "true" })] }), open && (_jsxs("div", { className: "menu", role: "menu", children: [user.is_admin && !user.must_change_password && (_jsx("a", { role: "menuitem", href: "/admin", onClick: (event) => {
                            setOpen(false);
                            go('/admin')(event);
                        }, children: "\u05E0\u05D9\u05D4\u05D5\u05DC" })), !user.must_change_password && (_jsx("a", { role: "menuitem", href: "/preferences", onClick: (event) => {
                            setOpen(false);
                            go('/preferences')(event);
                        }, children: "\u05D4\u05D4\u05E2\u05D3\u05E4\u05D5\u05EA \u05E9\u05DC\u05D9" })), _jsx("button", { role: "menuitem", type: "button", onClick: () => {
                            setOpen(false);
                            onSignOut();
                        }, children: "\u05D4\u05EA\u05E0\u05EA\u05E7" })] }))] }));
}
/** The mark: three white-city blocks with their windows, over the sea's line, on a sky-to-teal
 *  tile. Light and cool (#333). The same drawing is public/favicon.svg. */
export function LogoMark() {
    return (_jsxs("svg", { className: "mark", width: "44", height: "44", viewBox: "0 0 44 44", "aria-hidden": "true", children: [_jsx("defs", { children: _jsxs("linearGradient", { id: "logo-sky", x1: "0", y1: "0", x2: "1", y2: "1", children: [_jsx("stop", { offset: "0", stopColor: "#c7ecfb" }), _jsx("stop", { offset: "1", stopColor: "#5fd8c6" })] }) }), _jsx("rect", { x: "1", y: "1", width: "42", height: "42", rx: "12", fill: "url(#logo-sky)" }), _jsx("circle", { cx: "33.5", cy: "11", r: "3.2", fill: "#ffffff", fillOpacity: ".9" }), _jsx("path", { d: "M8 32V20.5l6.5-3.5V32z M16.5 32V12.5l8-4V32z M26.5 32V17l9 3.2V32z", fill: "#ffffff" }), _jsx("path", { d: "M10.5 22.5h2M10.5 26h2M19.5 14h2M19.5 17.5h2M19.5 21h2M19.5 24.5h2M29.5 21.5h3M29.5 25h3", stroke: "#7cc9d9", strokeWidth: "1.6", strokeLinecap: "round" }), _jsx("path", { d: "M5 36.5c4-2.4 7-2.4 11 0s7 2.4 11 0 7-2.4 12 0", stroke: "#0e7490", strokeWidth: "2.2", fill: "none", strokeLinecap: "round" })] }));
}
