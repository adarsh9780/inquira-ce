export const columnStatsCommands = [
  {
    name: 'mean',
    usage: '/mean <table>.<col>',
    description: 'Arithmetic mean of numeric column',
    category: 'column_stats',
  },
  {
    name: 'median',
    usage: '/median <table>.<col>',
    description: 'Median of numeric column',
    category: 'column_stats',
  },
  {
    name: 'mode',
    usage: '/mode <table>.<col>',
    description: 'Most frequent value in column',
    category: 'column_stats',
  },
  {
    name: 'std',
    usage: '/std <table>.<col>',
    description: 'Standard deviation',
    category: 'column_stats',
  },
  {
    name: 'sum',
    usage: '/sum <table>.<col>',
    description: 'Sum of values',
    category: 'column_stats',
  },
  {
    name: 'min',
    usage: '/min <table>.<col>',
    description: 'Minimum value',
    category: 'column_stats',
  },
  {
    name: 'max',
    usage: '/max <table>.<col>',
    description: 'Maximum value',
    category: 'column_stats',
  },
  {
    name: 'percentile',
    usage: '/percentile <table>.<col> [p]',
    description: 'Pth percentile (default 50)',
    category: 'column_stats',
  },
]
