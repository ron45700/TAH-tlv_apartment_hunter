// The admin's API (tlv_hunter/web/admin.py), on the same origin and through the site's one `call`
// (api.ts): JSON, the cookie, `Origin` on every write. The rows come back as `cards` so the list's
// paging (paging.ts) pages them as it pages the cards.
import { call } from '../api';
const enc = encodeURIComponent;
export const adminApi = {
    summary: (signal) => call('GET', '/api/admin/summary', undefined, signal),
    rows: async (list, reason, first, signal) => {
        const answer = await call('POST', '/api/admin/posts', { list, reason, first }, signal);
        return { ...answer, cards: answer.rows };
    },
    rowsById: async (list, reason, ids) => {
        const page = await call('POST', '/api/admin/posts/by-id', { list, reason, ids });
        return { cards: page.rows, gone: page.gone };
    },
    post: (id, signal) => call('GET', `/api/admin/posts/${enc(id)}`, undefined, signal),
    reports: (status, signal) => call('GET', `/api/admin/reports?status=${status}`, undefined, signal),
    corrections: (inForce, signal) => call('GET', `/api/admin/corrections?in_force=${inForce}`, undefined, signal),
    // Build steps 4 and 5: each write sends the `version` the page showed (#391) and answers the
    // post's fresh detail; 409 "changed" when the post changed meanwhile.
    retry: (id, version) => call('POST', `/api/admin/retry/${enc(id)}`, { version }),
    restore: (posts) => call('POST', '/api/admin/restore', { posts }),
    leaveOut: (id, version) => call('POST', `/api/admin/leave-out/${enc(id)}`, { version }),
    applyReports: (id, version) => call('POST', `/api/admin/apply-reports/${enc(id)}`, { version }),
    correct: (id, field, correctedValue, reportId, version) => call('POST', '/api/admin/corrections', {
        listing_id: id,
        field,
        corrected_value: correctedValue,
        report_id: reportId,
        version,
    }),
    removeCorrection: (correctionId, version) => call('POST', `/api/admin/corrections/${enc(correctionId)}/remove`, { version }),
    keys: () => call('GET', '/api/admin/keys'),
    /** The key is in this answer only (#266). */
    issueKey: (label) => call('POST', '/api/admin/keys', { label }),
    cancelKey: (keyId) => call('POST', `/api/admin/keys/${enc(keyId)}/cancel`, {}),
    users: () => call('GET', '/api/admin/users'),
    resetPassword: (username, temporary) => call('POST', `/api/admin/users/${enc(username)}/password`, { temporary_password: temporary }),
    disable: (username) => call('POST', `/api/admin/users/${enc(username)}/disable`, {}),
    enable: (username) => call('POST', `/api/admin/users/${enc(username)}/enable`, {}),
    // Phase 5 (#61, #471): the scheduler reads the settings at every pass and starts the runs.
    schedule: (signal) => call('GET', '/api/admin/schedule', undefined, signal),
    saveSchedule: (body) => call('POST', '/api/admin/schedule', body),
    runNow: () => call('POST', '/api/admin/schedule/run-now', {}),
};
