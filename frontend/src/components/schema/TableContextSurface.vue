<template>
  <section class="flex min-w-0 shrink-0 items-center gap-2 px-4 pb-2.5" aria-labelledby="table-context-title">
    <h3 id="table-context-title" class="shrink-0 text-[11px] font-semibold text-[var(--color-text-muted)]">Context</h3>
    <p v-if="modelValue.trim()" class="min-w-0 flex-1 truncate text-[12px] leading-5 text-[var(--color-text-sub)]">{{ modelValue }}</p>
    <p v-else class="min-w-0 flex-1 truncate text-[12px] leading-5 text-[var(--color-text-muted)]">Add business meaning, rules, and edge cases.</p>
    <button type="button" class="shrink-0 rounded px-1.5 py-1 text-[12px] font-medium text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]" @click="startEditing">
      {{ modelValue.trim() ? 'Edit context' : 'Add context' }}
    </button>

    <div
      v-if="isEditing"
      class="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-[1px]"
      data-table-context-backdrop
      @pointerdown.self="cancelEditing"
    >
      <aside class="flex h-full w-full max-w-[32rem] flex-col bg-[var(--color-surface)] shadow-2xl" role="dialog" aria-modal="true" :aria-label="`Edit context for ${tableName}`">
        <header class="flex items-start justify-between gap-4 border-b border-[var(--color-border)] px-5 py-4">
          <div class="min-w-0">
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Table context</p>
            <h4 class="mt-1 truncate font-mono text-[14px] font-semibold text-[var(--color-text-main)]">{{ tableName }}</h4>
          </div>
          <button type="button" class="flex h-8 w-8 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-base-muted)] hover:text-[var(--color-text-main)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]" aria-label="Close table context" :disabled="isSaving" @click="cancelEditing">
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>
          </button>
        </header>

        <form class="flex min-h-0 flex-1 flex-col p-5" @submit.prevent="save">
          <label for="table-context-input" class="text-[13px] font-medium text-[var(--color-text-main)]">Business meaning and query guidance</label>
          <p class="mt-1 text-[12px] leading-5 text-[var(--color-text-muted)]">This guidance is used whenever <span class="font-mono text-[var(--color-text-main)]">{{ tableName }}</span> is analyzed.</p>
          <textarea id="table-context-input" v-focus v-model="draft" maxlength="8000" class="mt-3 min-h-[16rem] flex-1 resize-none rounded-lg border border-[var(--color-border)] bg-[var(--color-base)] p-3 text-[14px] leading-6 text-[var(--color-text-main)] shadow-inner placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20" placeholder="Example: One row per completed order. Exclude test orders when reporting revenue."></textarea>
          <div class="mt-2 flex items-start justify-between gap-4">
            <p v-if="saveError" role="alert" class="text-[12px] text-[var(--color-danger-text)]">{{ saveError }}</p>
            <span v-else></span>
            <span class="shrink-0 text-[11px] tabular-nums text-[var(--color-text-muted)]">{{ draft.length.toLocaleString() }} / 8,000</span>
          </div>
          <div class="mt-4 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
            <button type="button" :disabled="isSaving" class="rounded-md px-3 py-1.5 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] disabled:opacity-50" @click="cancelEditing">Cancel</button>
            <button type="submit" :disabled="isSaving" class="btn-primary px-3 py-1.5 text-[13px]">{{ isSaving ? 'Saving…' : 'Save context' }}</button>
          </div>
        </form>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ modelValue: string; tableName: string; saveContext: (context: string) => Promise<void> }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const vFocus = { mounted: (element: HTMLElement) => element.focus() }
const isEditing = ref(false)
const isSaving = ref(false)
const saveError = ref('')
const draft = ref('')

watch(() => props.modelValue, (context) => { if (!isEditing.value) draft.value = context })

function startEditing() {
  draft.value = props.modelValue
  saveError.value = ''
  isEditing.value = true
}

function cancelEditing() {
  if (isSaving.value) return
  draft.value = props.modelValue
  saveError.value = ''
  isEditing.value = false
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape' && isEditing.value) cancelEditing()
}

async function save() {
  const context = draft.value.trim()
  isSaving.value = true
  saveError.value = ''
  try {
    await props.saveContext(context)
    emit('update:modelValue', context)
    isEditing.value = false
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : 'Unable to save table context.'
  } finally {
    isSaving.value = false
  }
}

onMounted(() => document.addEventListener('keydown', handleEscape))
onBeforeUnmount(() => document.removeEventListener('keydown', handleEscape))
</script>
