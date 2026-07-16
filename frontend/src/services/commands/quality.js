export const qualityCommands = [
  {
    name: 'nulls',
    usage: '/nulls <table> OR /nulls <table>.<col>',
    description: 'Null counts per column or for one column',
    category: 'quality',
  },
  {
    name: 'duplicates',
    usage: '/duplicates <table> [col1,col2,...]',
    description: 'Duplicate rows/groups by columns',
    category: 'quality',
  },
  {
    name: 'outliers',
    usage: '/outliers <table>.<col>',
    description: 'Rows outside 1.5*IQR bounds',
    category: 'quality',
  },
]
