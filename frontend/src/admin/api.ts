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
  RestoreResult,
  RowsPage,
  ScheduleAnswer,
  Summary,
} from './types'

/** A save of the schedule: Yad2's three are set together, or all null for no Yad2 runs (#529). */
export interface ScheduleSave {
  interval_minutes: number
  quiet_from: string
  quiet_until: string
  yad2_interval_minutes: number | null
  yad2_hours_from: string | null
  yad2_hours_until: string | null
  version: string
}

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
  // Build steps 4 and 5: each write sends the `version` the page showed (#391) and answers the
  // post's fresh detail; 409 "changed" when the post changed meanwhile.
  retry: (id: string, version: string) => call<Detail>('POST', `/api/admin/retry/${enc(id)}`, { version }),
  restore: (posts: { listing_id: string; version: string }[]) =>
    call<{ results: RestoreResult[] }>('POST', '/api/admin/restore', { posts }),
  leaveOut: (id: string, version: string) => call<Detail>('POST', `/api/admin/leave-out/${enc(id)}`, { version }),
  applyReports: (id: string, version: string) =>
    call<Detail>('POST', `/api/admin/apply-reports/${enc(id)}`, { version }),
  correct: (id: string, field: string, correctedValue: unknown, reportId: string, version: string) =>
    call<Detail>('POST', '/api/admin/corrections', {
      listing_id: id,
      field,
      corrected_value: correctedValue,
      report_id: reportId,
      version,
    }),
  removeCorrection: (correctionId: string, version: string) =>
    call<Detail>('POST', `/api/admin/corrections/${enc(correctionId)}/remove`, { version }),
  keys: () => call<{ keys: Key[] }>('GET', '/api/admin/keys'),
  /** The key is in this answer only (#266). */
  issueKey: (label: string) => call<Key & { key: string }>('POST', '/api/admin/keys', { label }),
  cancelKey: (keyId: string) => call<Key>('POST', `/api/admin/keys/${enc(keyId)}/cancel`, {}),
  users: () => call<{ users: AdminUser[] }>('GET', '/api/admin/users'),
  resetPassword: (username: string, temporary: string) =>
    call<AdminUser>('POST', `/api/admin/users/${enc(username)}/password`, { temporary_password: temporary }),
  disable: (username: string) => call<AdminUser>('POST', `/api/admin/users/${enc(username)}/disable`, {}),
  enable: (username: string) => call<AdminUser>('POST', `/api/admin/users/${enc(username)}/enable`, {}),
  // Phase 5 (#61, #471): the scheduler reads the settings at every pass and starts the runs.
  schedule: (signal?: AbortSignal) => call<ScheduleAnswer>('GET', '/api/admin/schedule', undefined, signal),
  saveSchedule: (body: ScheduleSave) => call<ScheduleAnswer>('POST', '/api/admin/schedule', body),
  runNow: () => call<ScheduleAnswer>('POST', '/api/admin/schedule/run-now', {}),
}
