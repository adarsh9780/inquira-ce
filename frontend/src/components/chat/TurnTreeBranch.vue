<template>
  <div class="space-y-1">
    <div class="flex items-stretch gap-1.5">
      <button
        v-if="hasChildren"
        type="button"
        class="group/tree-line relative flex w-3 shrink-0 items-stretch justify-center focus:outline-none"
        :title="isCollapsed ? 'Expand replies' : 'Collapse replies'"
        @click.stop="toggleCollapsed"
      >
        <span class="absolute inset-x-1/2 top-0 bottom-0 w-px -translate-x-1/2 bg-[var(--color-border)] transition-colors group-hover/tree-line:bg-[var(--color-text-muted)]"></span>
        <span
          class="relative mt-2 inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border text-[9px] font-semibold transition-colors"
          style="border-color: var(--color-border); background-color: var(--color-base); color: var(--color-text-muted);"
        >
          {{ isCollapsed ? '+' : '−' }}
        </span>
      </button>
      <span v-else class="w-3 shrink-0"></span>

      <button
        type="button"
        class="group/node w-full rounded-md border px-2.5 py-1.5 text-left transition-colors focus:outline-none"
        :class="isCurrent ? 'border-[var(--color-border-hover)]' : 'border-[var(--color-border)]'"
        :style="cardStyle"
        @click="emit('select', node.id)"
        @contextmenu.prevent="openContextMenu"
      >
        <div class="flex items-start gap-2">
          <div class="min-w-0 flex-1">
            <p class="truncate text-[11px] font-medium leading-[1.15rem] text-[var(--color-text-main)]">
              {{ questionLine }}
            </p>
            <p class="mt-0.5 truncate text-[10px] leading-[0.95rem] text-[var(--color-text-muted)]">
              {{ answerLine }}
            </p>
          </div>
        </div>
      </button>
    </div>

    <div v-if="hasChildren && !isCollapsed" class="ml-1 border-l border-[var(--color-border)] pl-2 space-y-1">
      <TurnTreeBranch
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :current-turn-id="currentTurnId"
        :current-parent-turn-id="currentParentTurnId"
        :final-turn-id="finalTurnId"
        @select="emit('select', $event)"
        @mark-final="emit('mark-final', $event)"
        @open-context-menu="emit('open-context-menu', $event)"
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
  currentParentTurnId: {
    type: String,
    default: ''
  },
  finalTurnId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select', 'mark-final', 'open-context-menu'])

const isCollapsed = ref(false)

const hasChildren = computed(() => Array.isArray(props.node?.children) && props.node.children.length > 0)
const isCurrent = computed(() => String(props.currentTurnId || '').trim() === String(props.node?.id || '').trim())
const isCurrentParent = computed(() => String(props.currentParentTurnId || '').trim() === String(props.node?.id || '').trim())
const questionLine = computed(() => {
  const value = String(props.node?.user_text || '').trim()
  return value || `Turn ${props.node?.seq_no || ''}`.trim()
})
const answerLine = computed(() => {
  const value = String(props.node?.assistant_text || '').replace(/\s+/g, ' ').trim()
  return value || 'No response saved'
})
const cardStyle = computed(() => ({
  boxShadow: 'none',
  backgroundColor: isCurrent.value
    ? 'color-mix(in srgb, var(--color-accent) 10%, var(--color-base))'
    : (isCurrentParent.value
        ? 'color-mix(in srgb, var(--color-text-main) 4%, var(--color-base))'
        : 'transparent'),
}))

function toggleCollapsed() {
  isCollapsed.value = !isCollapsed.value
}

function openContextMenu(event) {
  emit('open-context-menu', {
    turnId: String(props.node?.id || '').trim(),
    x: Number(event?.clientX || 0),
    y: Number(event?.clientY || 0),
  })
}
</script>
