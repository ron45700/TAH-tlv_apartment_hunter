// A signed-in user's actions on a post (PHASE_3.md 3.7 (c) rows 31–33, (i); build step 6): the
// report button's small menu (#328, #338), the confirmation before "המודעה משקרת" (#300), the "wrong
// classification" form (#254, #277: the fields as Hebrew labels, a note of up to 500 characters),
// and the notice that says, in words, what a write did (#330 point 21). Colour plus words only
// (#323): no glyphs.
import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from 'react'
import { ApiError } from '../api'
import type { ReportableField } from '../types'

export const NOTE_LIMIT = 500 // characters (#277)

export interface MenuItem {
  label: string
  onSelect: () => void
}

/** A button and its small menu: on the card the outlined "דיווח" (#338), opening upward; in the
 *  opened post the same; on a phone's opened post the top bar's "פעולות", opening downward. */
export function ActionMenu({
  label,
  items,
  className,
  placement = 'up',
}: {
  label: string
  items: MenuItem[]
  className: string
  placement?: 'up' | 'down'
}) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  useDismiss(open, setOpen, box, button)
  return (
    <div className="actmenu" ref={box}>
      <button
        ref={button}
        type="button"
        className={className}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {label}
      </button>
      {open && (
        <div className={`actmenu-list is-${placement}`} role="menu">
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                item.onSelect()
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/** Closes on a press outside `box` and on Escape (the focus back on `button`); Escape stops there,
 *  so an opened post behind the menu stays open. */
function useDismiss(
  open: boolean,
  setOpen: (open: boolean) => void,
  box: RefObject<HTMLElement | null>,
  button: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    if (!open) return
    const onDown = (event: PointerEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      setOpen(false)
      button.current?.focus()
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [open, setOpen, box, button])
}

/** A small modal over everything: the focus starts on the `data-initial` control; Escape and the
 *  backdrop cancel; the focus goes back where it was. */
function Modal({
  label,
  onCancel,
  children,
  wide = false,
}: {
  label: string
  onCancel: () => void
  children: ReactNode
  wide?: boolean
}) {
  const box = useRef<HTMLDivElement>(null)
  const cancel = useRef(onCancel)
  cancel.current = onCancel
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    // the heading stays in view: focusing a button at the foot must not scroll the box
    box.current?.querySelector<HTMLElement>('[data-initial]')?.focus({ preventScroll: true })
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.stopPropagation()
      cancel.current()
    }
    document.addEventListener('keydown', onKey, true)
    return () => {
      document.removeEventListener('keydown', onKey, true)
      previous?.focus?.()
    }
  }, [])
  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label={label}>
      <div className="modal-backdrop" onClick={onCancel} aria-hidden="true" />
      <div className={wide ? 'modal-box is-wide' : 'modal-box'} ref={box}>
        {children}
      </div>
    </div>
  )
}

/** The confirmation before a "lied" flag (3.7 (c) row 32). */
export function ConfirmFlag({
  busy,
  onConfirm,
  onCancel,
}: {
  busy: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <Modal label="סימון המודעה כמשקרת" onCancel={onCancel}>
      <h2 className="modal-title">לסמן שהמודעה משקרת?</h2>
      <p className="modal-text">
        המודעה תוסר מהרשימה של כל המשתמשים ותעבור לבדיקת המנהל. אם היא פורסמה כמה פעמים, כל הפרסומים שלה יסומנו.
      </p>
      <div className="modal-actions">
        <button type="button" className="btn danger" onClick={onConfirm} disabled={busy}>
          {busy ? 'מסמן…' : 'כן, המודעה משקרת'}
        </button>
        <button type="button" className="btn" onClick={onCancel} data-initial>
          ביטול
        </button>
      </div>
    </Modal>
  )
}

