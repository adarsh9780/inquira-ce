<template>
  <section class="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm" aria-labelledby="table-context-title">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h3 id="table-context-title" class="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Table context</h3>
        <p class="mt-1 text-[12px] leading-relaxed text-[var(--color-text-sub)]">Business meaning and query guidance used whenever <span class="font-mono font-semibold text-[var(--color-text-main)]">{{ tableName }}</span> is analyzed.</p>
      </div>
      <button v-if="!isEditing" type="button" class="shrink-0 rounded px-2 py-1 text-[12px] font-medium text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/10" @click="startEditing">Edit</button>
    </div>

    <form v-if="isEditing" class="mt-3" @submit.prevent="save">
      <label class="sr-only" for="table-context-input">Context for {{ tableName }}</label>
      <textarea id="table-context-input" v-focus v-model="draft" maxlength="8000" rows="4" class="w-full resize-y rounded-lg border border-[var(--color-accent)] bg-[var(--color-base)] p-3 text-[14px] leading-relaxed text-[var(--color-text-main)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20" placeholder="Example: One row per completed order. Exclude test orders when reporting revenue."></textarea>
      <div class="mt-1.5 flex items-start justify-between gap-4">
        <p v-if="saveError" role="alert" class="text-[12px] text-[var(--color-danger-text)]">{{ saveError }}</p>
        <span v-else></span>
        <span class="shrink-0 text-[11px] tabular-nums text-[var(--color-text-muted)]">{{ draft.length.toLocaleString() }} / 8,000</span>
      </div>
      <div class="mt-3 flex justify-end gap-2">
        <button type="button" :disabled="isSaving" class="rounded-lg px-4 py-2 text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-base-muted)] disabled:opacity-50" @click="cancelEditing">Cancel</button>
        <button type="submit" :disabled="isSaving" class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-[13px] font-semibold text-[var(--color-on-accent)] shadow-sm transition-all hover:brightness-95 disabled:opacity-50">{{ isSaving ? 'Saving…' : 'Save context' }}</button>
      </div>
    </form>
    <p v-else-if="modelValue.trim()" class="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-[var(--color-text-main)]">{{ modelValue }}</p>
    <p v-else class="mt-2 text-[13px] italic text-[var(--color-text-muted)]">Add table-specific definitions, rules, and edge cases.</p>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ modelValue: string; tableName: string; saveContext: (context: string) => Promise<void> }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const vFocus = { mounted: (element: HTMLElement) => element.focus() }
const isEditing = ref(false)
const isSaving = ref(false)
const saveError = ref('')
const draft = ref('')

watch(() => props.modelValue, (context) => { if (!isEditing.value) draft.value = context })
function startEditing() { draft.value = props.modelValue; saveError.value = ''; isEditing.value = true }
function cancelEditing() { draft.value = props.modelValue; saveError.value = ''; isEditing.value = false }
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
</script>
