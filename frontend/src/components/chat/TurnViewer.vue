<template>
  <div class="flex h-full min-w-0 flex-col gap-3 overflow-hidden rounded-xl border p-3" style="background-color: var(--color-base); border-color: var(--color-border);">
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <button type="button" class="btn-icon" :disabled="!appStore.activeTurnRelations?.previous_turn" @click="appStore.goToPreviousTurn()" title="Previous turn">
          &lt;
        </button>
        <button type="button" class="btn-icon" :disabled="!appStore.activeTurnRelations?.next_turn" @click="appStore.goToNextTurn()" title="Next turn">
          &gt;
        </button>
        <select
          class="rounded-lg border px-2 py-1 text-sm"
          style="background-color: var(--color-surface); border-color: var(--color-border); color: var(--color-text-main);"
          :value="selectedChildTurnId"
          @change="handleBranchPick"
        >
          <option value="">Current branch</option>
          <option
            v-for="child in branchChildren"
            :key="child.id"
            :value="child.id"
          >
            {{ child.user_text || child.id }}
          </option>
        </select>
      </div>

      <div class="flex items-center gap-2">
        <span
          v-if="isFinalTurn"
          class="rounded-full border px-2 py-0.5 text-xs font-semibold"
          style="border-color: var(--color-border); color: var(--color-accent);"
        >
          Final Turn
        </span>
        <button type="button" class="btn-secondary text-sm" @click="appStore.markActiveTurnFinal()">
          Mark Final
        </button>
        <button type="button" class="btn-secondary text-sm" :disabled="!appStore.finalTurnId" @click="appStore.rerunSelectedFinalTurn()">
          Rerun Final
        </button>
      </div>
    </div>

    <div class="min-w-0 rounded-xl border p-3" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <p class="text-xs uppercase tracking-wide" style="color: var(--color-text-muted);">Question</p>
      <p class="mt-1 text-sm" style="color: var(--color-text-main);">{{ appStore.activeTurn?.user_text || 'No turn selected.' }}</p>
    </div>

    <div class="min-h-0 flex-1 overflow-auto rounded-xl border p-3" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <p class="text-xs uppercase tracking-wide" style="color: var(--color-text-muted);">Answer</p>
      <p class="mt-1 whitespace-pre-wrap text-sm" style="color: var(--color-text-main);">{{ appStore.activeTurn?.assistant_text || '' }}</p>

      <p class="mt-4 text-xs uppercase tracking-wide" style="color: var(--color-text-muted);">Code</p>
      <pre class="mt-1 overflow-auto rounded-lg p-3 text-xs" style="background-color: var(--color-base); color: var(--color-text-main);">{{ appStore.activeTurnCode || '# No code snapshot' }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../../stores/appStore'

const appStore = useAppStore()

const branchChildren = computed(() => Array.isArray(appStore.activeTurnRelations?.children) ? appStore.activeTurnRelations.children : [])
const selectedChildTurnId = computed(() => '')
const isFinalTurn = computed(() => String(appStore.finalTurnId || '') === String(appStore.activeTurnId || ''))

function handleBranchPick(event) {
  const value = String(event?.target?.value || '').trim()
  if (!value) return
  void appStore.selectBranchChildTurn(value)
}
</script>
