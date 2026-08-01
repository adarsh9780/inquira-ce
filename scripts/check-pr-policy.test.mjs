import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

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

test('allows large cohesive changes while still reporting review metrics', () => {
  const result = evaluatePolicy({
    title: 'feat: deliver cohesive workspace manager',
    body: validBody,
    files: Array.from({ length: 24 }, (_, index) => ({
      path: `frontend/src/workspace/part-${index}.ts`,
      added: 100,
      deleted: 25,
    })),
  })

  assert.deepEqual(result.failures, [])
  assert.deepEqual(result.warnings, [])
  assert.equal(result.metrics.reviewableLines, 3000)
  assert.equal(result.metrics.reviewableFiles, 24)
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

test('uses the same verified action pins as the main CI workflow', () => {
  const ciWorkflow = readFileSync(new URL('../.github/workflows/ci.yml', import.meta.url), 'utf8')
  const policyWorkflow = readFileSync(new URL('../.github/workflows/pr-policy.yml', import.meta.url), 'utf8')

  for (const action of ['actions/checkout', 'actions/setup-node']) {
    const pattern = new RegExp(`${action.replace('/', '\\/')}@([a-f0-9]{40})`)
    const ciPin = ciWorkflow.match(pattern)?.[1]
    const policyPin = policyWorkflow.match(pattern)?.[1]

    assert.ok(ciPin, `${action} must have a verified pin in ci.yml`)
    assert.equal(policyPin, ciPin, `${action} must reuse the verified CI pin`)
  }
})
