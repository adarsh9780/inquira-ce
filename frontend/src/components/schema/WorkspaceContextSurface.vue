<template>
  <section class="relative z-10 mx-4 mt-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-sm" aria-labelledby="workspace-context-title">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <h3 id="workspace-context-title" class="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Workspace Context</h3>
        <div class="group relative inline-flex items-center">
          <button type="button" class="text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)] focus-visible:outline-none focus-visible:text-[var(--color-text-main)]" aria-describedby="workspace-context-help" aria-label="About workspace context">
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </button>
          <div id="workspace-context-help" role="tooltip" class="pointer-events-none absolute left-0 top-full z-30 mt-1 w-64 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-2.5 text-[12px] font-normal leading-normal text-[var(--color-text-main)] opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
            Shared across every dataset in this workspace for schema generation.
          </div>
        </div>
      </div>
      <button v-if="!isEditing" type="button" class="flex items-center gap-1 rounded px-2 py-0.5 text-[12px] font-medium text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/10 hover:brightness-110" @click="startEditing">
        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
        </svg>
        Edit
      </button>
    </div>

    <form v-if="isEditing" class="mt-3" @submit.prevent="save">
      <label class="sr-only" for="workspace-context-input">Workspace context</label>
      <textarea id="workspace-context-input" v-focus v-model="draft" rows="4" class="w-full resize-y rounded-lg border border-[var(--color-accent)] bg-[var(--color-base)] p-3 text-[14px] text-[var(--color-text-main)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20" placeholder="Example: Daily transaction-level sales data for retail stores. 'channel' means online vs in-store."></textarea>
      <p v-if="saveError" role="alert" class="mt-2 text-[12px] text-[var(--color-danger-text)]">{{ saveError }}</p>
      <div class="mt-3 flex justify-end gap-2">
        <button type="button" :disabled="isSaving" class="rounded-lg px-4 py-2 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] disabled:opacity-50" @click="cancelEditing">Cancel</button>
        <button type="submit" :disabled="isSaving" class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-[13px] font-semibold text-[var(--color-on-accent)] shadow-sm transition-all hover:brightness-95 disabled:opacity-50">{{ isSaving ? 'Saving…' : 'Save Context' }}</button>
      </div>
    </form>
    <div v-else class="prose mt-1.5 max-w-none text-[13px] leading-relaxed text-[var(--color-text-main)]">
      <div v-if="renderedContext" v-html="renderedContext"></div>
      <i v-else class="text-[var(--color-text-muted)]">Click edit to add shared workspace context...</i>
    </div>
  </section>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  saveContext: (context: string) => Promise<void>
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const vFocus = { mounted: (element: HTMLElement) => element.focus() }
const markdown = new MarkdownIt({ breaks: true, linkify: true })
const isEditing = ref(false)
const isSaving = ref(false)
const saveError = ref('')
const draft = ref('')

const renderedContext = computed(() => {
  const context = props.modelValue.trim()
  return context ? markdown.render(context) : ''
})

watch(() => props.modelValue, (context) => {
  if (!isEditing.value) draft.value = context
})

function startEditing() {
  draft.value = props.modelValue
  saveError.value = ''
  isEditing.value = true
}

function cancelEditing() {
  draft.value = props.modelValue
  saveError.value = ''
  isEditing.value = false
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
    saveError.value = error instanceof Error ? error.message : 'Unable to save workspace context.'
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.prose :deep(p) { margin: 0; }
.prose :deep(p:last-child) { margin-bottom: 0; }
.prose :deep(strong) { font-weight: 600; }
.prose :deep(code) {
  border-radius: 0.25rem;
  background-color: color-mix(in srgb, var(--color-text-main) 8%, transparent);
  padding: 0.125em 0.375em;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
}
.prose :deep(ul), .prose :deep(ol) { margin: 0.35em 0; padding-left: 1.5em; }
.prose :deep(a) { color: var(--color-accent); text-decoration: underline; }
</style>
