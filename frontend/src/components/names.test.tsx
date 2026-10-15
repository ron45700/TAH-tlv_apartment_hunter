// Label in Name (WCAG 2.5.3, #374): a control's accessible name starts with the text it shows. The
// "i" is drawn by CSS, so its name is the tier's words alone; the logo's two words are separated;
// the user pill's name starts with the username. Rendered to static markup in Node (no DOM).
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'
import { InfoButton } from './InfoButton'

describe('Label in Name (#374)', () => {
  it('the "i" holds no text of its own: its name is the tier\'s words', () => {
    const html = renderToStaticMarkup(<InfoButton label="מתאים חלקית" />)
    expect(html).toContain('aria-label="מתאים חלקית"')
    expect(html).not.toMatch(/>i</)
  })

  it('the logo\'s visible words are "TLV Apartment Hunter", as its name starts', () => {
    const html = renderToStaticMarkup(<Header user={null} onSignOut={() => {}} />)
    expect(html).toContain('aria-label="TLV Apartment Hunter, לעמוד הראשי"')
    expect(html).toMatch(/TLV<\/span> <span class="w2">Apartment Hunter/)
  })

  it("the user pill's name starts with the username it shows", () => {
    const user = { username: 'dana', is_admin: false, must_change_password: false }
    const html = renderToStaticMarkup(<Header user={user} onSignOut={() => {}} />)
    expect(html).toContain('aria-label="dana, תפריט החשבון"')
    // the avatar's letter is drawn by CSS: no text before the username
    expect(html).toContain('data-letter="D"></span>')
  })
})
