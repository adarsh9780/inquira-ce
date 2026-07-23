import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { basename, extname, resolve } from 'node:path'
import test from 'node:test'

const repoRoot = resolve(process.cwd(), '..')
const thisTest = 'frontend/test/repositoryLegacyDesktopArtifacts.test.mjs'
const frontendBoundaryTest = 'frontend/test/wailsOnlyFrontendBoundary.test.mjs'
const allowedGuardFiles = new Set([thisTest, frontendBoundaryTest])
const textExtensions = new Set([
  '.css',
  '.go',
  '.html',
  '.js',
  '.json',
  '.mjs',
  '.py',
  '.toml',
  '.ts',
  '.tsx',
  '.vue',
  '.yaml',
  '.yml',
])

function repositoryFiles() {
  return execFileSync(
    'git',
    ['ls-files', '--cached', '--others', '--exclude-standard', '-z'],
    { cwd: repoRoot, encoding: 'utf8' },
  )
    .split('\0')
    .filter(Boolean)
    .filter((path) => existsSync(resolve(repoRoot, path)))
}

function isTextFile(path) {
  return textExtensions.has(extname(path).toLowerCase())
    || ['Dockerfile', 'Makefile'].includes(basename(path))
}

test('frontend contains no generated HTTP-client pipeline or old backend E2E contract', () => {
  const files = repositoryFiles()
  const retiredClientPathPatterns = [
    /^frontend\/openapi\.(?:json|ya?ml)$/i,
    /^frontend\/orval\.config\.[cm]?[jt]s$/i,
    /^frontend\/src\/services\/generatedApi\.[jt]s$/i,
    /^frontend\/src\/services\/contracts\/v1Api\.[jt]s$/i,
  ]
  const retainedClientFiles = files.filter((path) => (
    retiredClientPathPatterns.some((pattern) => pattern.test(path))
  ))

  const packageJson = JSON.parse(
    readFileSync(resolve(repoRoot, 'frontend/package.json'), 'utf8'),
  )
  const dependencies = {
    ...(packageJson.dependencies || {}),
    ...(packageJson.devDependencies || {}),
  }
  const retiredDependencies = Object.keys(dependencies).filter((name) => (
    name === 'axios'
    || name === 'orval'
    || name.startsWith('@orval/')
  ))
  const retiredScriptNames = new Set(['export-openapi', 'generate-client'])
  const retiredScripts = Object.entries(packageJson.scripts || {})
    .filter(([name, command]) => (
      retiredScriptNames.has(name)
      || /\borval\b|\bopenapi\b/i.test(String(command || ''))
    ))
    .map(([name]) => name)

  const oldE2EReferences = []
  const e2eFiles = files.filter((path) => (
    path === 'frontend/playwright.config.js'
    || path.startsWith('frontend/e2e/')
  ))
  const oldE2EMarkers = [
    /\/api\/v1\//,
    /127\.0\.0\.1:8000/,
    /\bINQUIRA_(?:HOST|PORT|AUTH_PROVIDER|ALLOW_SCHEMA_BOOTSTRAP)\b/,
    /uv run --group dev python main\.py/,
    /path\.join\(repoRoot,\s*['"]backend['"]\)/,
  ]
  for (const path of e2eFiles) {
    if (!isTextFile(path)) continue
    const source = readFileSync(resolve(repoRoot, path), 'utf8')
    if (oldE2EMarkers.some((marker) => marker.test(source))) {
      oldE2EReferences.push(path)
    }
  }

  const retiredClientReferences = []
  const clientBoundaryFiles = files.filter((path) => (
    !allowedGuardFiles.has(path)
    && (
      path.startsWith('frontend/src/')
      || path.startsWith('frontend/test/')
      || path.startsWith('frontend/test-runtime/')
    )
  ))
  const retiredClientMarkers = [
    /\baxios\b/i,
    /\borval\b/i,
    /\bv1Api\b/,
    /\bgeneratedApi\b/,
    /\bopenapi\.json\b/i,
    /\/api\/v1\//,
  ]
  for (const path of clientBoundaryFiles) {
    if (!isTextFile(path)) continue
    const source = readFileSync(resolve(repoRoot, path), 'utf8')
    if (retiredClientMarkers.some((marker) => marker.test(source))) {
      retiredClientReferences.push(path)
    }
  }

  assert.deepEqual(
    retainedClientFiles,
    [],
    `retired generated-client files found:\n${retainedClientFiles.join('\n')}`,
  )
  assert.deepEqual(
    retiredDependencies,
    [],
    `retired frontend dependencies found:\n${retiredDependencies.join('\n')}`,
  )
  assert.deepEqual(
    retiredScripts,
    [],
    `retired frontend scripts found:\n${retiredScripts.join('\n')}`,
  )
  assert.deepEqual(
    retiredClientReferences,
    [],
    `retired generated-client references found:\n${retiredClientReferences.join('\n')}`,
  )
  assert.deepEqual(
    oldE2EReferences,
    [],
    `old backend E2E references found:\n${oldE2EReferences.join('\n')}`,
  )
})

test('frontend keeps retired workspace and artifact-limit compatibility paths removed', () => {
  const removedFrontendPaths = [
    'frontend/src/components/WorkspaceSwitcher.vue',
    'frontend/src/components/layout/sidebar/SidebarDatasets.vue',
    'frontend/src/components/layout/sidebar/SidebarWorkspaces.vue',
    'frontend/src/utils/chatBootstrap.js',
    'frontend/src/utils/datasetImport.js',
    'frontend/src/utils/sseParser.js',
  ]
  const retainedPaths = removedFrontendPaths.filter((path) => (
    existsSync(resolve(repoRoot, path))
  ))
  const guardedSources = [
    'frontend/src/components/modals/SettingsModal.vue',
    'frontend/src/components/layout/StatusBar.vue',
    'frontend/src/services/apiService.js',
  ]
  const retiredMarkers = [
    'workspace-operation-change',
    'activeWorkspaceOperation',
    'showArtifactUsageWarning',
    'artifactUsageWarningTitle',
    'subscribeWorkspaceArtifactUsage',
    'GetWorkspaceArtifactUsage',
  ]
  const retiredReferences = []

  for (const path of guardedSources) {
    const source = readFileSync(resolve(repoRoot, path), 'utf8')
    if (retiredMarkers.some((marker) => source.includes(marker))) {
      retiredReferences.push(path)
    }
  }

  assert.deepEqual(retainedPaths, [], `retired frontend files found:\n${retainedPaths.join('\n')}`)
  assert.deepEqual(
    retiredReferences,
    [],
    `retired workspace compatibility references found:\n${retiredReferences.join('\n')}`,
  )
})
