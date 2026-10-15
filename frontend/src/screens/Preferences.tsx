// The preferences page (PHASE_3.md 3.7 (e)(iii)): the only place preferences are saved (#335). At the
// top the profile's one sublet switch (#317); two tabs, "חדר בדירת שותפים" and "דירה שלמה" (#339),
// each with its on/off switch and "copy from the other option" (#272: every value but on/off; never
// the sqm range into the room option; the sublet switch is not copied). Sections as cards; each
// range two number boxes with a slider and "נקה" for "don't care"; each category its level. A
// summary and the live count "with these preferences: N posts" (#330 point 24); the save sticky at
// the right on a desktop, at the bottom on a phone; leaving with unsaved changes asks first.
import { useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../api'
import {
  OPTIONS,
  OPTION_NAMES,
  barOf,
  copyFromOther,
  optionSummary,
  other,
  refusalWords,
  sameBar,
  withOption,
  type Bar,
  type OptionName,
  type SearchOption,
} from '../bar'
import { MUST_HIDES, Switch } from '../components/controls'
import { AreasField, EntryField, FeaturesField, PriceField, RangeField, WomenField } from '../components/fields'
import { navigate, setLeaveGuard } from '../route'
import type { AreaGroup } from '../types'

interface Props {
  saved: Bar
  onSaved: (saved: Bar) => void
  groups: AreaGroup[]
  names: ReadonlyMap<number, string>
  today: string
}

type Saving = { state: 'idle' } | { state: 'saving' } | { state: 'saved' } | { state: 'failed'; words: string }

export function Preferences({ saved, onSaved, groups, names, today }: Props) {
  const [draft, setDraft] = useState<Bar>(saved)
  const [tab, setTab] = useState<OptionName>('room')
  const [count, setCount] = useState<number | null>(null)
  const [countProblem, setCountProblem] = useState<string | null>(null)
  const [saving, setSaving] = useState<Saving>({ state: 'idle' })
  const dirty = !sameBar(draft, saved)
  const dirtyRef = useRef(dirty)
  dirtyRef.current = dirty

  useEffect(() => {
    setLeaveGuard(() => dirtyRef.current)
    return () => setLeaveGuard(null)
  }, [])

  // The live count follows the draft, a moment after the last change.
  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      api
        .cards(draft, 0, controller.signal) // the count alone (#378)
        .then((list) => {
          setCount(list.count)
          setCountProblem(null)
        })
        .catch((error) => {
          if (error instanceof DOMException) return
          setCount(null)
          setCountProblem(
            error instanceof ApiError && error.status === 422 ? refusalWords(error.detail) : 'הספירה לא נטענה.',
          )
        })
    }, 350)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [draft])

  const edit = (next: Bar) => {
    setDraft(next)
    setSaving((current) => (current.state === 'saving' ? current : { state: 'idle' }))
  }
  const change = (name: OptionName) => (values: Partial<SearchOption>) => edit(withOption(draft, name, values))

  const save = async () => {
    setSaving({ state: 'saving' })
    try {
      const next = barOf(await api.saveProfile(draft))
      onSaved(next)
      setDraft(next)
      setSaving({ state: 'saved' })
    } catch (error) {
      const words =
        error instanceof ApiError && error.status === 422
          ? refusalWords(error.detail).replace('הסינון', 'ההעדפות')
          : 'לא נשמר. נסו שוב.'
      setSaving({ state: 'failed', words })
    }
  }

  const option = draft[tab]
  const saveRow = (
    <div className="saverow">
      <p className="livecount" aria-live="polite">
        {countProblem ?? (count === null ? 'סופר מודעות…' : `עם ההעדפות האלה: ${count} מודעות`)}
      </p>
      <button type="button" className="mainbtn" disabled={!dirty || saving.state === 'saving'} onClick={save}>
        {saving.state === 'saving' ? 'שומר…' : 'שמירת ההעדפות'}
      </button>
      <p className={saving.state === 'failed' ? 'savestate is-failed' : 'savestate'} role="status">
        {saving.state === 'saved' && !dirty && 'ההעדפות נשמרו.'}
        {saving.state === 'failed' && saving.words}
        {saving.state === 'idle' && dirty && 'יש שינויים שלא נשמרו.'}
      </p>
    </div>
  )

  return (
    <main className="shell prefs">
      <header className="prefs-head">
        <h1>ההעדפות שלי</h1>
        <p>הסינון בעמוד הראשי מתחיל מההעדפות האלה. שינוי בסינון שם לא משנה אותן: שומרים רק כאן.</p>
      </header>
      <div className="prefs-layout">
        <aside className="prefs-side" aria-label="סיכום ושמירה">
          <div className="pcard summary">
            <h2>סיכום</h2>
            {OPTIONS.map((name) => {
              const lines = optionSummary(draft[name], names, today)
              return (
                <div key={name} className="sum-kind">
                  <h3>
                    {OPTION_NAMES[name]}
                    {!draft[name].enabled && <span className="off-tag">כבוי</span>}
                  </h3>
                  {draft[name].enabled && (
                    <ul>
                      {lines.length ? lines.map((line) => <li key={line}>{line}</li>) : <li className="none">בלי סינון</li>}
                    </ul>
                  )}
                </div>
              )
            })}
            <p className="sum-sublet">{draft.include_sublets ? 'כולל סאבלטים' : 'בלי סאבלטים'}</p>
            <div className="side-save">{saveRow}</div>
          </div>
          <p className="side-link">
            <a
              href="/password"
              onClick={(event) => {
                event.preventDefault()
                navigate('/password')
              }}
            >
              שינוי סיסמה
            </a>
          </p>
        </aside>

        <div className="prefs-main">
          <section className="pcard">
            <Switch
              label="גם סאבלט"
              checked={draft.include_sublets}
              onChange={(include_sublets) => edit({ ...draft, include_sublets })}
              describedBy="sublet-line"
            />
            <p className="pline" id="sublet-line">
              סאבלטים מוצגים בחיפושים שהפעלת.
            </p>
          </section>

          <div className="tabs" role="tablist" aria-label="סוג החיפוש">
            {OPTIONS.map((name) => (
              <button
                key={name}
                type="button"
                role="tab"
                id={`tab-${name}`}
                aria-selected={tab === name}
                aria-controls="tab-panel"
                className={tab === name ? 'tab is-on' : 'tab'}
                onClick={() => setTab(name)}
              >
                {OPTION_NAMES[name]}
                {!draft[name].enabled && <span className="off-tag">כבוי</span>}
              </button>
            ))}
          </div>

          <div className="tabpanel" role="tabpanel" id="tab-panel" aria-labelledby={`tab-${tab}`}>
            <section className="pcard tabhead">
              <div className="tabhead-row">
                <Switch label="החיפוש הזה פעיל" checked={option.enabled} onChange={(enabled) => change(tab)({ enabled })} />
                <button type="button" className="barbtn" onClick={() => edit(copyFromOther(draft, tab))}>
                  העתקה מ{OPTION_NAMES[other(tab)]}
                </button>
              </div>
              <p className="pline">
                {option.enabled
                  ? `ההעתקה לוקחת את כל הערכים מ${OPTION_NAMES[other(tab)]}, מלבד ההפעלה` +
                    (tab === 'room' ? ' והגודל במ״ר, שאין בחיפוש חדר.' : '. הגודל במ״ר של דירה שלמה נשאר כמו שהוא.')
                  : 'החיפוש כבוי: הערכים נשמרים, אבל מודעות מהסוג הזה לא יוצגו.'}
              </p>
              <p className="pline">{MUST_HIDES}</p>
            </section>

            <section className="pcard">
              <AreasField option={option} groups={groups} names={names} onChange={change(tab)} />
            </section>
            <section className="pcard">
              <PriceField option={option} onChange={change(tab)} full />
            </section>
            <section className="pcard">
              <RangeField title="חדרים" scale="rooms" range={option.rooms} onChange={(rooms) => change(tab)({ rooms })} full />
            </section>
            <section className="pcard">
              <RangeField
                title="קומה"
                scale="floor"
                range={option.floor}
                onChange={(floor) => change(tab)({ floor })}
                hint="-1 מרתף, 0 קרקע"
                full
              />
            </section>
            {tab === 'whole_apartment' && (
              <section className="pcard">
                <RangeField
                  title="גודל (מ״ר)"
                  scale="size"
                  range={option.size_sqm}
                  onChange={(size_sqm) => change(tab)({ size_sqm })}
                  full
                />
              </section>
            )}
            <section className="pcard">
              <EntryField entry={option.entry_date} today={today} onChange={(entry_date) => change(tab)({ entry_date })} />
            </section>
            <section className="pcard">
              <FeaturesField option={option} onChange={change(tab)} tiles />
            </section>
            <section className="pcard">
              <WomenField option={option} onChange={change(tab)} />
            </section>
          </div>
        </div>
      </div>
      <div className="phone-save">{saveRow}</div>
    </main>
  )
}
