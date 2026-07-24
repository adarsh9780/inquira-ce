export function bytesToBase64(payload: unknown): string {
  const bytes = payload instanceof Uint8Array
    ? payload
    : new TextEncoder().encode(String(payload || ''))
  let binary = ''
  const chunkSize = 0x8000
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize))
  }
  return btoa(binary)
}
