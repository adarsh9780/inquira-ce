import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const ACTIVE_THEME_SURFACES = [
  'src/App.vue',
  'src/components/layout/UnifiedSidebar.vue',
  'src/components/layout/sidebar/SidebarWorkspaces.vue',
  'src/components/layout/sidebar/SidebarDatasets.vue',
  'src/components/chat/ChatInput.vue',
  'src/components/chat/ColumnSuggest.vue',
  'src/components/analysis/OutputTab.vue',
  'src/components/analysis/TableTab.vue',
  'src/components/analysis/TerminalTab.vue',
  'src/components/modals/AccountTab.vue',
  'src/components/modals/ApiTab.vue',
  'src/components/modals/DataTab.vue',
  'src/components/modals/tabs/AppearanceTab.vue',
  'src/components/modals/tabs/LLMSettingsTab.vue',
  'src/components/modals/tabs/WorkspaceTab.vue',
]

test('active dark-theme surfaces avoid light-only Tailwind palette utilities', () => {
  const lightOnlyUtility = /\b(?:bg|text|border|placeholder:text)-(?:white|black|red|green|blue|yellow|amber|slate|gray|zinc|neutral|stone|orange|purple|indigo|pink|emerald|cyan)(?:-\d+)?(?:\/\[[^\]]+\]|\/\d+)?\b/

  for (const relativePath of ACTIVE_THEME_SURFACES) {
    const source = readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
    assert.equal(lightOnlyUtility.test(source), false, relativePath)
  }
})
