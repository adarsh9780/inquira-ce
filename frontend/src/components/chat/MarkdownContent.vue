<template>
  <div v-if="mode === 'markdown'" v-html="rendered"></div>
  <pre v-else class="chat-code-scroll"><code class="language-python" v-html="rendered"></code></pre>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderCode, renderMarkdown } from '../../utils/messageRendering'
import 'katex/dist/katex.min.css'

const props = withDefaults(defineProps<{
  content?: string
  mode?: 'markdown' | 'code'
}>(), {
  content: '',
  mode: 'markdown',
})

const rendered = computed(() => (
  props.mode === 'code' ? renderCode(props.content) : renderMarkdown(props.content)
))
</script>
