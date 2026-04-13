<template>
  <div class="space-y-5">
    <div class="flex items-center gap-0">
      <template v-for="(step, idx) in steps" :key="step.id">
        <div class="flex min-w-0 flex-col items-center">
          <div
            class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium"
            :class="circleClass(step.id)"
          >
            <span v-if="step.id < currentStep">✓</span>
            <span v-else>{{ step.id }}</span>
          </div>
          <span class="mt-2 text-center text-[11px] leading-tight text-[var(--color-text-sub)]">{{ step.label }}</span>
        </div>
        <div
          v-if="idx < steps.length - 1"
          class="mx-2 h-px flex-1"
          :class="step.id < currentStep ? 'bg-[var(--color-accent)] opacity-40' : 'bg-[var(--color-border)]'"
        ></div>
      </template>
    </div>

    <div v-if="currentStep === 1" class="space-y-4">
      <div>
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Name it</label>
        <input
          :value="wsName"
          type="text"
          placeholder="e.g. IPL 2024 analytics"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          @input="emit('update:wsName', $event.target.value)"
        />
      </div>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!wsName.trim()"
          @click="emit('update:currentStep', 2)"
        >
          Next
        </button>
      </div>
    </div>

    <div v-else-if="currentStep === 2" class="space-y-4">
      <div
        v-if="!fileSelected"
        class="cursor-pointer rounded-lg border-2 border-dashed border-[var(--color-border-strong)] p-7 text-center transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)]"
        @click="simulateFileSelect"
      >
        <div class="text-2xl">📁</div>
        <p class="mt-2 text-sm font-medium text-[var(--color-text-main)]">Choose data file</p>
        <p class="mt-1 text-xs text-[var(--color-text-muted)]">Your files stay local on this device.</p>
        <div class="mt-3 flex flex-wrap justify-center gap-2">
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">CSV</span>
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">Parquet</span>
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">XLSX</span>
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">JSON</span>
        </div>
      </div>

      <div v-else class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] p-4 text-sm text-[var(--color-text-main)]">
        <div class="flex items-center gap-2">
          <span class="text-[var(--color-success)]">✓</span>
          <span>File selected successfully. You can continue.</span>
        </div>
      </div>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <button
          type="button"
          class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] font-medium"
          @click="emit('update:currentStep', 1)"
        >
          Back
        </button>
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!fileSelected"
          @click="emit('update:currentStep', 3)"
        >
          Next
        </button>
      </div>
    </div>

    <div v-else-if="currentStep === 3" class="space-y-4">
      <div>
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
          Data context
          <span class="ml-1 rounded-full bg-[var(--color-base-muted)] px-2 py-0.5 text-[10px] normal-case tracking-normal text-[var(--color-text-muted)]">Optional</span>
        </label>
        <textarea
          v-model="dataContext"
          rows="4"
          placeholder="Add business context so analyses are more accurate."
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
        ></textarea>
      </div>

      <div class="rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] p-3 text-xs leading-relaxed text-[var(--color-text-sub)]">
        Context helps the assistant interpret column intent, business terms, and metric definitions before generating charts and summaries.
      </div>

      <label class="inline-flex cursor-pointer items-start gap-2 text-sm text-[var(--color-text-sub)]">
        <input
          v-model="schemaPrivacy"
          type="checkbox"
          class="mt-0.5"
        />
        <span>Allow sample values in schema prompts for higher-quality field descriptions.</span>
      </label>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <button
          type="button"
          class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] font-medium"
          @click="emit('update:currentStep', 2)"
        >
          Back
        </button>
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90"
          @click="emit('triggerSave')"
        >
          Create workspace
        </button>
      </div>
    </div>

    <div v-else class="space-y-4">
      <p class="text-sm text-[var(--color-text-sub)]">Saving workspace setup</p>
      <ul class="space-y-2">
        <li v-for="(item, idx) in saveTasks" :key="item" class="flex items-center gap-2 text-sm text-[var(--color-text-main)]">
          <span v-if="idx + 1 < savingStep" class="text-[var(--color-success)]">✓</span>
          <span
            v-else-if="idx + 1 === savingStep"
            class="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent"
          ></span>
          <span v-else class="text-[var(--color-text-muted)]">○</span>
          <span>{{ item }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  currentStep: {
    type: Number,
    required: true,
  },
  wsName: {
    type: String,
    required: true,
  },
  fileSelected: {
    type: Boolean,
    required: true,
  },
  savingStep: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits(['update:currentStep', 'update:wsName', 'update:fileSelected', 'triggerSave'])

const dataContext = ref('')
const schemaPrivacy = ref(false)

const steps = [
  { id: 1, label: 'Name' },
  { id: 2, label: 'Data' },
  { id: 3, label: 'Context' },
  { id: 4, label: 'Saving' },
]

const saveTasks = [
  'Creating workspace record',
  'Preparing ingestion queue',
  'Extracting schema metadata',
  'Finalizing local cache',
]

const currentStep = computed(() => props.currentStep)
const wsName = computed(() => props.wsName)
const fileSelected = computed(() => props.fileSelected)
const savingStep = computed(() => props.savingStep)

function circleClass(stepId) {
  if (stepId < currentStep.value) {
    return 'bg-[var(--color-accent)] text-white'
  }
  if (stepId === currentStep.value) {
    return 'border-2 border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
  }
  return 'bg-[var(--color-base-muted)] text-[var(--color-text-muted)]'
}

function simulateFileSelect() {
  emit('update:fileSelected', true)
}
</script>
