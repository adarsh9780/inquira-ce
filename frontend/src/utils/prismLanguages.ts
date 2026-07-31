import type PrismType from 'prismjs'

export function registerPrismLanguages(Prism: typeof PrismType) {
  Prism.languages.python = {
    comment: {
      pattern: /(^|[^\\])#.*/,
      lookbehind: true,
      greedy: true,
    },
    'triple-quoted-string': {
      pattern: /(?:[rub]|br|rb)?("""|''')[\s\S]*?\1/i,
      greedy: true,
      alias: 'string',
    },
    string: {
      pattern: /(?:[rub]|br|rb)?("|')(?:\\.|(?!\1)[^\\\r\n])*\1/i,
      greedy: true,
    },
    function: {
      pattern: /((?:^|\s)def[ \t]+)[a-zA-Z_]\w*(?=\s*\()/g,
      lookbehind: true,
    },
    'class-name': {
      pattern: /(\bclass\s+)\w+/i,
      lookbehind: true,
    },
    decorator: {
      pattern: /(^[\t ]*)@\w+(?:\.\w+)*/m,
      lookbehind: true,
      alias: ['annotation', 'punctuation'],
    },
    keyword: /\b(?:and|as|assert|async|await|break|case|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|match|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b/,
    builtin: /\b(?:abs|all|any|bool|bytes|dict|enumerate|filter|float|format|frozenset|getattr|hasattr|int|isinstance|issubclass|iter|len|list|map|max|memoryview|min|next|object|open|print|property|range|repr|reversed|round|set|slice|sorted|str|sum|super|tuple|type|vars|zip)\b/,
    boolean: /\b(?:False|None|True)\b/,
    number: /\b0(?:b(?:_?[01])+|o(?:_?[0-7])+|x(?:_?[a-f0-9])+)\b|(?:\b\d+(?:_\d+)*(?:\.(?:\d+(?:_\d+)*)?)?|\B\.\d+(?:_\d+)*)(?:e[+-]?\d+(?:_\d+)*)?j?(?!\w)/i,
    operator: /[-+%=]=?|!=|:=|\*\*?=?|\/\/?=?|<[<=>]?|>[=>]?|[&|^~]/,
    punctuation: /[{}[\];(),.:]/,
  }
  Prism.languages.py = Prism.languages.python

  Prism.languages.sql = {
    comment: {
      pattern: /(^|[^\\])(?:\/\*[\s\S]*?\*\/|(?:--|\/\/|#).*)/,
      lookbehind: true,
    },
    variable: [/@(["'`])(?:\\[\s\S]|(?!\1)[^\\])+\1/, /@[\w.$]+/],
    string: {
      pattern: /(^|[^@\\])("|')(?:\\[\s\S]|(?!\2)[^\\]|\2\2)*\2/,
      greedy: true,
      lookbehind: true,
    },
    function: /\b(?:AVG|COALESCE|COUNT|FIRST|FORMAT|LAST|LCASE|LEN|MAX|MID|MIN|MOD|NOW|ROUND|SUM|UCASE)(?=\s*\()/i,
    keyword: /\b(?:ADD|ALL|ALTER|ANALYZE|AND|AS|ASC|BEGIN|BETWEEN|BY|CASE|CAST|CHECK|COLUMN|COMMIT|CONSTRAINT|CREATE|CROSS|CURRENT_DATE|CURRENT_TIME|CURRENT_TIMESTAMP|DATABASE|DELETE|DESC|DESCRIBE|DISTINCT|DROP|ELSE|END|EXCEPT|EXISTS|EXPLAIN|FALSE|FETCH|FOREIGN|FROM|FULL|GROUP|HAVING|IF|ILIKE|IN|INDEX|INNER|INSERT|INTERSECT|INTO|IS|JOIN|LEFT|LIKE|LIMIT|NATURAL|NOT|NULL|OFFSET|ON|OR|ORDER|OUTER|OVER|PARTITION|PRIMARY|REFERENCES|RETURNING|RIGHT|ROLLBACK|ROW|SCHEMA|SELECT|SET|SHOW|TABLE|THEN|TRANSACTION|TRIGGER|TRUE|TRUNCATE|UNION|UNIQUE|UPDATE|USING|VALUES|VIEW|WHEN|WHERE|WINDOW|WITH)\b/i,
    boolean: /\b(?:FALSE|NULL|TRUE)\b/i,
    number: /\b0x[\da-f]+\b|\b\d+(?:\.\d*)?|\B\.\d+\b/i,
    operator: /[-+*\/=%^~]|&&?|\|\|?|!=?|<(?:=>?|<|>)?|>[>=]?|\b(?:AND|BETWEEN|ILIKE|IN|IS|LIKE|NOT|OR)\b/i,
    punctuation: /[;[\]()`,.]/,
  }
}
