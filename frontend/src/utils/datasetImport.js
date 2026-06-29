import { filenameFromPath } from './pathUtils.js'

export const SUPPORTED_DATASET_EXTENSIONS = ['csv', 'tsv', 'parquet', 'json', 'xlsx', 'xls']
export const SUPPORTED_DATASET_EXTENSION_SET = new Set(
  SUPPORTED_DATASET_EXTENSIONS.map((extension) => `.${extension}`)
)

export function datasetPathExtension(pathValue) {
  const lowerPath = String(pathValue || '').trim().toLowerCase()
  if (!lowerPath.includes('.')) return ''
  return lowerPath.slice(lowerPath.lastIndexOf('.'))
}

export function filterSupportedDatasetPaths(paths) {
  return Array.from(paths || [])
    .map((pathValue) => String(pathValue || '').trim())
    .filter((pathValue) => pathValue && SUPPORTED_DATASET_EXTENSION_SET.has(datasetPathExtension(pathValue)))
}

export function getDroppedDatasetPaths(files) {
  return filterSupportedDatasetPaths(Array.from(files || []).map((file) => file?.path))
}

export function datasetImportLabel(paths) {
  const sourcePaths = Array.isArray(paths)
    ? paths.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (sourcePaths.length === 1) {
    return filenameFromPath(sourcePaths[0], 'Selected dataset')
  }
  return `${sourcePaths.length} selected files`
}
