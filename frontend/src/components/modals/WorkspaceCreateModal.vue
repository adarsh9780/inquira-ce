<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-[70] overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="modal-overlay" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="relative w-full max-w-2xl modal-card" @click.stop>
        <div class="modal-header flex-col items-start">
          <h3 class="text-base font-semibold" style="color: var(--color-text-main);">Open Or Create Workspace</h3>
          <p class="mt-1 text-sm" style="color: var(--color-text-muted);">
            Open an existing workspace or create a new one without leaving this dialog.
          </p>
        </div>

        <div class="px-5 py-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <section class="space-y-3">
            <div class="space-y-1">
              <h4 class="text-sm font-semibold" style="color: var(--color-text-main);">Create New Workspace</h4>
              <p class="text-xs" style="color: var(--color-text-muted);">{{ planLabel }} plan</p>
            </div>

            <div class="space-y-2">
              <label for="workspace-name" class="text-sm font-medium" style="color: var(--color-text-main);">Workspace Name</label>
              <input
                id="workspace-name"
                ref="nameInputRef"
                v-model="name"
                type="text"
                maxlength="120"
                class="input-base"
                placeholder="e.g. IPL Analytics"
                @keydown.enter.prevent="submit"
              />
              <p
                v-if="duplicateWorkspace"
                class="text-xs"
                style="color: #b42318;"
              >
                "{{ duplicateWorkspace.name }}" already exists. Open it from the list instead or choose a different name.
              </p>
              <p
                v-else
                class="text-xs"
                style="color: var(--color-text-muted);"
              >
                Workspace names must be unique. Matching ignores extra spaces and letter casing.
              </p>
            </div>

            <p class="text-xs leading-5 rounded-lg px-3 py-2" style="color: var(--color-text-muted); background-color: color-mix(in srgb, var(--color-surface) 82%, transparent);">
              Your new workspace will become the active workspace right away. If another workspace is active, we will clean up its running resources first. You can switch back later from the workspace picker.
            </p>
          </section>

          <section class="space-y-3">
            <div class="space-y-1">
              <h4 class="text-sm font-semibold" style="color: var(--color-text-main);">Open Existing Workspace</h4>
              <p class="text-xs" style="color: var(--color-text-muted);">
                Available workspaces are listed below. Select one to view details or open it directly.
              </p>
            </div>

            <div v-if="workspaceOptions.length > 0" class="space-y-3">
              <label for="workspace-open-select" class="text-sm font-medium" style="color: var(--color-text-main);">Available Workspaces</label>
              <select
                id="workspace-open-select"
                v-model="selectedWorkspaceId"
                class="input-base"
              >
                <option
                  v-for="workspace in workspaceOptions"
                  :key="workspace.id"
                  :value="workspace.id"
                >
                  {{ workspace.name }}{{ isWorkspaceCurrentlyActive(workspace) ? ' (Active)' : '' }}
                </option>
              </select>

              <div
                v-if="selectedWorkspace"
                class="rounded-xl border px-3 py-3 space-y-2"
                style="border-color: color-mix(in srgb, var(--color-border) 82%, transparent); background-color: color-mix(in srgb, var(--color-surface) 70%, transparent);"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="text-sm font-semibold truncate" style="color: var(--color-text-main);">
                      {{ selectedWorkspace.name }}
                    </p>
                    <p class="text-xs" style="color: var(--color-text-muted);">
                      {{ isWorkspaceCurrentlyActive(selectedWorkspace) ? 'Currently active workspace' : 'Inactive workspace' }}
                    </p>
                  </div>
                  <span
                    class="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium"
                    :style="selectedWorkspaceBadgeStyle(selectedWorkspace)"
                  >
                    {{ isWorkspaceCurrentlyActive(selectedWorkspace) ? 'Active' : 'Available' }}
                  </span>
                </div>

                <dl class="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <dt style="color: var(--color-text-muted);">Created</dt>
                    <dd style="color: var(--color-text-main);">{{ formatWorkspaceDate(selectedWorkspace.created_at) }}</dd>
                  </div>
                  <div>
                    <dt style="color: var(--color-text-muted);">Updated</dt>
                    <dd style="color: var(--color-text-main);">{{ formatWorkspaceDate(selectedWorkspace.updated_at) }}</dd>
                  </div>
                </dl>

                <button
                  type="button"
                  class="btn-secondary text-sm px-4 py-2 w-full"
                  :disabled="isSubmitting || !selectedWorkspaceId"
                  @click="openWorkspace"
                >
                  Open Workspace
                </button>
              </div>
            </div>

            <div
              v-else
              class="rounded-xl border px-3 py-3 text-sm"
              style="border-color: color-mix(in srgb, var(--color-border) 82%, transparent); color: var(--color-text-muted);"
            >
              No workspaces exist yet. Create your first one on the left.
            </div>
          </section>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn-secondary text-sm px-4 py-2" :disabled="isSubmitting" @click="closeModal">Cancel</button>
          <button type="button" class="btn-primary text-sm px-4 py-2" :disabled="createButtonDisabled" @click="submit">
            {{ isSubmitting ? 'Creating…' : 'Create Workspace' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  isSubmitting: {
    type: Boolean,
    default: false
  },
  plan: {
    type: String,
    default: 'FREE'
  },
  workspaces: {
    type: Array,
    default: () => []
  },
  activeWorkspaceId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'submit', 'open-workspace'])

