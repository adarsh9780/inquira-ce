<template>
  <div class="space-y-1.5">
    <div class="flex items-stretch gap-2">
      <button
        v-if="hasChildren"
        type="button"
        class="group/tree-line relative flex w-4 shrink-0 items-stretch justify-center focus:outline-none"
        :title="isCollapsed ? 'Expand replies' : 'Collapse replies'"
        @click.stop="toggleCollapsed"
      >
        <span class="absolute inset-x-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-[var(--color-border)] transition-colors group-hover/tree-line:bg-[var(--color-text-muted)]"></span>
        <span
          class="relative mt-2 inline-flex h-4 w-4 items-center justify-center rounded-full border text-[10px] font-semibold transition-colors"
          style="border-color: var(--color-border); background-color: var(--color-base); color: var(--color-text-muted);"
        >
          {{ isCollapsed ? '+' : '−' }}
        </span>
      </button>
      <span v-else class="w-4 shrink-0"></span>

      <button
        type="button"
        class="group/node w-full rounded-lg border px-3 py-2 text-left transition-colors focus:outline-none"
        :class="isCurrent ? 'border-[var(--color-border-hover)]' : 'border-[var(--color-border)]'"
        :style="cardStyle"
        @click="emit('select', node.id)"
      >
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <p class="truncate text-[12px] font-medium leading-5 text-[var(--color-text-main)]">
              {{ questionLine }}
            </p>
            <p class="mt-0.5 truncate text-[11px] leading-5 text-[var(--color-text-muted)]">
              {{ answerLine }}
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-2 pl-2">
            <span
              v-if="isFinal"
              class="rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em]"
              style="border-color: var(--color-border); color: var(--color-accent);"
            >
              Final
            </span>
            <span
              v-if="isCurrent"
              class="rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em]"
              style="border-color: var(--color-border); color: var(--color-accent);"
            >
              Current
            </span>
            <button
              type="button"
              class="opacity-0 transition-opacity group-hover/node:opacity-100"
              title="Mark final"
              @click.stop="emit('mark-final', node.id)"
            >
              <span
                class="inline-flex rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em]"
                style="border-color: var(--color-border); color: var(--color-text-muted);"
              >
                Mark final
              </span>
            </button>
          </div>
        </div>
      </button>
    </div>

    <div v-if="hasChildren && !isCollapsed" class="ml-2 border-l border-[var(--color-border)] pl-3 space-y-1.5">
      <TurnTreeBranch
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :current-turn-id="currentTurnId"
        :final-turn-id="finalTurnId"
        @select="emit('select', $event)"
        @mark-final="emit('mark-final', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

defineOptions({
  name: 'TurnTreeBranch'
})

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  currentTurnId: {
    type: String,
    default: ''
  },
  finalTurnId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select', 'mark-final'])

const isCollapsed = ref(false)

const hasChildren = computed(() => Array.isArray(props.node?.children) && props.node.children.length > 0)
const isCurrent = computed(() => String(props.currentTurnId || '').trim() === String(props.node?.id || '').trim())
const isFinal = computed(() => String(props.finalTurnId || '').trim() === String(props.node?.id || '').trim())
const questionLine = computed(() => {
  const value = String(props.node?.user_text || '').trim()
  return value || `Turn ${props.node?.seq_no || ''}`.trim()
})
const answerLine = computed(() => {
  const value = String(props.node?.assistant_text || '').replace(/\s+/g, ' ').trim()
  return value || 'No response saved'
})
const cardStyle = computed(() => ({
  backgroundColor: isCurrent.value
    ? 'color-mix(in srgb, var(--color-accent) 6%, var(--color-base))'
    : 'transparent',
}))

function toggleCollapsed() {
  isCollapsed.value = !isCollapsed.value
}
</script>
