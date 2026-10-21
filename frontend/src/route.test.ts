import { describe, expect, it } from 'vitest'
import { ADMIN_PAGES, ADMIN_SECTIONS, adminPath, parseRoute, sectionOf } from './route'

describe('the admin sections (#483)', () => {
  it('holds every page exactly once, in three sections', () => {
    const pages = ADMIN_SECTIONS.flatMap((section) => section.pages)
    expect(ADMIN_SECTIONS.map((section) => section.name)).toEqual(['posts', 'analysis', 'system'])
    expect([...pages].sort()).toEqual([...ADMIN_PAGES].sort())
  })

  it('puts a page, and a post, in its section', () => {
    expect(sectionOf('archive').name).toBe('posts')
    expect(sectionOf('post').name).toBe('posts')
    expect(sectionOf('analysis').name).toBe('analysis')
    expect(sectionOf('schedule').name).toBe('system')
  })

  it('gives the placeholder page its own address', () => {
    expect(adminPath('analysis')).toBe('/admin/analysis')
    expect(parseRoute('/admin/analysis')).toEqual({ name: 'admin', page: 'analysis' })
  })
})
