import { expect, test } from 'vitest'

import { bytesToBase64 } from '../src/utils/exportEncoding'

test('native export encoding preserves large binary payloads without argument overflow', () => {
  const payload = new Uint8Array(200_000)
  for (let index = 0; index < payload.length; index += 1) payload[index] = index % 251
  const decoded = Buffer.from(bytesToBase64(payload), 'base64')

  expect(decoded).toEqual(Buffer.from(payload))
  expect(Buffer.from(bytesToBase64('Δ export'), 'base64').toString('utf8')).toBe('Δ export')
})
