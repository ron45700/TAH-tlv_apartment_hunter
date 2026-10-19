// The admin's pages (PHASE_3.md 3.8 (a), (c)): a rail of the lists with their counts at the right
// (on a phone, a strip of tabs under the header), and the page beside it. The admin only: a user who
// is not the admin reads that the pages are the admin's. The rail's counts come from
// /api/admin/summary, asked again when the page changes.
import type { ReactNode } from 'react'
import { adminApi } from '../../admin/api'
import type { Summary } from '../../admin/types'
import { REASON_FAMILY, REASON_NAMES, REASON_ORDER } from '../../admin/words'
import { ADMIN_PAGES, adminPath, type AdminPage } from '../../route'
import type { AreaGroup, SessionUser } from '../../types'
import { Keys, Users } from './Accounts'
import { AdminPost } from './AdminPost'
import { PostRows } from './PostRows'
import { Corrections, Reports } from './Reports'
import { Schedule } from './Schedule'
import { Link, useLoad } from './ui'

type ListedPage = (typeof ADMIN_PAGES)[number]

const TITLES: Record<ListedPage, string> = {
  overview: 'סקירה',
  rejected: 'נדחו',
  pending: 'ממתינות לסיווג',
  flags: 'סומנו כמשקרות',
  reports: 'דיווחים',
  corrections: 'תיקונים',
  archive: 'ארכיון',
  keys: 'קודי הזמנה',
  users: 'משתמשים',
  schedule: 'תזמון',
}

function railCount(page: ListedPage, summary: Summary | null): number | null {
  if (!summary) return null
  const counts: Partial<Record<ListedPage, number>> = {
    rejected: summary.rejected,
    pending: summary.pending,
    flags: summary.flag_actions,
    reports: summary.open_reports,
    corrections: summary.corrections,
    archive: summary.archive,
    keys: summary.usable_keys,
    users: summary.users,
  }
  return counts[page] ?? null
}

interface Props {
  user: SessionUser | null | undefined
  page: AdminPage
  id?: string
  names: ReadonlyMap<number, string>
  groups: AreaGroup[]
  now: Date
}

export function Admin({ user, page, id, names, groups, now }: Props) {
  if (user === undefined) {
    return (
      <main className="shell adm-solo">
        <p className="adm-empty">טוען…</p>
      </main>
    )
  }
  if (!user?.is_admin) {
    return (
      <main className="shell adm-solo">
        <p className="adm-empty">
          הדפים האלה למנהל בלבד. <Link to="/">לרשימת המודעות</Link>
        </p>
      </main>
    )
  }
  return <Desk page={page} id={id} names={names} groups={groups} now={now} />
}

function Desk({ page, id, names, groups, now }: Omit<Props, 'user'>) {
  const [summary, recount] = useLoad((signal) => adminApi.summary(signal), `${page}:${id ?? ''}`)
  const counts = summary.state === 'ready' ? summary.data : null
  const current: ListedPage = page === 'post' ? 'overview' : page
  return (
    <div className="shell adm">
      <nav className="rail" aria-label="דפי המנהל">
        <ul>
          {ADMIN_PAGES.map((name) => {
            const count = railCount(name, counts)
            const on = page !== 'post' && name === current
            return (
              <li key={name}>
                <Link to={adminPath(name)} className={`rail-link${on ? ' is-on' : ''}`} current={on}>
                  <span>{TITLES[name]}</span>
                  {count !== null && <span className="rail-count">{count}</span>}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
      <main className="adm-main">
        {page === 'post' && id ? (
          <>
            <Head title="מודעה">
              <button type="button" className="linkbtn" onClick={() => history.back()}>
                חזרה
              </button>
            </Head>
            <AdminPost id={id} names={names} groups={groups} now={now} />
          </>
        ) : (
          <>
            <Head title={TITLES[current]} />
            {current === 'overview' && <Overview summary={counts} />}
            {(current === 'rejected' || current === 'pending' || current === 'archive' || current === 'flags') && (
              <PostRows key={current} list={current} now={now} onChanged={recount} />
            )}
            {current === 'reports' && <Reports now={now} />}
            {current === 'corrections' && <Corrections names={names} now={now} />}
            {current === 'keys' && <Keys onChanged={recount} />}
            {current === 'users' && <Users onChanged={recount} />}
            {current === 'schedule' && <Schedule now={now} />}
          </>
        )}
      </main>
    </div>
  )
}

function Head({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="adm-head">
      <h1>{title}</h1>
      {children}
    </div>
  )
}

interface Line {
  to: AdminPage
  text: string
  detail?: ReactNode
  /** A line that needs the admin; shown only when its count is not 0. */
  alert?: number
}

/** One line per list with its count (3.8 (c), "Overview"). */
function Overview({ summary }: { summary: Summary | null }) {
  if (!summary) return <p className="adm-empty">טוען…</p>
  const lines: Line[] = [
    { to: 'reports', text: `${summary.not_removed} דיווחים שהמודעה שלהם עדיין ברשימה`, alert: summary.not_removed },
    { to: 'reports', text: `${summary.restore_unfinished} שחזורים שלא הושלמו`, alert: summary.restore_unfinished },
    {
      to: 'rejected',
      text: `${summary.rejected} מודעות נדחו`,
      detail: (
        <span className="ov-reasons">
          {REASON_ORDER.filter((name) => summary.rejected_by_reason[name]).map((name) => (
            <span key={name} className={`rchip rchip-${REASON_FAMILY[name]}`}>
              {REASON_NAMES[name]} {summary.rejected_by_reason[name]}
            </span>
          ))}
        </span>
      ),
    },
    {
      to: 'pending',
      text: `${summary.pending} ממתינות לסיווג`,
      detail: summary.pending_failed > 0 ? `${summary.pending_failed} מהן נכשלו בסיווג` : undefined,
    },
    {
      to: 'flags',
      text: `${summary.flag_actions} סימונים כמשקרות`,
      detail: summary.flagged_posts ? `על ${summary.flagged_posts} פרסומים` : undefined,
    },
    { to: 'reports', text: `${summary.open_reports} דיווחים פתוחים על סיווג שגוי` },
    { to: 'corrections', text: `${summary.corrections} תיקונים בתוקף` },
    { to: 'archive', text: `${summary.archive} מודעות בארכיון` },
    { to: 'keys', text: `${summary.usable_keys} קודי הזמנה פנויים` },
    { to: 'users', text: `${summary.users} משתמשים` },
  ]
  return (
    <>
      <p className="adm-lead">
        עד שהאתר יוגש מהמאגר עצמו (שלב 3.9), כל מה שנעשה כאן נשמר רק בעותק המתוארך שהאתר מגיש, ונעלם בעותק הבא.
      </p>
      <ul className="ov">
        {lines
          .filter((line) => line.alert === undefined || line.alert > 0)
          .map((line) => (
            <li key={line.text} className={line.alert ? 'is-alert' : undefined}>
              <Link to={adminPath(line.to)} className="ov-link">
                {line.text}
              </Link>
              {line.detail && <span className="ov-detail">{line.detail}</span>}
            </li>
          ))}
      </ul>
    </>
  )
}
