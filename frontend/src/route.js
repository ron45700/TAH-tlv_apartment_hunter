// The page's addresses (PHASE_3.md 3.7 (f), (k): no router library): the list, /post/<id> (its own
// address, so the browser's back closes it), the screens of build step 5: /sign-in, /sign-up,
// /password and /preferences, and the admin's pages under /admin (3.8).
//
// A screen with unsaved changes (the preferences page) sets a guard: a link inside the site, the
// browser's back and forward, a reload and closing the tab all ask first (3.7 (e)(iii)).
import { useEffect, useState } from 'react';
/** The admin's pages (3.8 (c)): /admin, /admin/<page>, /admin/post/<id>. */
export const ADMIN_PAGES = [
    'overview',
    'rejected',
    'pending',
    'flags',
    'reports',
    'corrections',
    'archive',
    'keys',
    'users',
    'schedule',
];
const SCREENS = ['sign-in', 'sign-up', 'password', 'preferences'];
export function adminPath(page, id) {
    if (page === 'post')
        return `/admin/post/${encodeURIComponent(id ?? '')}`;
    return page === 'overview' ? '/admin' : `/admin/${page}`;
}
export function parseRoute(pathname) {
    const match = /^\/post\/([^/]+)\/?$/.exec(pathname);
    if (match)
        return { name: 'post', id: decodeURIComponent(match[1]) };
    const adminPost = /^\/admin\/post\/([^/]+)\/?$/.exec(pathname);
    if (adminPost)
        return { name: 'admin', page: 'post', id: decodeURIComponent(adminPost[1]) };
    const admin = /^\/admin(?:\/([a-z]+))?\/?$/.exec(pathname);
    if (admin) {
        const page = ADMIN_PAGES.find((name) => name === (admin[1] ?? 'overview'));
        if (page)
            return { name: 'admin', page };
    }
    const screen = SCREENS.find((name) => pathname.replace(/\/$/, '') === `/${name}`);
    return screen ? { name: screen } : { name: 'list' };
}
export function postPath(id) {
    return `/post/${encodeURIComponent(id)}`;
}
const listeners = new Set();
let guard = null;
let shownPath = typeof location === 'undefined' ? '/' : location.pathname;
/** While set, leaving asks first; `fn` answers whether there is something to lose. */
export function setLeaveGuard(fn) {
    guard = fn;
}
export const LEAVE_QUESTION = 'יש שינויים שלא נשמרו. לצאת בלי לשמור?';
function mayLeave() {
    return !guard || !guard() || window.confirm(LEAVE_QUESTION);
}
function changed() {
    shownPath = location.pathname;
    listeners.forEach((listener) => listener());
}
export function navigate(path, { replace = false } = {}) {
    if (path === location.pathname)
        return;
    if (!mayLeave())
        return;
    guard = null;
    if (replace)
        history.replaceState(null, '', path);
    else
        history.pushState(null, '', path);
    changed();
}
if (typeof window !== 'undefined') {
    window.addEventListener('popstate', () => {
        if (guard && guard() && !window.confirm(LEAVE_QUESTION)) {
            history.pushState(null, '', shownPath); // stay: the address back to the screen shown
            return;
        }
        guard = null;
        changed();
    });
    window.addEventListener('beforeunload', (event) => {
        if (guard && guard())
            event.preventDefault();
    });
}
export function useRoute() {
    const [route, setRoute] = useState(() => parseRoute(location.pathname));
    useEffect(() => {
        const update = () => setRoute(parseRoute(location.pathname));
        listeners.add(update);
        return () => {
            listeners.delete(update);
        };
    }, []);
    return route;
}
