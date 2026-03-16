import test from 'node:test'
import assert from 'node:assert/strict'

import { chooseTableSelectionAfterRefresh } from '../src/utils/tableSelection.js'

test('pending latest artifact overrides an older valid selection after refresh', () => {
  const selected = chooseTableSelectionAfterRefresh({
    currentSelectionId: 'artifact-old',
    availableArtifactIds: new Set(['artifact-old', 'artifact-new']),
    rememberedArtifactId: 'artifact-old',
    latestArtifactId: 'artifact-new',
    latestMemoryArtifactId: '',
    pendingAutoSelectArtifactId: 'artifact-new',
  })

  assert.equal(selected, 'artifact-new')
})

test('current selection is preserved when no newer artifact is pending', () => {
  const selected = chooseTableSelectionAfterRefresh({
    currentSelectionId: 'artifact-old',
    availableArtifactIds: new Set(['artifact-old', 'artifact-new']),
    rememberedArtifactId: 'artifact-old',
    latestArtifactId: 'artifact-new',
    latestMemoryArtifactId: '',
    pendingAutoSelectArtifactId: '',
  })

  assert.equal(selected, 'artifact-old')
})
