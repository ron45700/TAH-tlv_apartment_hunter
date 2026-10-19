import { jsx as _jsx } from "react/jsx-runtime";
// "Back to top" on a phone (Ron, 2026-10-18): a small round button at the bottom centre, over the
// safe area, shown only once the list has scrolled more than a screen down. It never covers a card's
// buttons: when the scrolling stops it looks at what lies under it, and stays hidden while a card's
// foot buttons or its "i" are there (checked when the page comes to rest, so it does not blink past
// every card while the list moves). Hidden, it is `visibility: hidden`: out of the tab order and of
// what a screen reader reads. The arrow is drawn by CSS, so the name is the words only (#374). The
// phone's header still scrolls away; this brings it back.
import { useEffect, useRef, useState } from 'react';
const SETTLE_MS = 150;
const UNDER = '.card .acts, .card .info';
export function BackToTop() {
    const button = useRef(null);
    const [shown, setShown] = useState(false);
    useEffect(() => {
        let timer = 0;
        const covers = () => {
            const box = button.current?.getBoundingClientRect();
            if (!box)
                return false;
            const xs = [box.left + 2, box.left + box.width / 2, box.right - 2];
            const ys = [box.top + 2, box.top + box.height / 2, box.bottom - 2];
            return xs.some((x) => ys.some((y) => document.elementsFromPoint(x, y).some((el) => el.closest(UNDER))));
        };
        const settle = () => setShown(window.scrollY > window.innerHeight && !covers());
        const onScroll = () => {
            if (window.scrollY <= window.innerHeight)
                setShown(false);
            window.clearTimeout(timer);
            timer = window.setTimeout(settle, SETTLE_MS);
        };
        settle();
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll);
        return () => {
            window.clearTimeout(timer);
            window.removeEventListener('scroll', onScroll);
            window.removeEventListener('resize', onScroll);
        };
    }, []);
    const toTop = () => {
        const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: 0, behavior: still ? 'auto' : 'smooth' });
        // the button goes once the page is at the top: the focus moves to the header's first control
        document.querySelector('.appbar a, .appbar button')?.focus({ preventScroll: true });
    };
    return (_jsx("button", { ref: button, type: "button", className: shown ? 'totop is-shown' : 'totop', "aria-label": "\u05D7\u05D6\u05E8\u05D4 \u05DC\u05E8\u05D0\u05E9 \u05D4\u05E2\u05DE\u05D5\u05D3", onClick: toTop }));
}
