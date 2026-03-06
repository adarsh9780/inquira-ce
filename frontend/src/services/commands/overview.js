export const overviewCommands = [
  {
    name: 'describe',
    usage: '/describe <table>',
    description: 'Profile columns using DuckDB SUMMARIZE',
    category: 'overview',
  },
  {
    name: 'info',
    usage: '/info <table>',
    description: 'Show table structure and row count',
    category: 'overview',
  },
  {
    name: 'shape',
    usage: '/shape <table>',
    description: 'Show row count and column count',
    category: 'overview',
  },
  {
    name: 'dtypes',
    usage: '/dtypes <table>',
    description: 'List columns and data types',
    category: 'overview',
  },
  {
    name: 'head',
    usage: '/head <table> [n]',
    description: 'Preview first N rows (default 10)',
    category: 'overview',
  },
  {
    name: 'tail',
    usage: '/tail <table> [n]',
    description: 'Preview last N rows (default 10)',
    category: 'overview',
  },
  {
    name: 'sample',
    usage: '/sample <table> [n]',
    description: 'Preview random N rows (default 10)',
    category: 'overview',
  },
]
