export class ApiError extends Error {
    status;
    /** The server's refusal: a 3.5 reason name ("wrong", "delayed", …). */
    refusal;
    retryAfter;
    /** A 422's rule, or another error's detail. */
    detail;
    constructor(status, body) {
        super(`HTTP ${status}`);
        this.name = 'ApiError';
        this.status = status;
        this.refusal = typeof body?.refusal === 'string' ? body.refusal : null;
        this.retryAfter = typeof body?.retry_after_seconds === 'number' ? body.retry_after_seconds : null;
        this.detail = body?.detail ?? null;
    }
}
/** The one request every page makes (the admin's pages too, admin/api.ts). */
export async function call(method, path, body, signal) {
    let response;
    try {
        response = await fetch(path, {
            method,
            credentials: 'same-origin',
            referrerPolicy: 'same-origin',
            signal,
            headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
            body: body === undefined ? undefined : JSON.stringify(body),
        });
    }
    catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError')
            throw error;
        throw new ApiError(0, null);
    }
    let payload = null;
    try {
        payload = await response.json();
    }
    catch {
        payload = null;
    }
    if (!response.ok)
        throw new ApiError(response.status, payload);
    return payload;
}
export const api = {
    reference: (signal) => call('GET', '/api/reference', undefined, signal),
    /** The cards for what the bar holds (#314, #315): a read; the bar is never saved. `first`: how
     * many come whole with the order (#376); 0, the count alone (#378). */
    cards: (bar, first, signal, showHidden = false) => call('POST', '/api/cards', { ...bar, first, show_hidden: showHidden }, signal),
    /** A later page of a load: the cards of these ids, against the same bar (#376). */
    cardsById: (bar, ids, signal, showHidden = false) => call('POST', '/api/cards/by-id', { bar, ids, show_hidden: showHidden }, signal),
    post: (id, signal) => call('GET', `/api/posts/${encodeURIComponent(id)}`, undefined, signal),
    session: () => call('GET', '/api/session'),
    signIn: (username, password) => call('POST', '/api/sign-in', { username, password }),
    signUp: (key, username, password) => call('POST', '/api/sign-up', { key, username, password }),
    signOut: () => call('POST', '/api/sign-out', {}),
    password: (current, next) => call('POST', '/api/password', { current, new: next }),
    profile: () => call('GET', '/api/profile'),
    /** The preferences page's save: the only place preferences are saved (#335). */
    saveProfile: (bar) => call('PUT', '/api/profile', bar),
    // Phase 4: linking Telegram from the preferences page (#453).
    telegram: () => call('GET', '/api/telegram'),
    /** A one-time code, shown once: the deep link to the bot, and the code to type. */
    telegramLink: () => call('POST', '/api/telegram/link', {}),
    telegramUnlink: () => call('DELETE', '/api/telegram', {}),
    // Build step 6 (3.7 (i)): a post no longer in a current card answers 409, refusal "gone".
    /** Opening a post marks its card viewed (#253). */
    markViewed: (id) => call('POST', `/api/viewed/${encodeURIComponent(id)}`, {}),
    unmarkViewed: (id) => call('DELETE', `/api/viewed/${encodeURIComponent(id)}`, {}),
    /** "הסתר" (#464, #468): the card's shown post; "בטל הסתרה": every post of the card. */
    hide: (id) => call('POST', `/api/hidden/${encodeURIComponent(id)}`, {}),
    unhide: (id) => call('DELETE', `/api/hidden/${encodeURIComponent(id)}`, {}),
    /** "המודעה משקרת": every publication of the card (#300). */
    flag: (id) => call('POST', `/api/flag/${encodeURIComponent(id)}`, {}),
    /** "סיווג שגוי": the shown post only (#300); `removed` false when the admin will handle it. */
    report: (id, fields, note) => call('POST', `/api/report/${encodeURIComponent(id)}`, { fields, note }),
};
