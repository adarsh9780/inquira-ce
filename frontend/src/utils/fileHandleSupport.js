export function supportsPersistentFileHandles() {
  return (
    typeof window !== 'undefined' &&
    typeof window.showOpenFilePicker === 'function' &&
    typeof window.indexedDB !== 'undefined'
  )
}

export function isLikelyStaleHandleError(error) {
  const name = error?.name || ''
  const message = String(error?.message || '').toLowerCase()
  return (
    name === 'NotFoundError' ||
    name === 'TypeMismatchError' ||
    message.includes('not found') ||
    message.includes('no such file')
  )
}
