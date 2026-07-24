import { describe, expect, it } from 'vitest'

import {
  dropdownOptionStyle,
  dropdownSurfaceStyle,
} from '../src/components/ui/dropdownShared'

describe('shared dropdown styles', () => {
  it('uses semantic defaults while accepting scoped overrides', () => {
    expect(dropdownSurfaceStyle()).toEqual({
      backgroundColor: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
    })
    expect(dropdownOptionStyle(true, { activeMix: 'red 10%' }).backgroundColor).toContain('red 10%')
    expect(dropdownOptionStyle(false).backgroundColor).toBe('transparent')
  })
})
