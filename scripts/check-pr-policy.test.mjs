import test from 'node:test'
import assert from 'node:assert/strict'

import { evaluatePolicy, isReviewablePath, parseNumstat } from './check-pr-policy.mjs'

const validBody = `## Summary

One focused change.

## Why

Explain the root cause.

## Out of scope

Unrelated cleanup.

## Reviewer guide

Review the policy first.

## Validation

- [x] Tests pass

## Risk and recovery

Revert this PR.
`

test('accepts a focused conventional pull request', () => {
  const result = evaluatePolicy({
    title: 'ci: enforce reviewable pull requests',
    body: validBody,
    files: parseNumstat('80\t20\tscripts/check-pr-policy.mjs\n20\t0\t.github/workflows/pr-policy.yml\n'),
  })

  assert.deepEqual(result.failures, [])
  assert.deepEqual(result.warnings, [])
  assert.equal(result.metrics.reviewableLines, 120)
})

test('rejects oversized changes without a documented override', () => {
  const result = evaluatePolicy({
    title: 'fix: oversized change',
    body: validBody,
    files: [{ path: 'frontend/src/large.ts', added: 401, deleted: 0 }],
  })

  assert.equal(result.failures.some((failure) => failure.includes('size-override')), true)
  assert.equal(result.warnings.length, 1)
})

test('allows a documented size override and ignores generated files', () => {
  const result = evaluatePolicy({
    title: 'fix: regenerate desktop assets',
    body: `${validBody}\n## Size override\n\nGenerated assets must change together.`,
    labels: ['size-override'],
    files: [
      { path: 'frontend/src/large.ts', added: 401, deleted: 0 },
      { path: 'frontend/package-lock.json', added: 900, deleted: 800 },
      { path: 'build/appicon.png', added: 0, deleted: 0, binary: true },
    ],
  })

  assert.deepEqual(result.failures, [])
  assert.equal(result.metrics.reviewableLines, 401)
  assert.equal(result.metrics.ignoredFiles, 2)
})

test('requires metadata and completed validation for ready PRs', () => {
  const result = evaluatePolicy({
    title: 'update things',
    body: '## Summary\n\nIncomplete.\n\n- [ ] Tests pass',
    draft: false,
  })

  assert.equal(result.failures.some((failure) => failure.includes('conventional PR title')), true)
  assert.equal(result.failures.some((failure) => failure.includes('validation checklist')), true)
  assert.equal(result.failures.some((failure) => failure.includes('## Why')), true)
})

test('classifies reviewable paths and binary numstat safely', () => {
  assert.equal(isReviewablePath('frontend/src/App.vue'), true)
  assert.equal(isReviewablePath('frontend/package-lock.json'), false)
  assert.equal(isReviewablePath('build/icon.ico'), false)
  assert.deepEqual(parseNumstat('-\t-\tbuild/icon.ico\n'), [
    { path: 'build/icon.ico', added: 0, deleted: 0, binary: true },
  ])
})
