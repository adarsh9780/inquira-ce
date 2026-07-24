import MarkdownIt from 'markdown-it'
import markdownItKatexModule from '@vscode/markdown-it-katex'
import DOMPurify from 'dompurify'
import Prism from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-sql'

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.getAttribute('href')) {
    node.setAttribute('rel', 'noopener noreferrer')
    node.setAttribute('target', '_blank')
  }
})

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})
markdown.use(markdownItKatexModule)
const defaultLinkOpen = markdown.renderer.rules.link_open
markdown.renderer.rules.link_open = (tokens: any[], index: number, options: any, environment: any, self: any) => {
  tokens[index].attrSet('rel', 'noopener noreferrer')
  tokens[index].attrSet('target', '_blank')
  return defaultLinkOpen
    ? defaultLinkOpen(tokens, index, options, environment, self)
    : self.renderToken(tokens, index, options)
}

function resolveLanguage(value: unknown) {
  const normalized = String(value || '').trim().toLowerCase()
  return ['sql', 'sqlite', 'duckdb', 'postgres', 'postgresql'].includes(normalized) ? 'sql' : 'python'
}

markdown.renderer.rules.fence = (tokens: any[], index: number) => {
  const token = tokens[index]
  const language = resolveLanguage(String(token.info || '').split(/\s+/)[0])
  const rawCode = String(token.content || '')
  const grammar = Prism.languages[language]
  const highlighted = grammar
    ? Prism.highlight(rawCode, grammar, language)
    : markdown.utils.escapeHtml(rawCode)
  return [
    '<div class="chat-code-block">',
    '<div class="chat-code-header">',
    `<span>${language}</span>`,
    '<button type="button" class="chat-code-copy" aria-label="Copy code" title="Copy code">',
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">',
    '<rect x="9" y="9" width="13" height="13" rx="2"></rect>',
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>',
    '</svg></button></div>',
    `<pre class="chat-code-scroll"><code class="language-${language}">${highlighted}</code></pre>`,
    '</div>',
  ].join('')
}

export function renderMarkdown(content: unknown) {
  const normalized = String(content || '').replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n')
  if (!normalized) return ''
  return DOMPurify.sanitize(markdown.render(normalized), {
    ADD_TAGS: ['button', 'svg', 'rect', 'path'],
    ADD_ATTR: [
      'aria-hidden', 'aria-label', 'class', 'fill', 'stroke', 'stroke-width',
      'stroke-linecap', 'stroke-linejoin', 'title', 'type', 'viewBox', 'x', 'y',
      'width', 'height', 'rx', 'd', 'rel', 'target',
    ],
  })
}

export function renderCode(content: unknown) {
  const rawCode = String(content || '')
  if (!rawCode) return ''
  const grammar = Prism.languages.python
  const highlighted = grammar
    ? Prism.highlight(rawCode, grammar, 'python')
    : markdown.utils.escapeHtml(rawCode)
  return DOMPurify.sanitize(highlighted, {
    ALLOWED_TAGS: ['span'],
    ALLOWED_ATTR: ['class'],
  })
}
