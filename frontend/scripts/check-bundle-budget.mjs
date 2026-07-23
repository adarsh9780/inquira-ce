import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const report = JSON.parse(readFileSync(resolve(root, 'artifacts', 'frontend-bundle-report.json'), 'utf8'))
const warnings = []
const mainEntry = report.build.initial.files.find((item) => /assets\/index-[^/]+\.js$/.test(item.file))
const initialHeavyFeatures = ['plotly-charts', 'codemirror', 'xterm']

if (mainEntry && mainEntry.gzipBytes > 460 * 1024) {
  warnings.push(`main application chunk is ${(mainEntry.gzipBytes / 1024).toFixed(2)} KiB gzip (warning budget: 460 KiB)`)
}

for (const marker of initialHeavyFeatures) {
  const match = report.build.initial.files.find((item) => item.file.includes(marker))
  if (match) warnings.push(`${marker} is present in the initial application payload (${(match.gzipBytes / 1024).toFixed(2)} KiB gzip)`)
}

if (warnings.length === 0) {
  console.log('Bundle warning budgets pass.')
} else {
  console.warn('Bundle budget warnings:')
  for (const warning of warnings) console.warn(`- ${warning}`)
  console.warn('Warning-only mode is active while feature loading boundaries are being established.')
}
