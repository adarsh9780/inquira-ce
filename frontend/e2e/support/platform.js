export const currentPlatform = process.platform

export function isMacOS() {
  return currentPlatform === 'darwin'
}

export function isWindows() {
  return currentPlatform === 'win32'
}

export function isLinux() {
  return currentPlatform === 'linux'
}
