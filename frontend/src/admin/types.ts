// The admin's payloads as the page reads them (tlv_hunter/web/admin_rows.py, admin.py). A user is
// named by username only; no hash of any kind ever comes here.
import type { ListingFields, Phone, Publication } from '../types'

export type ListName = 'rejected' | 'pending' | 'archive' | 'flags'
export type Reason =
  | 'no_text'
  | 'no_images'
  | 'other_city'
  | 'seeking'
  | 'for_sale'
  | 'not_listing'
  | 'flagged'
  | 'misclassified'
export type ReportStatus = 'open' | 'left_out' | 'restored'
export type Mark = 'not_removed' | 'restore_unfinished'

export interface Flag {
  by: string
  at: string | null
  note: string | null
}

export interface StateWords {
  state: 'pending' | 'active' | 'rejected' | 'archived'
  state_words: string
  reason: Reason | null
  reason_words: string | null
}

export interface Row extends StateWords {
  id: string
  city: string | null
  posted_at: string
  last_published_at: string
  publications: number
  text: string | null
  permalink: string
  photo: string | null
  photo_count: number
  videos: string[]
  failures: number
  last_error: string | null
  flag: Flag | null
  listing: ListingFields | null
  corrected: string[]
  /** What a write from this row sends back (#391). */
  version: string
}

export interface RowsAnswer {
  generation: number
  count: number
  order: string[]
  rows: Row[]
  reasons?: Partial<Record<Reason, number>>
}

export interface RowsPage {
  generation: number
  rows: Row[]
  gone: string[]
}

export interface Summary {
  rejected: number
  rejected_by_reason: Partial<Record<Reason, number>>
  pending: number
  pending_failed: number
  archive: number
  flag_actions: number
  flagged_posts: number
  open_reports: number
  not_removed: number
  restore_unfinished: number
  corrections: number
  usable_keys: number
  users: number
}

export interface FieldRow {
  field: string
  label: string
  model: unknown
  seen: unknown
  corrected: boolean
}

export interface Report {
  report_id: string
  listing_id: string
  reporter: string
  reported_at: string
  fields: { field: string; label: string }[]
  note: string | null
  status: ReportStatus
  resolved_by: string | null
  resolved_at: string | null
}

export interface Correction {
  correction_id: string
  listing_id: string
  field: string
  label: string
  model_value: unknown
  corrected_value: unknown
  corrected_by: string
  corrected_at: string
  report_id: string | null
  removed_by: string | null
  removed_at: string | null
  post?: Row | null
}

export interface Detail {
  id: string
  canonical: boolean
  lifecycle: StateWords & {
    flag: Flag | null
    failures: number
    last_error: string | null
    last_published_at: string
    image_errors: string[]
  }
  text: string | null
  permalink: string
  posted_at: string
  photos: string[]
  videos: string[]
  phones: Phone[]
  publications: Publication[]
  listing: ListingFields | null
  fields: FieldRow[]
  classified: { model_name: string; prompt_version: string; classified_at: string } | null
  city: { name: string | null; source: 'correction' | 'native_location' | 'model' | null } | null
  corrections: Correction[]
  reports: Report[]
  marks: Mark[]
  restore_preview: StateWords | null
  /** What a write from the detail sends back (#391). */
  version: string
}

export interface RestoreResult {
  listing_id: string
  outcome: 'restored' | 'changed' | 'not_restorable'
  state: StateWords['state'] | null
}

export interface ReportEntry {
  listing_id: string
  post: Row | null
  reports: Report[]
  marks: Mark[]
}

export interface ReportsAnswer {
  status: ReportStatus
  count: number
  posts: number
  groups: { field: string; label: string; posts: ReportEntry[] }[]
}

export interface Key {
  key_id: string
  label: string
  created_at: string
  state: 'usable' | 'used' | 'cancelled'
  used_by: string | null
  used_at: string | null
  cancelled_at: string | null
}

export interface AdminUser {
  username: string
  created_at: string
  is_admin: boolean
  key_label: string | null
  disabled_at: string | null
  must_change_password: boolean
  failed_sign_ins: number
}
