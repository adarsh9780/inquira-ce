#!/usr/bin/env node

import { execFileSync } from 'node:child_process'
import { appendFileSync, readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const REQUIRED_SECTIONS = [
  'Summary',
  'Why',
  'Out of scope',
  'Reviewer guide',
  'Validation',
  'Risk and recovery',
]

const CONVENTIONAL_TITLE = /^(build|chore|ci|docs|feat|fix|perf|refactor|revert|test)(\([a-z0-9._/-]+\))?!?: .+/i
const IGNORED_REVIEW_PATHS = [
  /(^|\/)(package-lock\.json|uv\.lock|go\.sum)$/,
  /(^|\/)(dist|node_modules|vendor|wailsjs)\//,
  /(^|\/)[^/]+\.generated\.[^/]+$/,
  /\.(gif|ico|icns|jpe?g|pdf|png|ttf|woff2?|zip)$/i,
]

export function isReviewablePath(path) {
  return !IGNORED_REVIEW_PATHS.some((pattern) => pattern.test(path))
}

export function parseNumstat(output) {
  return String(output || '')
    .split('\n')
    .filter(Boolean)
    .map((line) => {
      const [added, deleted, ...pathParts] = line.split('\t')
      return {
        added: added === '-' ? 0 : Number(added || 0),
        deleted: deleted === '-' ? 0 : Number(deleted || 0),
        path: pathParts.join('\t'),
        binary: added === '-' || deleted === '-',
      }
    })
}

export function evaluatePolicy({
  title,
  body,
  draft = false,
  files = [],
}) {
  const failures = []
  const warnings = []
  const reviewableFiles = files.filter((file) => isReviewablePath(file.path))
  const ignoredFiles = files.filter((file) => !isReviewablePath(file.path))
  const reviewableLines = reviewableFiles.reduce((total, file) => total + file.added + file.deleted, 0)

  if (!CONVENTIONAL_TITLE.test(title)) {
    failures.push('Use a conventional PR title such as `fix: close dropdowns on Escape`.')
  }

  for (const section of REQUIRED_SECTIONS) {
    const heading = new RegExp(`^## ${section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`, 'im')
    if (!heading.test(body)) failures.push(`Add the required \`## ${section}\` section.`)
  }

  const uncheckedItems = body.match(/^- \[ \]/gm)?.length || 0
  if (uncheckedItems > 0) {
    const message = `Complete or explicitly mark all ${uncheckedItems} validation checklist item(s) as not applicable.`
    if (draft) warnings.push(message)
    else failures.push(message)
  }

  return {
    failures,
    warnings,
    metrics: {
      reviewableLines,
      reviewableFiles: reviewableFiles.length,
      ignoredFiles: ignoredFiles.length,
    },
  }
}

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(name)
  return index >= 0 ? process.argv[index + 1] : fallback
}

function renderSummary(result) {
  const { failures, warnings, metrics } = result
  return [
    '# PR policy',
    '',
    `- Reviewable lines: ${metrics.reviewableLines}`,
    `- Reviewable files: ${metrics.reviewableFiles}`,
    `- Generated, lock, or binary files excluded from size: ${metrics.ignoredFiles}`,
    '',
    failures.length ? '## Failures' : '## Failures\n\nNone.',
    ...failures.map((failure) => `- ${failure}`),
    '',
    warnings.length ? '## Warnings' : '## Warnings\n\nNone.',
    ...warnings.map((warning) => `- ${warning}`),
    '',
  ].join('\n')
}

function main() {
  const event = JSON.parse(readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'))
  const base = argumentValue('--base', `origin/${event.pull_request.base.ref}`)
  const head = argumentValue('--head', 'HEAD')
  const numstat = execFileSync('git', ['diff', '--numstat', '--find-renames', `${base}...${head}`], { encoding: 'utf8' })
  const result = evaluatePolicy({
    title: event.pull_request.title || '',
    body: event.pull_request.body || '',
    draft: Boolean(event.pull_request.draft),
    files: parseNumstat(numstat),
  })
  const summary = renderSummary(result)

  process.stdout.write(`${summary}\n`)
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, summary)
  if (result.failures.length > 0) process.exitCode = 1
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main()
