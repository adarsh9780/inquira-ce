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

test('turn-specific remembered selection beats stale selection from a different turn', () => {
  const selected = chooseTableSelectionAfterRefresh({
    currentSelectionId: 'artifact-from-previous-turn',
    availableArtifactIds: new Set(['artifact-from-previous-turn', 'artifact-for-current-turn']),
    rememberedArtifactId: 'artifact-for-current-turn',
    latestArtifactId: '',
    latestMemoryArtifactId: '',
    pendingAutoSelectArtifactId: '',
  })

  assert.equal(selected, 'artifact-for-current-turn')
})