const name = ref('')
const nameInputRef = ref(null)
const selectedWorkspaceId = ref('')

const planLabel = computed(() => `${String(props.plan || 'FREE').toUpperCase()}`)
const workspaceOptions = computed(() => Array.isArray(props.workspaces) ? props.workspaces : [])
const duplicateWorkspace = computed(() => {
  const normalizedCandidate = normalizeWorkspaceName(name.value)
  if (!normalizedCandidate) return null
  return workspaceOptions.value.find((workspace) => normalizeWorkspaceName(workspace?.name) === normalizedCandidate) || null
})
const selectedWorkspace = computed(() => {
  const selectedId = String(selectedWorkspaceId.value || '').trim()
  return workspaceOptions.value.find((workspace) => workspace?.id === selectedId) || null
})
const createButtonDisabled = computed(() => props.isSubmitting || !name.value.trim() || Boolean(duplicateWorkspace.value))

function closeModal() {
  emit('close')
}

function submit() {
  if (!name.value.trim() || duplicateWorkspace.value) return
  emit('submit', name.value.trim())
}

function openWorkspace() {
  const workspaceId = String(selectedWorkspaceId.value || '').trim()
  if (!workspaceId || props.isSubmitting) return
  emit('open-workspace', workspaceId)
}

function normalizeWorkspaceName(value) {
  return String(value || '').trim().split(/\s+/).join(' ').toLowerCase()
}

function isWorkspaceCurrentlyActive(workspace) {
  const workspaceId = String(workspace?.id || '').trim()
  return workspaceId !== '' && workspaceId === String(props.activeWorkspaceId || '').trim()
}

function formatWorkspaceDate(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'Unknown'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

function selectedWorkspaceBadgeStyle(workspace) {
  if (isWorkspaceCurrentlyActive(workspace)) {
    return 'background-color: #ecfdf3; color: #027a48;'
  }
  return 'background-color: color-mix(in srgb, var(--color-surface) 84%, transparent); color: var(--color-text-muted);'
}

function resetWorkspaceSelection() {
  const preferredId = String(props.activeWorkspaceId || '').trim()
  if (preferredId && workspaceOptions.value.some((workspace) => workspace?.id === preferredId)) {
    selectedWorkspaceId.value = preferredId
    return
  }
  selectedWorkspaceId.value = String(workspaceOptions.value[0]?.id || '')
}

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      name.value = ''
      resetWorkspaceSelection()
      await nextTick()
      nameInputRef.value?.focus()
    }
  }
)

watch(
  () => [props.workspaces, props.activeWorkspaceId],
  () => {
    if (!props.isOpen) return
    const selectedId = String(selectedWorkspaceId.value || '').trim()
    if (selectedId && workspaceOptions.value.some((workspace) => workspace?.id === selectedId)) {
      return
    }
    resetWorkspaceSelection()
  },
)

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && props.isOpen) {
    closeModal()
  }
})
</script>
