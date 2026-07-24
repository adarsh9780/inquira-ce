import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const report = JSON.parse(readFileSync(resolve(root, 'artifacts', 'frontend-bundle-report.json'), 'utf8'))
const failures = []
const mainEntry = report.build.initial.files.find((item) => /assets\/index-[^/]+\.js$/.test(item.file))
const initialHeavyFeatures = ['plotly-charts', 'CodeTab-', 'NativeTerminalPane-']
const lazyFeatures = ['settings', 'code', 'terminal', 'figure']

if (!mainEntry) {
  failures.push('main application chunk could not be identified')
} else if (mainEntry.gzipBytes > 350 * 1024) {
  failures.push(`main application chunk is ${(mainEntry.gzipBytes / 1024).toFixed(2)} KiB gzip (budget: 350 KiB)`)
}

for (const marker of initialHeavyFeatures) {
  const match = report.build.initial.files.find((item) => item.file.includes(marker))
  if (match) failures.push(`${marker} is present in the initial application payload (${(match.gzipBytes / 1024).toFixed(2)} KiB gzip)`)
}

for (const feature of lazyFeatures) {
  if (report.build.features[feature]?.bundledWithInitial) {
    failures.push(`${feature} is bundled with the initial application path`)
  }
}

if (failures.length === 0) {
  console.log('Bundle budgets pass.')
} else {
  console.error('Bundle budget failures:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exitCode = 1
}
