import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const repositoryRoot = resolve(process.cwd(), '..')

test('desktop releases build only after a stable release is published', () => {
  const workflow = readFileSync(resolve(repositoryRoot, '.github/workflows/release.yml'), 'utf8')

  assert.match(workflow, /release:\n\s+types:\n\s+- published/)
  assert.doesNotMatch(workflow, /pull_request:/)
  assert.doesNotMatch(workflow.toLowerCase(), /playwright/)
  assert.match(workflow, /Require successful CI for the release commit/)
  assert.match(workflow, /macos-14/)
  assert.match(workflow, /windows-2025/)
  assert.match(workflow, /Build release frontend/)
  assert.match(workflow, /inquira-frontend-\$\{\{ needs\.guard\.outputs\.tag \}\}/)
  assert.match(workflow, /-platform darwin\/arm64 -trimpath -s/)
  assert.match(workflow, /-platform windows\/amd64 -trimpath -nsis -s/)
  assert.match(workflow, /Test macOS Go packages/)
  assert.match(workflow, /Test Windows Go packages/)
  assert.match(workflow, /ProgramFiles\(x86\).*NSIS.*makensis\.exe/)
  assert.match(workflow, /GITHUB_PATH/)
  assert.match(workflow, /makensis\.exe is unavailable after NSIS installation/)
})

test('release publication archives assets and changes the public pointer last', () => {
  const workflow = readFileSync(resolve(repositoryRoot, '.github/workflows/release.yml'), 'utf8')

  assert.match(workflow, /gh release upload/)
  assert.match(workflow, /cmd\/releasemanifest/)
  assert.match(workflow, /CLOUDFLARE_API_TOKEN/)
  assert.match(workflow, /SHA256SUMS\.txt/)

  const versionedUpload = workflow.indexOf('Publish versioned downloads to Cloudflare R2')
  const latestUpload = workflow.indexOf('Atomically publish the latest release pointer')
  const verification = workflow.indexOf('Verify public download publication')
  assert.ok(versionedUpload >= 0)
  assert.ok(latestUpload > versionedUpload)
  assert.ok(verification > latestUpload)
})

test('ordinary CI does not spend native runner minutes', () => {
  const workflow = readFileSync(resolve(repositoryRoot, '.github/workflows/ci.yml'), 'utf8')

  assert.doesNotMatch(workflow, /macos-/)
  assert.doesNotMatch(workflow, /windows-/)
  assert.doesNotMatch(workflow.toLowerCase(), /playwright/)
})
