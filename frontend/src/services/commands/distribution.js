export const distributionCommands = [
  {
    name: 'value_counts',
    usage: '/value_counts <table>.<col> [n]',
    description: 'Top N value counts (default 20)',
    category: 'distribution',
  },
  {
    name: 'unique',
    usage: '/unique <table>.<col>',
    description: 'Distinct count with sample values',
    category: 'distribution',
  },
  {
    name: 'histogram',
    usage: '/histogram <table>.<col> [bins]',
    description: 'Bucketed distribution (default 10 bins)',
    category: 'distribution',
  },
  {
    name: 'corr',
    usage: '/corr <table>.<c1> <c2>',
    description: 'Pearson correlation between two columns',
    category: 'distribution',
  },
  {
    name: 'crosstab',
    usage: '/crosstab <table>.<c1> <c2>',
    description: 'Cross-tab style frequency counts',
    category: 'distribution',
  },
]
