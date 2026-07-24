import { readFileSync as readRawFileSync } from 'node:fs'

export function normalizeTypeScriptSource(source) {
  const normalizeScript = (script) => String(script)
    .replace(/\b(ref|reactive|computed)<(?:[^<>]|<[^<>]*>)+>/g, '$1')
    .replace(/:\s*(?:any|unknown|string|number|boolean|File|KeyboardEvent|PointerEvent|MouseEvent)(?=\s*[,)=;{])/g, '')
    .replace(/:\s*(?:Record<[^;\n=]+>|[A-Za-z_$][\w$]*(?:\[\])?)(?=\s*=)/g, '')
    .replace(/:\s*Promise<[^>\n]+>(?=\s*{)/g, '')
    .replace(/\s+as\s+(?:any|unknown)(?=[,).;\]}])/g, '')

  return String(source).replace(
    /(<script\b[^>]*>)([\s\S]*?)(<\/script>)/g,
    (_match, open, script, close) => `${open}${normalizeScript(script)}${close}`,
  )
}

export function readFileSync(path, options) {
  const source = readRawFileSync(path, options)
  return /\.vue$/.test(String(path))
    ? normalizeTypeScriptSource(source)
    : source
}