/** The "wrong classification" form (3.7 (c) row 33): one or more fields and an optional note. */
export function ReportForm({
  fields,
  onSend,
  onCancel,
}: {
  fields: ReportableField[]
  onSend: (fields: string[], note: string | null) => Promise<void>
  onCancel: () => void
}) {
  const [picked, setPicked] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const noteId = useId()
  const toggle = (field: string) =>
    setPicked((current) => (current.includes(field) ? current.filter((f) => f !== field) : [...current, field]))
  const send = () => {
    if (!picked.length) {
      setProblem('בחרו לפחות פרט אחד שסווג לא נכון.')
      return
    }
    setBusy(true)
    setProblem(null)
    const inOrder = fields.map((f) => f.field).filter((f) => picked.includes(f))
    onSend(inOrder, note.trim() ? note.trim() : null)
      .catch((error) => setProblem(reportProblem(error)))
      .finally(() => setBusy(false))
  }
  return (
    <Modal label="דיווח על סיווג שגוי" onCancel={onCancel} wide>
      <h2 className="modal-title">דיווח על סיווג שגוי</h2>
      <p className="modal-text">סמנו מה סווג לא נכון. המודעה תוסר מהרשימה עד שהמנהל יבדוק ויתקן אותה.</p>
      <fieldset className="report-fields">
        <legend>מה לא נכון?</legend>
        <div className="rtiles">
          {fields.map(({ field, label }) => (
            <label key={field} className={picked.includes(field) ? 'rtile is-picked' : 'rtile'}>
              <input
                type="checkbox"
                name={`report-${field}`}
                checked={picked.includes(field)}
                onChange={() => toggle(field)}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <div className="report-note">
        <label htmlFor={noteId}>הערה (לא חובה)</label>
        <textarea
          id={noteId}
          name="report-note"
          dir="auto"
          rows={3}
          maxLength={NOTE_LIMIT}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="למשל: המחיר במודעה הוא לחדר, לא לדירה"
        />
        <span className="report-count">
          {note.length}/{NOTE_LIMIT}
        </span>
      </div>
      {problem && (
        <p className="formerror" role="alert">
          {problem}
        </p>
      )}
      <div className="modal-actions">
        <button type="button" className="btn danger" onClick={send} disabled={busy}>
          {busy ? 'שולח…' : picked.length ? `שליחת הדיווח (${picked.length})` : 'שליחת הדיווח'}
        </button>
        <button type="button" className="btn" onClick={onCancel} data-initial>
          ביטול
        </button>
      </div>
    </Modal>
  )
}

export function reportProblem(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.refusal === 'already_reported') return 'כבר דיווחת על המודעה הזו, והדיווח עדיין פתוח אצל המנהל.'
    if (error.status === 422) return 'הדיווח לא תקין: בחרו פרט אחד לפחות, והערה של עד 500 תווים.'
    if (error.status === 401) return 'צריך להתחבר כדי לדווח.'
  }
  return 'הדיווח לא נשלח. בדקו את החיבור ונסו שוב.'
}

export interface Notice {
  text: string
  retry?: { label: string; run: () => void }
}

/** What a write did, in words, at the foot of the screen. It leaves by itself after a while,
 *  unless it offers a retry. */
export function NoticeBar({ notice, onDismiss }: { notice: Notice | null; onDismiss: () => void }) {
  useEffect(() => {
    if (!notice || notice.retry) return
    const timer = window.setTimeout(onDismiss, 7000)
    return () => window.clearTimeout(timer)
  }, [notice, onDismiss])
  return (
    <div className="notice-slot" role="status" aria-live="polite">
      {notice && (
        <div className="notice">
          <span className="notice-text">{notice.text}</span>
          {notice.retry && (
            <button type="button" className="notice-btn" onClick={notice.retry.run}>
              {notice.retry.label}
            </button>
          )}
          <button type="button" className="notice-btn is-quiet" onClick={onDismiss}>
            סגירה
          </button>
        </div>
      )}
    </div>
  )
}
