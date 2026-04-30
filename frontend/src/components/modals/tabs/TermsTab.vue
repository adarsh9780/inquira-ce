<template>
  <section class="h-full">
    <div class="mb-4">
      <h2 class="text-lg font-bold text-[var(--color-text-main)]">Terms &amp; Conditions</h2>
      <p class="mt-1 text-sm text-[var(--color-text-muted)]">
        Review the current desktop usage terms inside the app.
      </p>
      <p v-if="termsLastUpdated" class="mt-2 text-xs text-[var(--color-text-muted)]">
        Last updated: {{ termsLastUpdated }}
      </p>
    </div>

    <div
      class="rounded-xl border bg-[var(--color-base)] p-4 text-sm leading-6"
      style="border-color: var(--color-border);"
    >
      <p v-if="isTermsLoading" class="text-[var(--color-text-muted)]">Loading terms...</p>
      <p
        v-else-if="termsError"
        class="rounded-md border border-[var(--color-danger)]/35 bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger-text)]"
      >
        {{ termsError }}
      </p>
      <div
        v-else
        class="terms-markdown-content"
        v-html="termsHtml"
      ></div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import apiService from '../../../services/apiService'

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
})

const isTermsLoading = ref(false)
const termsError = ref('')
const termsMarkdown = ref('')
const termsLastUpdated = ref('')

const termsMarkdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const termsHtml = computed(() => {
  const raw = String(termsMarkdown.value || '').trim()
  if (!raw) return ''
  return DOMPurify.sanitize(termsMarkdownRenderer.render(raw), {
    USE_PROFILES: { html: true },
  })
})

watch(
  () => props.active,
  (isActive) => {
    if (isActive) {
      void loadTermsAndConditions()
    }
  },
  { immediate: true },
)

async function loadTermsAndConditions({ force = false } = {}) {
  if (termsMarkdown.value && !force) return
  isTermsLoading.value = true
  termsError.value = ''
  try {
    const payload = await apiService.v1GetTermsAndConditions()
    termsMarkdown.value = String(payload?.markdown || '').trim()
    termsLastUpdated.value = String(payload?.last_updated || '').trim()
  } catch (error) {
    termsError.value = error?.message || 'Failed to load Terms & Conditions.'
  } finally {
    isTermsLoading.value = false
  }
}
</script>

<style scoped>
:deep(.terms-markdown-content h1),
:deep(.terms-markdown-content h2),
:deep(.terms-markdown-content h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

:deep(.terms-markdown-content h1:first-child),
:deep(.terms-markdown-content h2:first-child),
:deep(.terms-markdown-content h3:first-child) {
  margin-top: 0;
}

:deep(.terms-markdown-content p) {
  margin: 0.5rem 0;
}

:deep(.terms-markdown-content ul) {
  margin: 0.5rem 0;
  padding-left: 1.1rem;
  list-style: disc;
}

:deep(.terms-markdown-content li) {
  margin: 0.2rem 0;
}

:deep(.terms-markdown-content code) {
  background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent);
  border-radius: 0.25rem;
  padding: 0.05rem 0.3rem;
}

:deep(.terms-markdown-content a) {
  color: var(--color-info);
  text-decoration: underline;
}
</style>
