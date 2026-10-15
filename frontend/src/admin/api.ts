// The admin's API (tlv_hunter/web/admin.py), on the same origin and through the site's one `call`
// (api.ts): JSON, the cookie, `Origin` on every write. The rows come back as `cards` so the list's
// paging (paging.ts) pages them as it pages the cards.
import { call } from '../api'
import type {
  AdminUser,
  Correction,
  Detail,
  Key,
  ListName,
  Reason,
  ReportStatus,
  ReportsAnswer,
  RowsAnswer,
  RowsPage,
  Summary,
} from './types'

const enc = encodeURIComponent

export const adminApi = {
  summary: (signal?: AbortSignal) => call<Summary>('GET', '/api/admin/summary', undefined, signal),
  rows: async (list: ListName, reason: Reason | null, first: number, signal?: AbortSignal) => {
    const answer = await call<RowsAnswer>('POST', '/api/admin/posts', { list, reason, first }, signal)
    return { ...answer, cards: answer.rows }
  },
  rowsById: async (list: ListName, reason: Reason | null, ids: string[]) => {
    const page = await call<RowsPage>('POST', '/api/admin/posts/by-id', { list, reason, ids })
    return { cards: page.rows, gone: page.gone }
  },
  post: (id: string, signal?: AbortSignal) => call<Detail>('GET', `/api/admin/posts/${enc(id)}`, undefined, signal),
  reports: (status: ReportStatus, signal?: AbortSignal) =>
    call<ReportsAnswer>('GET', `/api/admin/reports?status=${status}`, undefined, signal),
  corrections: (inForce: boolean, signal?: AbortSignal) =>
    call<{ in_force: boolean; corrections: Correction[] }>('GET', `/api/admin/corrections?in_force=${inForce}`, undefined, signal),
  keys: () => call<{ keys: Key[] }>('GET', '/api/admin/keys'),
  /** The key is in this answer only (#266). */
  issueKey: (label: string) => call<Key & { key: string }>('POST', '/api/admin/keys', { label }),
  cancelKey: (keyId: string) => call<Key>('POST', `/api/admin/keys/${enc(keyId)}/cancel`, {}),
  users: () => call<{ users: AdminUser[] }>('GET', '/api/admin/users'),
  resetPassword: (username: string, temporary: string) =>
    call<AdminUser>('POST', `/api/admin/users/${enc(username)}/password`, { temporary_password: temporary }),
  disable: (username: string) => call<AdminUser>('POST', `/api/admin/users/${enc(username)}/disable`, {}),
  enable: (username: string) => call<AdminUser>('POST', `/api/admin/users/${enc(username)}/enable`, {}),
}
