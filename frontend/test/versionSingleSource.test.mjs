import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const repositoryRoot = resolve(process.cwd(), '..')
const read = (relative) => readFileSync(resolve(repositoryRoot, relative), 'utf8')

test('VERSION is the only tracked application version source', () => {
  const version = read('VERSION').trim()
  const frontendPackage = JSON.parse(read('frontend/package.json'))
  const frontendLock = JSON.parse(read('frontend/package-lock.json'))
  const wailsTemplate = JSON.parse(read('wails.template.json'))
  const ignore = read('.gitignore')

  assert.match(version, /^\d+\.\d+\.\d+$/)
  assert.equal(Object.hasOwn(frontendPackage, 'version'), false)
  assert.equal(Object.hasOwn(frontendLock, 'version'), false)
  assert.equal(Object.hasOwn(frontendLock.packages[''], 'version'), false)
  assert.equal(Object.hasOwn(wailsTemplate.info, 'productVersion'), false)
  assert.match(ignore, /^wails\.json$/m)
  assert.match(ignore, /^frontend\/package\.json\.md5$/m)

  const generatedFilesTracked = execFileSync(
    'git',
    ['ls-files', 'wails.json', 'frontend/package.json.md5'],
    { cwd: repositoryRoot, encoding: 'utf8' },
  ).trim()
  assert.equal(generatedFilesTracked, '')
})

test('build consumers read VERSION instead of independent fallbacks', () => {
  const makefile = read('Makefile')
  const vite = read('frontend/vite.config.js')
  const backend = read('version.go')
  const release = read('.github/workflows/release.yml')

  assert.match(makefile, /prepare-version:/)
  assert.match(makefile, /go run \.\/cmd\/prepareversion/)
  assert.match(makefile, /build: prepare-version prepare-uv/)
  assert.match(vite, /resolve\(frontendRoot, '\.\.', 'VERSION'\)/)
  assert.doesNotMatch(vite, /frontendPackage\.version|INQUIRA_BUILD_VERSION/)
  assert.match(backend, /go:embed VERSION/)
  assert.match(release, /does not match canonical VERSION/)
})
