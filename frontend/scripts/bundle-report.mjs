import { gzipSync } from 'node:zlib'
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { dirname, isAbsolute, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const defaultDistRoot = resolve(frontendRoot, '../src/inquira/frontend/dist')
const defaultManifestPath = resolve(defaultDistRoot, '.vite/manifest.json')
const defaultOutputPath = resolve(frontendRoot, 'reports/bundle-report.json')
const defaultBudgetPath = resolve(frontendRoot, 'bundle-budgets.json')

export function collectManifestClosure(manifest, entryKey) {
  const visited = new Set()

  function visit(key) {
    if (!key || visited.has(key)) return
    const item = manifest[key]
    if (!item) return
    visited.add(key)
    for (const dependency of item.imports || []) visit(dependency)
  }

  visit(entryKey)
  return [...visited]
}

export function findManifestKey(manifest, matcher) {
  return Object.keys(manifest).find((key) => matcher(key, manifest[key])) || null
}

export async function assetSize(distRoot, relativePath) {
  const absolutePath = resolve(distRoot, relativePath)
  const contents = await readFile(absolutePath)
  const details = await stat(absolutePath)
  return {
    file: relativePath,
    rawBytes: details.size,
    gzipBytes: gzipSync(contents, { level: 9 }).length,
  }
}

async function summarizeClosure(manifest, distRoot, entryKey) {
  const keys = collectManifestClosure(manifest, entryKey)
  const files = new Set()

  for (const key of keys) {
    const item = manifest[key]
    if (item?.file) files.add(item.file)
    for (const cssFile of item?.css || []) files.add(cssFile)
  }

  const assets = await Promise.all([...files].sort().map((file) => assetSize(distRoot, file)))
  return {
    entryKey,
    rawBytes: assets.reduce((sum, item) => sum + item.rawBytes, 0),
    gzipBytes: assets.reduce((sum, item) => sum + item.gzipBytes, 0),
    assets,
  }
}

export async function buildBundleReport({
  manifestPath = defaultManifestPath,
  distRoot = defaultDistRoot,
} = {}) {
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
  const entryKey = findManifestKey(manifest, (_key, item) => item.isEntry)
  if (!entryKey) throw new Error('Vite manifest does not contain an application entry.')

  const featureMatchers = {
    table: (key) => key.endsWith('/TableTab.vue'),
    figure: (key) => key.endsWith('/FigureTab.vue'),
    output: (key) => key.endsWith('/OutputTab.vue'),
    runChart: (key) => key.endsWith('/RunChartOutput.vue'),
  }

  const features = {}
  for (const [name, matcher] of Object.entries(featureMatchers)) {
    const featureKey = findManifestKey(manifest, matcher)
    if (featureKey) features[name] = await summarizeClosure(manifest, distRoot, featureKey)
  }

  const chunks = {}
  for (const [key, item] of Object.entries(manifest)) {
    if (!item.file?.endsWith('.js')) continue
    chunks[key] = await assetSize(distRoot, item.file)
  }

  const plotlyKey = findManifestKey(
    manifest,
    (key, item) => key.includes('plotly-charts') || item.name === 'plotly-charts',
  )
  const mainEntry = await summarizeClosure(manifest, distRoot, entryKey)

  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    entry: mainEntry,
    entryFile: await assetSize(distRoot, manifest[entryKey].file),
    plotlyChunk: plotlyKey ? await assetSize(distRoot, manifest[plotlyKey].file) : null,
    features,
    chunks,
  }
}

export function evaluateBudgets(report, budgets) {
  const checks = [
    {
      name: 'entryFileGzipBytes',
      actual: report.entryFile.gzipBytes,
      limit: budgets.entryFileGzipBytes,
    },
    {
      name: 'initialClosureGzipBytes',
      actual: report.entry.gzipBytes,
      limit: budgets.initialClosureGzipBytes,
    },
    {
      name: 'plotlyChunkGzipBytes',
      actual: report.plotlyChunk?.gzipBytes || 0,
      limit: budgets.plotlyChunkGzipBytes,
    },
  ].filter((item) => Number.isFinite(item.limit))

  return checks.map((item) => ({
    ...item,
    passed: item.actual <= item.limit,
  }))
}

function parseArguments(argv) {
  const result = {
    check: false,
    outputPath: defaultOutputPath,
    budgetPath: defaultBudgetPath,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--check') result.check = true
    if (argument === '--output' && argv[index + 1]) result.outputPath = resolve(frontendRoot, argv[++index])
    if (argument === '--budgets' && argv[index + 1]) result.budgetPath = resolve(frontendRoot, argv[++index])
  }
  return result
}

async function main() {
  const options = parseArguments(process.argv.slice(2))
  const report = await buildBundleReport()
  await mkdir(dirname(options.outputPath), { recursive: true })
  await writeFile(options.outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')

  const kb = (bytes) => `${(bytes / 1024).toFixed(2)} KB`
  console.log(`Entry file: ${kb(report.entryFile.gzipBytes)} gzip`)
  console.log(`Initial closure: ${kb(report.entry.gzipBytes)} gzip`)
  console.log(`Plotly chunk: ${kb(report.plotlyChunk?.gzipBytes || 0)} gzip`)
  console.log(`Report: ${options.outputPath}`)

  if (!options.check) return

  const budgets = JSON.parse(await readFile(options.budgetPath, 'utf8'))
  const checks = evaluateBudgets(report, budgets)
  for (const check of checks) {
    console.log(
      `${check.passed ? 'PASS' : 'FAIL'} ${check.name}: ${kb(check.actual)} / ${kb(check.limit)}`,
    )
  }
  if (checks.some((check) => !check.passed)) process.exitCode = 1
}

if (isAbsolute(process.argv[1] || '') && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main()
}
