import { gzipSync } from 'node:zlib'
import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const dist = resolve(root, 'dist')
const manifestPath = resolve(dist, '.vite', 'manifest.json')
const outputFlag = process.argv.indexOf('--output')
const outputPath = outputFlag >= 0
  ? resolve(root, process.argv[outputFlag + 1])
  : resolve(root, 'artifacts', 'frontend-bundle-report.json')

const featureSources = {
  settings: 'src/components/modals/SettingsModal.vue',
  code: 'src/components/analysis/CodeTab.vue',
  terminal: 'src/components/analysis/TerminalTab.vue',
  table: 'src/components/analysis/TableTab.vue',
  figure: 'src/components/analysis/FigureTab.vue',
  other: 'src/components/analysis/OutputTab.vue',
}

function filesUnder(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    return entry.isDirectory() ? filesUnder(path) : [path]
  })
}

function fileSize(path) {
  const content = readFileSync(path)
  return {
    rawBytes: content.byteLength,
    gzipBytes: /\.(?:css|html|js|json|svg)$/.test(path) ? gzipSync(content).byteLength : null,
  }
}

function assetRecord(path) {
  return {
    file: relative(dist, path).replaceAll('\\', '/'),
    ...fileSize(path),
  }
}

function collectManifestFiles(manifest, key, seen = new Set()) {
  if (!key || seen.has(key) || !manifest[key]) return seen
  seen.add(key)
  for (const imported of manifest[key].imports || []) collectManifestFiles(manifest, imported, seen)
  return seen
}

function emittedFilesForKeys(manifest, keys) {
  const files = new Set()
  for (const key of keys) {
    const item = manifest[key]
    if (!item) continue
    if (item.file) files.add(item.file)
    for (const css of item.css || []) files.add(css)
    for (const asset of item.assets || []) files.add(asset)
  }
  return files
}

function summarizeFiles(files) {
  const records = [...files]
    .filter((file) => statSync(resolve(dist, file)).isFile())
    .map((file) => assetRecord(resolve(dist, file)))
    .sort((left, right) => right.rawBytes - left.rawBytes)
  return {
    rawBytes: records.reduce((total, item) => total + item.rawBytes, 0),
    gzipBytes: records.reduce((total, item) => total + (item.gzipBytes || 0), 0),
    files: records,
  }
}

function packageDuplicates() {
  const lock = JSON.parse(readFileSync(resolve(root, 'package-lock.json'), 'utf8'))
  const versions = new Map()
  for (const [packagePath, item] of Object.entries(lock.packages || {})) {
    if (!packagePath || !item?.version || !packagePath.includes('node_modules/')) continue
    const name = packagePath.slice(packagePath.lastIndexOf('node_modules/') + 'node_modules/'.length)
    const existing = versions.get(name) || new Set()
    existing.add(item.version)
    versions.set(name, existing)
  }
  return [...versions.entries()]
    .filter(([, values]) => values.size > 1)
    .map(([name, values]) => ({ name, versions: [...values].sort() }))
    .sort((left, right) => left.name.localeCompare(right.name))
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
const entryKey = Object.keys(manifest).find((key) => manifest[key].isEntry)
if (!entryKey) throw new Error('Vite manifest does not contain an application entry')

const initialKeys = collectManifestFiles(manifest, entryKey)
const initialFiles = emittedFilesForKeys(manifest, initialKeys)
initialFiles.add('index.html')

const features = Object.fromEntries(Object.entries(featureSources).map(([name, source]) => {
  const key = Object.keys(manifest).find((candidate) => candidate === source || manifest[candidate].src === source)
  if (!key) {
    return [name, {
      source,
      bundledWithInitial: true,
      reason: 'No independent feature chunk was emitted.',
      incremental: { rawBytes: 0, gzipBytes: 0, files: [] },
    }]
  }
  const featureKeys = collectManifestFiles(manifest, key)
  const featureFiles = emittedFilesForKeys(manifest, featureKeys)
  const incrementalFiles = new Set([...featureFiles].filter((file) => !initialFiles.has(file)))
  return [name, {
    source,
    bundledWithInitial: initialKeys.has(key),
    incremental: summarizeFiles(incrementalFiles),
  }]
}))

const importers = new Map()
for (const [key, item] of Object.entries(manifest)) {
  for (const imported of item.imports || []) {
    const consumers = importers.get(imported) || []
    consumers.push(key)
    importers.set(imported, consumers)
  }
}

const report = {
  schemaVersion: 1,
  generatedAt: new Date().toISOString(),
  build: {
    entry: entryKey,
    emitted: filesUnder(dist)
      .filter((path) => !path.includes('/.vite/'))
      .map(assetRecord)
      .sort((left, right) => right.rawBytes - left.rawBytes),
    initial: summarizeFiles(initialFiles),
    features,
    sharedChunks: [...importers.entries()]
      .filter(([, importersForChunk]) => importersForChunk.length > 1)
      .map(([key, importersForChunk]) => ({
        key,
        file: manifest[key]?.file || '',
        importers: importersForChunk.sort(),
      }))
      .sort((left, right) => left.key.localeCompare(right.key)),
  },
  duplicatePackages: packageDuplicates(),
}

mkdirSync(dirname(outputPath), { recursive: true })
writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`)
console.log(`Bundle report written to ${relative(root, outputPath)}`)
console.log(`Initial payload: ${(report.build.initial.gzipBytes / 1024).toFixed(2)} KiB gzip`)
