<template>
  <div :class="rootClass">
    <div v-if="isEmpty" class="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
      {{ emptyLabel }}
    </div>
    <div v-else class="space-y-4">
      <section v-for="conversation in graphConversations" :key="conversation.id" class="overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-base)]">
        <button
          type="button"
          class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-[var(--color-text-main)]/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-accent)]"
          :class="isExpanded(conversation.id) ? 'border-b border-[var(--color-border)]' : ''"
          :aria-expanded="isExpanded(conversation.id)"
          :aria-controls="`conversation-graph-${conversation.id}`"
          @click="toggleConversation(conversation.id)"
        >
          <span class="flex min-w-0 items-center gap-2">
            <ChevronRightIcon class="h-3 w-3 shrink-0 transition-transform" :class="isExpanded(conversation.id) ? 'rotate-90' : ''" />
            <span class="truncate text-[12px] font-semibold text-[var(--color-text-main)]">{{ conversation.title || 'Untitled' }}</span>
          </span>
          <span class="shrink-0 text-[10px] text-[var(--color-text-muted)]">{{ turnCountLabel(conversation) }}</span>
        </button>
        <div
          v-show="isExpanded(conversation.id)"
          :id="`conversation-graph-${conversation.id}`"
          :ref="(element) => setCanvasRef(conversation.id, element)"
          class="relative overflow-hidden bg-[var(--color-surface)]"
          :class="variant === 'page' ? 'h-[360px]' : 'h-[300px]'"
          :data-turn-tree-graph="conversation.id"
          @wheel.prevent="handleWheel(conversation.id, $event)"
        >
          <svg
            class="h-full w-full touch-none select-none"
            role="img"
            :aria-label="`${conversation.title || 'Untitled'} conversation graph`"
            @pointerdown="startPan(conversation.id, $event)"
            @pointermove="movePan(conversation.id, $event)"
            @pointerup="stopPan(conversation.id, $event)"
            @pointercancel="stopPan(conversation.id, $event)"
          >
            <g :transform="viewportTransform(conversation.id)">
              <path
                v-for="edge in conversation.layout.edges"
                :key="edge.id"
                :d="edgePath(conversation, edge)"
                fill="none"
                stroke="var(--color-border-hover)"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                vector-effect="non-scaling-stroke"
              />
              <foreignObject
                v-for="node in conversation.layout.nodes"
                :key="node.id"
                :x="node.x"
                :y="node.y"
                :width="NODE_WIDTH"
                :height="NODE_HEIGHT"
              >
                <div class="h-full" data-graph-interactive>
                  <div class="relative h-full rounded-lg border transition-colors" :class="nodeClass(conversation, node)">
                    <button
                      type="button"
                      class="flex h-full w-full flex-col overflow-hidden rounded-lg px-3 py-2 pr-8 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
                      :aria-label="`Open turn ${node.display_no || node.id}`"
                      @click="selectNode(conversation.id, node.id)"
                      @contextmenu.prevent="openNodeMenu(conversation.id, node.id, $event)"
                    >
                      <span class="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
                        Turn {{ node.display_no || '?' }}
                        <span v-if="isFinal(conversation, node)" class="rounded-full border border-[var(--color-border)] px-1.5 py-0.5 normal-case tracking-normal">Final</span>
                      </span>
                      <span class="mt-1 truncate text-[12px] font-medium text-[var(--color-text-main)]">{{ questionLine(node) }}</span>
                      <span class="mt-0.5 truncate text-[10px] text-[var(--color-text-muted)]">{{ answerLine(node) }}</span>
                    </button>
                    <button
                      type="button"
                      class="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-md text-sm text-[var(--color-text-muted)] hover:bg-[var(--color-panel-muted)] hover:text-[var(--color-text-main)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
                      :aria-label="`Actions for turn ${node.display_no || node.id}`"
                      @click.stop="openNodeMenu(conversation.id, node.id, $event)"
                    >
                      ⋯
                    </button>
                  </div>
                </div>
              </foreignObject>
              <g
                v-for="node in conversation.layout.nodes"
                :key="`${node.id}-ports`"
                class="pointer-events-none"
                aria-hidden="true"
              >
                <circle
                  v-if="node.depth > 0"
                  :cx="nodeInputPort(node).x"
                  :cy="nodeInputPort(node).y"
                  :r="PORT_RADIUS"
                  class="turn-tree-port"
                />
                <circle
                  v-if="node.children?.length"
                  :cx="nodeOutputPort(node).x"
                  :cy="nodeOutputPort(node).y"
                  :r="PORT_RADIUS"
                  class="turn-tree-port"
                />
              </g>
            </g>
          </svg>
          <div class="absolute bottom-2 right-2 flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] p-1 shadow-sm" data-graph-interactive>
            <button type="button" class="graph-control" aria-label="Zoom in" title="Zoom in" @click="zoomBy(conversation.id, 1.2)">+</button>
            <button type="button" class="graph-control" aria-label="Zoom out" title="Zoom out" @click="zoomBy(conversation.id, 1 / 1.2)">−</button>
            <button type="button" class="graph-control px-2" aria-label="Reset graph view" title="Fit graph to view" @click="fitToView(conversation.id)">Fit</button>
          </div>
        </div>
      </section>
    </div>

    <TurnTreeNodeActions
      ref="nodeActionsRef"
      @select="emit('select', $event)"
      @mark-final="emit('mark-final', $event)"
      @delete-turn="emit('delete-turn', $event)"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
