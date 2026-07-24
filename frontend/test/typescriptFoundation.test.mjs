import assert from 'node:assert/strict'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { relative, resolve } from 'node:path'
import test from 'node:test'

const frontendRoot = process.cwd()
const sourceRoot = resolve(frontendRoot, 'src')
function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name)
    return entry.isDirectory() ? sourceFiles(path) : [path]
  })
}

function sourcePath(path) {
  return relative(frontendRoot, path).replaceAll('\\', '/')
}

test('TypeScript is strict, exclusive for production source, and checked independently', () => {
  const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'))
  const tsconfig = JSON.parse(readFileSync(resolve(process.cwd(), 'tsconfig.json'), 'utf8'))

  assert.equal(packageJson.scripts.typecheck, 'vue-tsc --noEmit')
  assert.match(packageJson.scripts.check, /npm run typecheck/)
  assert.equal(tsconfig.compilerOptions.strict, true)
  assert.notEqual(tsconfig.compilerOptions.allowJs, true)
  assert.notEqual(tsconfig.compilerOptions.checkJs, true)
  assert.equal(tsconfig.compilerOptions.noEmit, true)
})

test('production source contains no standalone JavaScript', () => {
  const actual = sourceFiles(sourceRoot)
    .filter((path) => path.endsWith('.js'))
    .map(sourcePath)
    .sort()

  assert.deepEqual(actual, [])
})

test('every scripted Vue component uses TypeScript', () => {
  const actual = sourceFiles(sourceRoot)
    .filter((path) => path.endsWith('.vue'))
    .filter((path) => {
      const source = readFileSync(path, 'utf8')
      return /<script(?:\s|>)/.test(source)
        && !/<script[^>]*\blang=["']ts["']/.test(source)
    })
    .map(sourcePath)
    .sort()

  assert.deepEqual(actual, [])
})

test('shared domain types cover the current Wails application boundaries', () => {
  for (const file of [
    'api.ts',
    'artifact.ts',
    'conversation.ts',
    'execution.ts',
    'identifiers.ts',
    'native.ts',
    'preferences.ts',
    'workspace.ts',
  ]) {
    assert.equal(existsSync(resolve(process.cwd(), 'src/types', file)), true, `${file} is missing`)
  }
})

test('native invocations derive their arguments and results from the method map', () => {
  const nativeApi = readFileSync(resolve(process.cwd(), 'src/api/native.ts'), 'utf8')
  const nativeTypes = readFileSync(resolve(process.cwd(), 'src/types/native.ts'), 'utf8')

  assert.match(nativeApi, /Method extends NativeMethodName/)
  assert.match(nativeApi, /NativeArguments<Method>/)
  assert.match(nativeApi, /NativeResult<Method>/)
  assert.match(nativeTypes, /export interface NativeMethodMap/)
  assert.doesNotMatch(nativeApi, /invokeNative<T>/)
})

test('new domain stores must be TypeScript during the compatibility migration', () => {
  const stores = readdirSync(resolve(process.cwd(), 'src/stores'))
  const allowedLegacyStores = new Set()
  const unexpectedJavaScriptStores = stores.filter((file) => file.endsWith('.js') && !allowedLegacyStores.has(file))

  assert.deepEqual(unexpectedJavaScriptStores, [])
})
