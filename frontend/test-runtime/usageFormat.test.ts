import { describe, expect, it } from 'vitest'

import {
  formatTokenCount,
  formatUsageCompact,
  formatUsageTooltip,
  mergeUsageTotals,
  normalizeUsage,
} from '../src/utils/usageFormat'

describe('usage formatting', () => {
  it('normalizes and merges only provided non-negative usage values', () => {
    expect(normalizeUsage({ input_tokens: '12', output_tokens: 3, price_usd: -1 })).toEqual({
      input_tokens: 12,
      output_tokens: 3,
      cached_tokens: null,
      total_tokens: null,
      price_usd: null,
    })
    expect(mergeUsageTotals(
      { input_tokens: 10, total_tokens: 10 },
      { input_tokens: 5, output_tokens: 2, total_tokens: 7 },
    )).toEqual({
      input_tokens: 15,
      output_tokens: 2,
      cached_tokens: null,
      total_tokens: 17,
      price_usd: null,
    })
  })

  it('formats compact counts, usage summaries, and tooltips', () => {
    const usage = { input_tokens: 1_200, output_tokens: 25, price_usd: 0.00125 }

    expect(formatTokenCount(1_200)).toBe('1.2k')
    expect(formatUsageCompact(usage)).toBe('1.2k in · 25 out · $0.001250')
    expect(formatUsageTooltip(usage, { turn_count: 3 })).toContain('Turns: 3')
  })
})