import {
  layoutTurnTree,
  turnTreeGraphEdgePath,
  turnTreeGraphPort,
  TURN_TREE_GRAPH_NODE_HEIGHT,
  TURN_TREE_GRAPH_NODE_WIDTH,
  TURN_TREE_GRAPH_PORT_RADIUS,
} from '../../utils/turnTreeGraphLayout'
import TurnTreeNodeActions from './TurnTreeNodeActions.vue'

const MIN_SCALE = 0.35
const MAX_SCALE = 2.4
const NODE_WIDTH = TURN_TREE_GRAPH_NODE_WIDTH
const NODE_HEIGHT = TURN_TREE_GRAPH_NODE_HEIGHT
const PORT_RADIUS = TURN_TREE_GRAPH_PORT_RADIUS

const props = defineProps({
  conversations: { type: Array, default: () => [] },
  currentTurnId: { type: String, default: '' },
  currentParentTurnId: { type: String, default: '' },
  emptyLabel: { type: String, default: 'No turns yet.' },
  variant: { type: String, default: 'modal' },
})
const emit = defineEmits(['select', 'mark-final', 'delete-turn'])
const nodeActionsRef = ref(null)
const canvasRefs = new Map()
const viewports = reactive({})
const expandedConversationIds = ref(new Set())
let resizeObserver = null

const rootClass = computed(() => props.variant === 'page' ? 'min-h-0 flex-1 overflow-y-auto px-1 py-3' : 'min-h-0 flex-1 overflow-y-auto px-3 py-3')
const graphConversations = computed(() => (Array.isArray(props.conversations) ? props.conversations : []).map((conversation) => {
  const layout = layoutTurnTree(conversation?.roots)
  return {
    id: String(conversation?.id || '').trim(),
    title: String(conversation?.title || '').trim(),
    finalTurnId: resolveGraphFinalTurnId(
      layout,
      String(conversation?.final_turn_id || conversation?.finalTurnId || '').trim(),
    ),
    layout,
  }
}).filter((conversation) => conversation.id))
const isEmpty = computed(() => graphConversations.value.length === 0 || graphConversations.value.every((conversation) => conversation.layout.nodes.length === 0))

function ensureViewport(conversationId) {
  if (!viewports[conversationId]) viewports[conversationId] = { x: 0, y: 0, scale: 1, pointerId: null, lastX: 0, lastY: 0 }
  return viewports[conversationId]
}

function resolveGraphFinalTurnId(layout, configuredFinalTurnId) {
  const configuredFinal = layout.nodes.find((node) => node.id === configuredFinalTurnId)
  if (configuredFinal && (!Array.isArray(configuredFinal.children) || configuredFinal.children.length === 0)) {
    return configuredFinal.id
  }
  const leaves = layout.nodes.filter((node) => !Array.isArray(node.children) || node.children.length === 0)
  return leaves.reduce((latest, node) => (
    !latest || Number(node.display_no || 0) > Number(latest.display_no || 0) ? node : latest
  ), null)?.id || ''
}

function isExpanded(conversationId) {
  return expandedConversationIds.value.has(String(conversationId || '').trim())
}

function toggleConversation(conversationId, forceOpen = false) {
  const id = String(conversationId || '').trim()
  if (!id) return
  const next = new Set(expandedConversationIds.value)
  if (forceOpen || !next.has(id)) next.add(id)
  else next.delete(id)
  expandedConversationIds.value = next
  if (next.has(id)) void nextTick(() => fitToView(id))
}

function turnCountLabel(conversation) {
  const count = conversation.layout.nodes.length
  return `${count} ${count === 1 ? 'turn' : 'turns'}`
}

function setCanvasRef(conversationId, element) {
  const previous = canvasRefs.get(conversationId)
  if (previous && resizeObserver) resizeObserver.unobserve(previous)
  if (!element) {
    canvasRefs.delete(conversationId)
    return
  }
  canvasRefs.set(conversationId, element)
  ensureViewport(conversationId)
  if (resizeObserver) resizeObserver.observe(element)
}

function viewportTransform(conversationId) {
  const viewport = ensureViewport(conversationId)
  return `translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`
}

function conversationById(conversationId) {
  return graphConversations.value.find((conversation) => conversation.id === conversationId)
}

function edgePath(conversation, edge) {
  const parent = conversation.layout.nodes.find((node) => node.id === edge.parentId)
  const child = conversation.layout.nodes.find((node) => node.id === edge.childId)
  return turnTreeGraphEdgePath(parent, child)
}

function nodeInputPort(node) {
  return turnTreeGraphPort(node, 'input')
}

function nodeOutputPort(node) {
  return turnTreeGraphPort(node, 'output')
}

function fitToView(conversationId) {
  const element = canvasRefs.get(conversationId)
  const conversation = conversationById(conversationId)
  if (!element || !conversation || conversation.layout.bounds.width === 0) return
  const width = element.clientWidth || 1
  const height = element.clientHeight || 1
  const scale = clamp(Math.min(width / conversation.layout.bounds.width, height / conversation.layout.bounds.height) * 0.92, MIN_SCALE, 1.5)
  const viewport = ensureViewport(conversationId)
  viewport.scale = scale
  viewport.x = (width - (conversation.layout.bounds.width * scale)) / 2
  viewport.y = (height - (conversation.layout.bounds.height * scale)) / 2
}

function zoomBy(conversationId, factor, clientX = null, clientY = null) {
  const element = canvasRefs.get(conversationId)
  if (!element) return
  const viewport = ensureViewport(conversationId)
  const rect = element.getBoundingClientRect()
  const pointX = clientX === null ? rect.width / 2 : clientX - rect.left
  const pointY = clientY === null ? rect.height / 2 : clientY - rect.top
  const nextScale = clamp(viewport.scale * factor, MIN_SCALE, MAX_SCALE)
  const graphX = (pointX - viewport.x) / viewport.scale
  const graphY = (pointY - viewport.y) / viewport.scale
  viewport.scale = nextScale
  viewport.x = pointX - (graphX * nextScale)
  viewport.y = pointY - (graphY * nextScale)
}

function handleWheel(conversationId, event) {
  zoomBy(conversationId, event.deltaY < 0 ? 1.12 : 1 / 1.12, event.clientX, event.clientY)
}

function startPan(conversationId, event) {
  if (event.button !== 0 || event.target?.closest?.('[data-graph-interactive]')) return
  const viewport = ensureViewport(conversationId)
  viewport.pointerId = event.pointerId
  viewport.lastX = event.clientX
  viewport.lastY = event.clientY
  event.currentTarget?.setPointerCapture?.(event.pointerId)
}

function movePan(conversationId, event) {
  const viewport = ensureViewport(conversationId)
  if (viewport.pointerId !== event.pointerId) return
  viewport.x += event.clientX - viewport.lastX
  viewport.y += event.clientY - viewport.lastY
  viewport.lastX = event.clientX
  viewport.lastY = event.clientY
}

function stopPan(conversationId, event) {
  const viewport = ensureViewport(conversationId)
  if (viewport.pointerId !== event.pointerId) return
  viewport.pointerId = null
  event.currentTarget?.releasePointerCapture?.(event.pointerId)
}

function selectNode(conversationId, turnId) {
  emit('select', { conversationId, turnId })
}

function openNodeMenu(conversationId, turnId, event) {
  nodeActionsRef.value?.open({ conversationId, turnId, x: event?.clientX || 0, y: event?.clientY || 0 })
}

function nodeClass(conversation, node) {
  if (String(props.currentTurnId || '').trim() === node.id) return 'border-[var(--color-accent)] bg-[color-mix(in_srgb,var(--color-accent)_10%,var(--color-base))] shadow-[0_0_0_1px_color-mix(in_srgb,var(--color-accent)_30%,transparent)]'
  if (String(props.currentParentTurnId || '').trim() === node.id) return 'border-[var(--color-border-hover)] bg-[color-mix(in_srgb,var(--color-text-main)_4%,var(--color-base))]'
  return 'border-[var(--color-border)] bg-[var(--color-base)] opacity-80 hover:opacity-100'
}

function isFinal(conversation, node) {
  return conversation.finalTurnId === node.id
}

function questionLine(node) {
  return String(node?.user_text || '').trim() || `Turn ${node?.display_no || ''}`.trim()
}

function answerLine(node) {
  return String(node?.assistant_text || '').replace(/\s+/g, ' ').trim() || 'No response saved'
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value))
}

async function fitAll() {
  await nextTick()
  for (const conversation of graphConversations.value) fitToView(conversation.id)
}

onMounted(() => {
  for (const conversation of graphConversations.value) toggleConversation(conversation.id, true)
  if ('ResizeObserver' in window) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const match = [...canvasRefs.entries()].find(([, element]) => element === entry.target)
        if (match) fitToView(match[0])
      }
    })
    for (const element of canvasRefs.values()) resizeObserver.observe(element)
  }
  void fitAll()
})

onBeforeUnmount(() => resizeObserver?.disconnect())
watch(() => graphConversations.value.map((conversation) => `${conversation.id}:${conversation.layout.nodes.length}`).join('|'), () => void fitAll())
watch(() => graphConversations.value.map((conversation) => conversation.id).join('|'), () => {
  const next = new Set(expandedConversationIds.value)
  for (const conversation of graphConversations.value) next.add(conversation.id)
  expandedConversationIds.value = next
})

defineExpose({ fitToView, zoomBy })
</script>

<style scoped>
.graph-control {
  display: inline-flex;
  min-width: 1.75rem;
  height: 1.75rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.graph-control:hover {
  background: var(--color-panel-muted);
  color: var(--color-text-main);
}

.graph-control:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.turn-tree-port {
  fill: var(--color-border-hover);
  stroke: var(--color-surface);
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
</style>
