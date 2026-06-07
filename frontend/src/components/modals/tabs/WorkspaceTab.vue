<template>
  <section class="scrollbar-hidden h-full overflow-y-auto">
    <div class="grid grid-cols-[240px_1fr] gap-6 h-full min-h-0">
      
      <!-- Left Column: Workspace Switch & Create Navigator -->
      <aside class="flex flex-col border-r border-[var(--color-border)] pr-4 h-full min-h-0 select-none">
        <header class="mb-3 flex items-center justify-between">
          <h3 class="section-label">Workspaces</h3>
          <button
            type="button"
            class="text-xs font-semibold text-[var(--color-accent)] hover:underline"
            @click="emit('navigate', 'ws-create', 'forward')"
          >
            + New
          </button>
        </header>

        <!-- Search / Filter / Inline Create -->
        <div class="mb-3 space-y-2">
          <!-- Inline quick-create panel -->
          <div class="relative">
            <input
              v-model="quickCreateName"
              type="text"
              class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-base)] px-2.5 py-1.5 text-xs text-[var(--color-text-main)] placeholder-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]"
              placeholder="Quick create + Enter"
              @keydown.enter.prevent="handleQuickCreate"
            />
          </div>
        </div>

        <!-- Scrollable list of workspaces -->
        <div class="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin">
          <div v-if="workspaceCards.length" class="space-y-2">
            <div
              v-for="workspace in workspaceCards"
              :key="workspace.id"
              class="group relative flex flex-col w-full cursor-pointer rounded-lg px-3 py-2.5 text-left transition-all"
              :class="workspace.id === activeWorkspaceId
                ? 'bg-[var(--color-accent-soft)] ring-1 ring-[var(--color-accent-border)]'
                : 'bg-[var(--color-base-soft)] hover:bg-[var(--color-base-muted)]'"
              @click="openWorkspaceDetail(workspace.id)"
            >
              <div class="flex items-start justify-between gap-2">
                <p
                  class="truncate text-xs font-medium"
                  :class="workspace.id === activeWorkspaceId ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'"
                >
                  {{ workspace.name || 'Untitled workspace' }}
                </p>
                <div class="flex shrink-0 items-center gap-1.5">
                  <span
                    v-if="workspace.id === activeWorkspaceId"
                    class="rounded-full bg-[var(--color-success-bg)] px-1.5 py-0.25 text-[9px] text-[var(--color-success)]"
                  >
                    Active
                  </span>
                  <button
                    type="button"
                    class="rounded p-1 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)]"
                    title="Delete workspace"
                    aria-label="Delete workspace"
                    @click.stop="requestDeleteWorkspace(workspace.id)"
                  >
                    <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M5 7h14" />
                      <path d="M9 7V5h6v2" />
                      <path d="M8 7l1 12h6l1-12" />
                    </svg>
                  </button>
                </div>
              </div>
              <p class="text-[10px] text-[var(--color-text-muted)] mt-1">
                {{ workspace.conversationCount }} convs · {{ workspace.lastActiveLabel }}
              </p>
            </div>
          </div>
          <div v-else class="text-center py-4">
            <p class="text-xs text-[var(--color-text-muted)]">No workspaces yet</p>
          </div>
        </div>
      </aside>

      <!-- Right Column: Detail / Configuration / Ingest Dashboard -->
      <div class="flex flex-col min-w-0 h-full">
        <!-- If in ws-list mode but no workspace is active / selected, or just show active detail -->
        <div v-if="panelMode === 'ws-list'" class="flex-1 flex flex-col justify-between h-full space-y-4">
          <header class="flex items-center justify-between pb-2 border-b border-[var(--color-border)]">
            <h2 class="text-sm font-bold text-[var(--color-text-main)]">Active Workspace Summary</h2>
            <button
              type="button"
              class="inline-flex items-center gap-1 rounded-md border border-[var(--color-border-strong)] bg-[var(--color-base)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-accent)] shadow-sm transition-all hover:border-[var(--color-accent-border)] hover:bg-[var(--color-accent-soft)] hover:shadow-none"
              @click="emit('navigate', 'ws-create', 'forward')"
            >
              <span class="text-sm leading-none">+</span>
              <span>New workspace</span>
            </button>
          </header>

          <div v-if="activeWorkspace" class="space-y-4 flex-1 overflow-y-auto scrollbar-thin">
            <!-- Active workspace statistics card -->
            <div class="grid grid-cols-3 gap-3 bg-[var(--color-base-soft)] p-3 rounded-lg border border-[var(--color-border)]">
              <div>
                <span class="section-label block mb-1">Workspace Name</span>
                <p class="text-sm font-semibold truncate text-[var(--color-text-main)]">{{ activeWorkspace.name }}</p>
              </div>
              <div>
                <span class="section-label block mb-1">Conversations</span>
                <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ activeWorkspace.conversationCount }}</p>
              </div>
              <div>
                <span class="section-label block mb-1">Last Active</span>
                <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ activeWorkspace.lastActiveLabel }}</p>
              </div>
            </div>

            <!-- Ingested datasets list -->
            <div class="space-y-2">
              <h4 class="section-label mb-2">Linked Datasets</h4>
              <div v-if="datasetEntries.length" class="space-y-2">
                <div
                  v-for="dataset in datasetEntries"
                  :key="dataset.table_name"
                  class="rounded-lg bg-[var(--color-base-soft)] px-3 py-2.5 flex items-center justify-between border border-[var(--color-border)]"
                >
                  <div class="min-w-0">
                    <p class="text-xs font-medium text-[var(--color-text-main)] truncate">{{ dataset.filename }}</p>
                    <p class="text-[10px] text-[var(--color-text-muted)] mt-0.5">{{ datasetMetadata(dataset) }}</p>
                  </div>
                  <span
                    class="rounded-full px-2 py-0.5 text-[9px] font-medium"
                    :class="datasetSchemaStatusBadgeClass(dataset)"
                  >
                    {{ datasetSchemaStatusLabel(dataset) }}
                  </span>
                </div>
              </div>
              <div v-else class="text-center py-6 border border-dashed border-[var(--color-border)] rounded-lg bg-[var(--color-base-soft)]/20">
                <p class="text-xs text-[var(--color-text-muted)]">No datasets loaded yet.</p>
                <button
                  type="button"
                  class="text-xs font-semibold text-[var(--color-accent)] hover:underline mt-1"
                  @click="openWorkspaceDetail(activeWorkspace.id)"
                >
                  Configure and import data &rarr;
                </button>
              </div>
            </div>
          </div>
          
          <div v-else-if="workspaceCards.length" class="flex-1 flex flex-col items-center justify-center p-6 text-center">
            <svg viewBox="0 0 24 24" class="h-10 w-10 text-[var(--color-text-muted)] mb-3" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 7h6l2 2h10v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
            </svg>
            <p class="text-xs text-[var(--color-text-muted)]">Select a workspace from the list to view its details or activate it.</p>
          </div>

          <div v-else class="rounded-lg bg-[var(--color-base-soft)] px-5 py-8 text-center flex-1 flex flex-col items-center justify-center">
            <svg viewBox="0 0 24 24" class="mx-auto mb-3 h-8 w-8 text-[var(--color-text-muted)]" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M3 7h6l2 2h10v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
            </svg>
            <p class="mb-4 text-sm text-[var(--color-text-sub)]">No workspaces yet</p>
            <button
              type="button"
              class="btn-primary px-4 py-2 text-sm"
              @click="emit('navigate', 'ws-create', 'forward')"
            >
              Create your first workspace
            </button>
          </div>
        </div>

        <div v-else class="flex h-full flex-col min-h-0">
          <!-- Header -->
          <header class="flex shrink-0 items-center justify-between gap-3 pt-1 pb-3 border-b border-[var(--color-border)]">
            <div class="flex min-w-0 flex-1 items-center gap-2">
              <button
                v-if="isCreatingMode"
                type="button"
                class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] hover:text-[var(--color-text-main)]"
                title="Back to workspace list"
                aria-label="Back to workspace list"
                @click="emit('navigate', 'ws-list', 'backward')"
              >
                <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M12.5 4.5L7 10l5.5 5.5" />
                </svg>
              </button>
              <h2 class="truncate text-sm font-bold text-[var(--color-text-main)]">
                {{ isCreatingMode ? 'New workspace' : (setupWorkspaceName || activeWorkspace?.name || 'Workspace detail') }}
              </h2>
            </div>
            <div v-if="!isCreatingMode" class="flex items-center gap-2">
              <button
                v-if="!isWorkspaceActive"
                type="button"
                class="rounded-full border border-[var(--color-border-strong)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-main)] transition-colors hover:border-[var(--color-accent-border)] hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-accent)]"
                @click="activateSelectedWorkspace"
              >
                Activate workspace
              </button>
              <span
                v-else
                class="inline-flex items-center rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-success)]"
              >
                Active
              </span>
            </div>
          </header>

          <!-- Stepper (single shared instance) -->
          <div class="shrink-0 px-4 pb-4 pt-5">
            <div class="workspace-stepper">
              <button
                v-for="(step, index) in setupSteps"
                :key="step.id"
                type="button"
                class="workspace-stepper-item"
                @click="goToSetupStep(step.id)"
              >
                <span
                  v-if="index > 0"
                  class="workspace-stepper-line"
                  :class="setupStep > step.id - 1 ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-border)]'"
                ></span>
                <span class="workspace-stepper-dot" :class="stepDotClass(step.id)">{{ step.id }}</span>
                <span class="mt-2 block truncate text-[10px] font-semibold" :class="stepLabelClass(step.id)">{{ step.label }}</span>
              </button>
            </div>
          </div>

          <!-- Step content separator -->
          <div class="mx-4 border-t border-[var(--color-border)]"></div>

          <!-- Step content -->
          <Transition
            enter-active-class="dialog-fade-enter-active"
            enter-from-class="dialog-fade-enter-from"
            leave-active-class="dialog-fade-leave-active"
            leave-to-class="dialog-fade-leave-to"
            mode="out-in"
            class="min-h-0 flex-1 overflow-y-auto pt-5"
          >
            <!-- Step 1: Workspace name — shared between create and detail -->
            <div v-if="setupStep === 1" key="step-1" class="relative flex flex-col gap-4 pb-4 pt-1">
              <!-- Loading overlay shown only during creation -->
              <div
                v-if="isCreatingWorkspace"
                class="absolute inset-0 z-10 flex items-center justify-center bg-[var(--color-base)]/85 px-6 text-center backdrop-blur-sm"
                role="status"
                aria-live="polite"
              >
                <div class="max-w-sm">
                  <span class="mx-auto mb-4 block h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-accent-border)] border-t-[var(--color-accent)]"></span>
                  <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ workspaceCreateTitle }}</p>
                  <p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ workspaceCreateMessage }}</p>
                </div>
              </div>

              <p class="rounded-lg bg-[var(--color-base-muted)]/60 px-3 py-2 text-xs leading-relaxed text-[var(--color-text-muted)]">
                Give this workspace a short name. You can add context and data in the next steps.
              </p>

              <label class="flex flex-col gap-1.5">
                <span class="section-label">Workspace name</span>
                <input
                  v-model="setupWorkspaceName"
                  type="text"
                  class="input-base input-outlined py-1.5 text-xs"
                  placeholder="e.g. Sales analysis"
                  :disabled="isCreatingWorkspace || isSavingWorkspaceIdentity"
                  @keydown.enter.prevent="continueFromWorkspaceName()"
                />
              </label>

              <div class="mt-2 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
                <button
                  v-if="!isCreatingMode"
                  type="button"
                  class="btn-ghost text-xs text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] py-1.5 px-3"
                  :disabled="isSavingWorkspaceIdentity"
                  @click="requestDeleteWorkspace(activeWorkspaceId)"
                >
                  Delete workspace
                </button>
                <span v-else />
                <button
                  type="button"
                  class="btn-primary px-4 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="isCreatingWorkspace || isSavingWorkspaceIdentity || !setupWorkspaceName.trim()"
                  @click="continueFromWorkspaceName()"
                >
                  <span v-if="isCreatingWorkspace || isSavingWorkspaceIdentity">{{ isCreatingMode ? 'Creating...' : 'Saving...' }}</span>
                  <span v-else>Next</span>
                </button>
              </div>
            </div>

            <!-- Step 2: Workspace context -->
            <div v-else-if="setupStep === 2" key="step-2" class="relative flex flex-col gap-4 pb-4 pt-1">
              <p class="rounded-lg bg-[var(--color-base-muted)]/60 px-3 py-2 text-xs leading-relaxed text-[var(--color-text-muted)]">
                Add optional business context so schema descriptions and future answers use your terminology.
              </p>

              <label class="flex flex-col gap-1.5">
                <span class="section-label inline-flex items-center gap-1.5">
                  Workspace context
                  <span class="inline-flex items-center gap-1 rounded bg-[var(--color-base-muted)] px-1 py-0.5 text-[9px] normal-case tracking-normal text-[var(--color-text-muted)]">
                    <svg class="h-2 w-2" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="M8 1v14M1 8h14"/>
                    </svg>
                    Optional
                  </span>
                </span>
                <textarea
                  v-model="setupWorkspaceContext"
                  rows="5"
                  class="input-base input-outlined resize-none py-1.5 text-xs"
                  placeholder="Describe the business purpose, terms, and schema context for this workspace..."
                  :disabled="isSavingWorkspaceIdentity"
                  @keydown.enter.exact.prevent="continueFromWorkspaceContext()"
                ></textarea>
              </label>

              <div class="mt-2 flex items-center justify-end gap-2 border-t border-[var(--color-border)] pt-4">
                <button
                  type="button"
                  class="btn-secondary px-5 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="isSavingWorkspaceIdentity"
                  @click="skipWorkspaceContext()"
                >
                  Skip
                </button>
                <button
                  type="button"
                  class="btn-primary px-4 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="isSavingWorkspaceIdentity || !setupWorkspaceContext.trim()"
                  @click="saveWorkspaceContextAndContinue()"
                >
                  <span v-if="isSavingWorkspaceIdentity">Saving...</span>
                  <span v-else>Next</span>
                </button>
              </div>
            </div>

            <!-- Step 3: Datasets -->
            <div v-else-if="setupStep === 3" key="step-3" class="space-y-4">
              <!-- Visual Connection/Pipeline Graph -->
              <div class="p-3 bg-[var(--color-base-soft)] rounded-xl border border-[var(--color-border)] overflow-hidden">
                <p class="section-label mb-3">System Pipeline Graph</p>
                <div class="flex items-center justify-between gap-2 text-center select-none">
                  <!-- Node 1: Files -->
                  <div class="flex-1 flex flex-col items-center p-2 rounded-lg bg-[var(--color-base)] border border-[var(--color-border)] shadow-sm">
                    <svg viewBox="0 0 24 24" class="h-5 w-5 text-[var(--color-accent)] mb-1" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <span class="text-[9px] font-bold text-[var(--color-text-main)] truncate max-w-full">Data Files</span>
                    <span class="text-[8px] text-[var(--color-text-muted)] mt-0.5">{{ datasetEntries.length }} Active</span>
                  </div>

                  <!-- Connector Arrow -->
                  <div class="flex items-center justify-center text-[var(--color-text-muted)]">
                    <svg viewBox="0 0 24 24" class="h-4 w-4 animate-pulse" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </div>

                  <!-- Node 2: Profiler -->
                  <div class="flex-1 flex flex-col items-center p-2 rounded-lg bg-[var(--color-base)] border border-[var(--color-border)] shadow-sm">
                    <svg viewBox="0 0 24 24" class="h-5 w-5 text-[var(--color-accent)] mb-1" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                      <line x1="12" y1="22.08" x2="12" y2="12" />
                    </svg>
                    <span class="text-[9px] font-bold text-[var(--color-text-main)]">LLM Profiler</span>
                    <span class="text-[8px] text-[var(--color-text-muted)] mt-0.5">Auto-Schemas</span>
                  </div>

                  <!-- Connector Arrow -->
                  <div class="flex items-center justify-center text-[var(--color-text-muted)]">
                    <svg viewBox="0 0 24 24" class="h-4 w-4 animate-pulse" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </div>

                  <!-- Node 3: Database -->
                  <div class="flex-1 flex flex-col items-center p-2 rounded-lg bg-[var(--color-base)] border border-[var(--color-border)] shadow-sm">
                    <svg viewBox="0 0 24 24" class="h-5 w-5 text-[var(--color-accent)] mb-1" fill="none" stroke="currentColor" stroke-width="2">
                      <ellipse cx="12" cy="5" rx="9" ry="3" />
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                      <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
                    </svg>
                    <span class="text-[9px] font-bold text-[var(--color-text-main)]">DuckDB</span>
                    <span class="text-[8px] text-[var(--color-text-muted)] mt-0.5">Local DB</span>
                  </div>

                  <!-- Connector Arrow -->
                  <div class="flex items-center justify-center text-[var(--color-text-muted)]">
                    <svg viewBox="0 0 24 24" class="h-4 w-4 animate-pulse" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </div>

                  <!-- Node 4: Kernel -->
                  <div 
                    class="flex-1 flex flex-col items-center p-2 rounded-lg bg-[var(--color-base)] border shadow-sm transition-all"
                    :class="{
                      'node-success': runtimeStatusTone === 'success',
                      'node-danger': runtimeStatusTone === 'danger',
                      'node-accent': runtimeStatusTone === 'accent',
                      'border-[var(--color-border)]': runtimeStatusTone === 'muted'
                    }"
                  >
                    <svg 
                      viewBox="0 0 24 24" 
                      class="h-5 w-5 mb-1" 
                      :class="{
                        'text-[var(--color-success)]': runtimeStatusTone === 'success',
                        'text-[var(--color-danger)]': runtimeStatusTone === 'danger',
                        'text-[var(--color-accent)] animate-spin': runtimeStatusTone === 'accent',
                        'text-[var(--color-text-muted)]': runtimeStatusTone === 'muted'
                      }" 
                      fill="none" 
                      stroke="currentColor" 
                      stroke-width="2"
                    >
                      <rect x="4" y="4" width="16" height="16" rx="2" />
                      <rect x="9" y="9" width="6" height="6" />
                      <line x1="9" y1="1" x2="9" y2="4" />
                      <line x1="15" y1="1" x2="15" y2="4" />
                      <line x1="9" y1="20" x2="9" y2="23" />
                      <line x1="15" y1="20" x2="15" y2="23" />
                      <line x1="20" y1="9" x2="23" y2="9" />
                      <line x1="20" y1="15" x2="23" y2="15" />
                      <line x1="1" y1="9" x2="4" y2="9" />
                      <line x1="1" y1="15" x2="4" y2="15" />
                    </svg>
                    <span class="text-[9px] font-bold text-[var(--color-text-main)]">AI Agent</span>
                    <span class="text-[8px] text-[var(--color-text-muted)] mt-0.5 truncate max-w-full">{{ runtimeStatusLabel }}</span>
                  </div>
                </div>
              </div>

              <!-- Metadata dashboard grid -->
              <div class="grid grid-cols-1 gap-3 border-b border-[var(--color-border)] pb-3 sm:grid-cols-3">
                <div>
                  <p class="section-label">Created</p>
                  <p class="mt-1 text-sm text-[var(--color-text-main)]">{{ detailCreatedAt }}</p>
                </div>
                <div>
                  <p class="section-label">Conversations</p>
                  <p class="mt-1 text-sm text-[var(--color-text-main)]">{{ detailConversationCount }}</p>
                </div>
                <div>
                  <p class="section-label">Last active</p>
                  <p class="mt-1 text-sm text-[var(--color-text-main)]">{{ detailLastActive }}</p>
                </div>
              </div>

              <!-- Runtime Operations -->
              <section class="space-y-3 border-b border-[var(--color-border)] pb-5">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div class="min-w-0">
                    <p class="section-label">Workspace runtime</p>
                    <div class="mt-2 flex flex-wrap items-center gap-2">
                      <span
                        class="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium"
                        :class="{
                          'bg-[var(--color-success-bg)] text-[var(--color-success)]': runtimeStatusTone === 'success',
                          'bg-[var(--color-danger-bg)] text-[var(--color-danger)]': runtimeStatusTone === 'danger',
                          'bg-[var(--color-accent-soft)] text-[var(--color-accent)]': runtimeStatusTone === 'accent',
                          'bg-[var(--color-base-soft)] text-[var(--color-text-muted)]': runtimeStatusTone === 'muted',
                        }"
                      >
                        {{ runtimeStatusLabel }}
                      </span>
                      <span v-if="requiresWorkspaceActivation" class="text-xs text-[var(--color-text-muted)]">Inspecting only. Activate this workspace before changing data.</span>
                    </div>
                    <p v-if="runtimeStatusMessage" class="mt-2 max-w-2xl text-sm text-[var(--color-text-muted)]">{{ runtimeStatusMessage }}</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <button
                      v-if="requiresWorkspaceActivation"
                      type="button"
                      class="rounded-full border border-[var(--color-border-strong)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-main)] transition-colors hover:border-[var(--color-accent-border)] hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-accent)]"
                      @click="activateSelectedWorkspace"
                    >
                      Activate workspace
                    </button>
                    <button
                      type="button"
                      class="rounded-full border border-[var(--color-border-strong)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-main)] transition-colors hover:border-[var(--color-accent-border)] hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-60"
                      :disabled="isRetryingWorkspaceRuntime || isHardResettingWorkspaceRuntime || isCreatingWorkspace"
                      @click="retryWorkspaceRuntime"
                    >
                      {{ isRetryingWorkspaceRuntime ? 'Retrying...' : 'Retry runtime' }}
                    </button>
                    <button
                      type="button"
                      class="rounded-full border border-[var(--color-border-strong)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-main)] transition-colors hover:border-[var(--color-danger)]/35 hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-60"
                      :disabled="isRetryingWorkspaceRuntime || isHardResettingWorkspaceRuntime || isCreatingWorkspace"
                      @click="hardResetWorkspaceRuntime"
                    >
                      {{ isHardResettingWorkspaceRuntime ? 'Rebuilding...' : 'Hard reset runtime' }}
                    </button>
                  </div>
                </div>
              </section>

              <!-- Datasets Area -->
              <div class="space-y-3">
                <div class="flex items-center justify-between gap-3">
                  <p class="section-label">Datasets</p>
                  <button
                    type="button"
                    data-testid="workspace-import-datasets-header"
                    class="btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="isDatasetIngesting || isDeletingDataset || requiresWorkspaceActivation"
                    @click="openDatasetPicker"
                  >
                    <span v-if="isDatasetIngesting">Processing dataset...</span>
                    <span v-else-if="requiresWorkspaceActivation">Activate workspace to add data</span>
                    <span v-else>Import datasets</span>
                  </button>
                </div>

                <!-- Dataset Ingestion Loading -->
                <div
                  v-if="isDatasetIngesting"
                  class="rounded-lg px-4 py-3"
                  :class="datasetIngestHasError ? 'bg-[var(--color-danger-bg)]' : 'bg-[var(--color-accent-soft)]'"
                  aria-live="polite"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <p class="truncate text-sm font-medium" :class="datasetIngestHasError ? 'text-[var(--color-danger)]' : 'text-[var(--color-accent)]'">{{ datasetIngestFilename || 'Selected dataset' }}</p>
                      <p class="mt-1 text-xs" :class="datasetIngestHasError ? 'text-[var(--color-danger)]/90' : 'text-[var(--color-accent)]/90'">{{ datasetIngestStatusLabel }}</p>
                    </div>
                    <button
                      v-if="datasetIngestHasError"
                      type="button"
                      class="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger-bg)] px-2 py-1 text-xs font-medium text-[var(--color-danger)] transition-colors hover:border-[var(--color-danger)]/45"
                      @click="retryLastDatasetIngestion"
                    >
                      Retry
                    </button>
                    <span v-else class="mt-0.5 h-4 w-4 animate-spin rounded-full border-2 border-[var(--color-accent)]/40 border-t-[var(--color-accent)]"></span>
                  </div>
                  <div v-if="datasetIngestPercent !== null" class="mt-2">
                    <div class="h-1.5 overflow-hidden rounded-full" :class="datasetIngestHasError ? 'bg-[var(--color-danger)]/25' : 'bg-[var(--color-accent-border)]/80'">
                      <div
                        class="h-full rounded-full transition-all duration-300"
                        :class="datasetIngestHasError ? 'bg-[var(--color-danger)]' : 'bg-[var(--color-accent)]'"
                        :style="{ width: `${datasetIngestPercent}%` }"
                      ></div>
                    </div>
                    <p class="mt-1 text-right text-[11px]" :class="datasetIngestHasError ? 'text-[var(--color-danger)]' : 'text-[var(--color-accent)]'">{{ datasetIngestPercent }}%</p>
                  </div>
                </div>

                <!-- Dataset List -->
                <div v-if="datasetEntries.length" class="space-y-2">
                  <div
                    v-for="dataset in datasetEntries"
                    :key="dataset.table_name"
                    class="mb-2 rounded-lg bg-[var(--color-base-soft)] px-4 py-3"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="min-w-0">
                        <div class="flex flex-wrap items-center gap-2">
                          <p class="min-w-0 truncate text-sm font-medium text-[var(--color-text-main)]">{{ dataset.filename }}</p>
                          <span
                            class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
                            :class="datasetSchemaStatusBadgeClass(dataset)"
                          >
                            {{ datasetSchemaStatusLabel(dataset) }}
                          </span>
                        </div>
                      </div>
                      <div class="flex items-center gap-1">
                        <button
                          type="button"
                          class="rounded p-1 text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)] disabled:cursor-not-allowed disabled:opacity-50"
                          title="Regenerate schema"
                          :disabled="isDatasetIngesting || isDeletingDataset || isSchemaRegenerateSubmitting"
                          @click="requestRegenerateDatasetSchema(dataset)"
                        >
                          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                            <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                            <path d="M20 4v6h-6" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          class="rounded p-1 text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)] disabled:cursor-not-allowed disabled:opacity-50"
                          title="Remove dataset"
                          :disabled="isDatasetIngesting || isDeletingDataset"
                          @click="requestRemoveDataset(dataset)"
                        >
                          <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                            <path d="M5 7h14" />
                            <path d="M9 7V5h6v2" />
                            <path d="M8 7l1 12h6l1-12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    <p class="mt-1 text-xs text-[var(--color-text-muted)]">
                      {{ datasetMetadata(dataset) }}
                    </p>
                  </div>
                </div>

                <!-- Empty Upload Dropzone -->
                <div
                  v-else
                  class="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-base-soft)]/50 px-5 py-6 text-center cursor-pointer hover:bg-[var(--color-base-soft)]/80 transition-colors"
                  data-testid="workspace-import-datasets-empty"
                  @click="openDatasetPicker"
                >
                  <p class="text-sm font-medium text-[var(--color-text-main)]">No datasets loaded yet.</p>
                  <p class="mt-1 text-sm text-[var(--color-text-muted)]">Import one or more files to start profiling data and generating schemas automatically.</p>
                  <button
                    type="button"
                    class="btn-primary mt-4 px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="isDatasetIngesting || isDeletingDataset || requiresWorkspaceActivation"
                    @click.stop="openDatasetPicker"
                  >
                    <span v-if="isDatasetIngesting">Processing dataset...</span>
                    <span v-else-if="requiresWorkspaceActivation">Activate workspace to add data</span>
                    <span v-else>Import datasets</span>
                  </button>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>

    </div>

    <!-- Confirmations -->
    <ConfirmationModal
      :is-open="isDatasetDeleteDialogOpen"
      title="Delete Dataset"
      :message="datasetDeleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeDatasetDeleteDialog"
      @confirm="confirmRemoveDataset"
    />

    <ConfirmationModal
      :is-open="isWorkspaceDeleteDialogOpen"
      title="Delete Workspace"
      :message="workspaceDeleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeWorkspaceDeleteDialog"
      @confirm="deleteWorkspace"
    />

    <ConfirmationModal
      :is-open="isSchemaRegenerateDialogOpen"
      title="Regenerate Schema"
      :message="schemaRegenerateDialogMessage"
      confirm-text="Regenerate"
      cancel-text="Cancel"
      @close="closeSchemaRegenerateDialog"
      @confirm="confirmRegenerateDatasetSchema"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { apiService } from '../../../services/apiService'
import { previewService } from '../../../services/previewService'
import { settingsWebSocket } from '../../../services/websocketService'
import { useAppStore } from '../../../stores/appStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import ConfirmationModal from '../ConfirmationModal.vue'

const props = defineProps({
  panelMode: {
    type: String,
    default: 'ws-list',
  },
  activeWorkspaceId: {
    type: String,
    default: '',
  },
  workspaces: {
    type: Array,
    default: () => [],
  },
  requestedSetupStep: {
    type: Number,
    default: 1,
  },
  workspaceIdentityDraft: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['navigate', 'select-workspace', 'activate-workspace', 'workspace-operation-change', 'workspace-created'])

const appStore = useAppStore()

const workspaceSummaries = ref({})
const workspaceDetail = ref(null)
const datasetEntries = ref([])
const datasetColumnCounts = ref({})
const datasetFileSizes = ref({})
const isDatasetIngesting = ref(false)
const datasetIngestFilename = ref('')
const datasetIngestMessage = ref('')
const datasetIngestPercent = ref(null)
const datasetIngestError = ref('')
const lastSelectedDatasetPaths = ref([])
const isDatasetDeleteDialogOpen = ref(false)
const pendingRemovalDataset = ref(null)
const isDeletingDataset = ref(false)
const isSchemaRegenerateDialogOpen = ref(false)
const pendingSchemaRegenerateDataset = ref(null)
const isSchemaRegenerateSubmitting = ref(false)
const isRenamingInline = ref(false)
const renameValue = ref('')
const renameInputRef = ref(null)
const isWorkspaceDeleteDialogOpen = ref(false)
const pendingWorkspaceDeletionId = ref('')
const datasetDeletionPollers = new Map()
const datasetIngestionPollers = new Map()
const pendingSchemaReadyNotifications = new Set()
let unsubscribeProgress = null
let unsubscribeRuntimeError = null
let unsubscribeRuntimeComplete = null
let datasetSchemaPoller = null

const isCreatingWorkspace = ref(false)
const isCreatingWorkspaceRuntime = ref(false)
const workspaceCreateMessage = ref('Saving the workspace name. You will add context next.')
const runtimeProgressEntries = ref([])
const runtimeProgressError = ref('')
const runtimeActionMode = ref('')
const isRetryingWorkspaceRuntime = ref(false)
const isHardResettingWorkspaceRuntime = ref(false)
const activeWorkspaceOperation = ref('')
const activeWorkspaceOperationMessage = ref('')
const setupStep = ref(1)
const setupWorkspaceName = ref('')
const setupWorkspaceContext = ref('')
const isSavingWorkspaceIdentity = ref(false)
const isCheckingWorkspaceReadiness = ref(false)
const setupSteps = [
  { id: 1, label: 'Name' },
  { id: 2, label: 'Context' },
  { id: 3, label: 'Data' },
]

const quickCreateName = ref('')
async function handleQuickCreate() {
  const name = String(quickCreateName.value || '').trim()
  if (!name) return
  setupWorkspaceName.value = name
  quickCreateName.value = ''
  await createWorkspace({ setupStep: 3 })
}

function normalizeWorkspaceName(value) {
  return String(value || '').toUpperCase()
}

const workspaceCards = computed(() => {
  const items = Array.isArray(props.workspaces) ? props.workspaces : []
  return items.map((workspace) => {
    const id = String(workspace?.id || '').trim()
    const name = String(workspace?.name || '').trim()
    const duckdbPath = String(workspace?.duckdb_path || '').trim()
    const filename = duckdbPath.split('/').pop() || 'workspace.duckdb'
    const summary = workspaceSummaries.value?.[id] || {}
    const conversationCount = Number(summary?.conversation_count || 0)
    const lastActive = String(workspace?.updated_at || '').trim()
    return {
      ...workspace,
      id,
      name,
      filename,
      conversationCount,
      lastActiveLabel: formatRelativeTime(lastActive),
    }
  })
})

const activeWorkspace = computed(() => workspaceCards.value.find((workspace) => workspace.id === String(props.activeWorkspaceId || '').trim()) || null)
const isCreatingMode = computed(() => props.panelMode === 'ws-create')
const isWorkspaceActive = computed(() => !!activeWorkspace.value && !!activeWorkspace.value.is_active)
const detailWorkspaceSelected = computed(() => Boolean(String(props.activeWorkspaceId || '').trim()))
const requiresWorkspaceActivation = computed(() => !isCreatingMode.value && !isWorkspaceActive.value)
const detailCreatedAt = computed(() => formatCreatedDate(workspaceDetail.value?.created_at || activeWorkspace.value?.created_at))
const detailConversationCount = computed(() => Number(workspaceDetail.value?.conversation_count || 0))
const detailLastActive = computed(() => formatRelativeTime(workspaceDetail.value?.updated_at || activeWorkspace.value?.updated_at))
const datasetIngestStatusLabel = computed(() => String(datasetIngestMessage.value || 'Processing dataset...').trim() || 'Processing dataset...')
const datasetIngestHasError = computed(() => Boolean(String(datasetIngestError.value || '').trim()))
const workspaceKernelStatus = computed(() => appStore.getWorkspaceKernelStatus(props.activeWorkspaceId))
const workspaceKernelReady = computed(() => ['ready', 'busy'].includes(workspaceKernelStatus.value))
const isRuntimeActionInProgress = computed(() => (
  isCreatingWorkspaceRuntime.value || isRetryingWorkspaceRuntime.value || isHardResettingWorkspaceRuntime.value
))
const runtimeStatusTone = computed(() => {
  if (runtimeProgressError.value) return 'danger'
  if (workspaceKernelReady.value) return 'success'
  if (isRuntimeActionInProgress.value || ['starting', 'connecting'].includes(String(workspaceKernelStatus.value || ''))) {
    return 'accent'
  }
  return 'muted'
})
const runtimeStatusLabel = computed(() => {
  if (runtimeProgressError.value) return 'Runtime failed'
  if (workspaceKernelStatus.value === 'busy') return 'Kernel busy'
  if (workspaceKernelStatus.value === 'ready') return 'Kernel ready'
  if (isHardResettingWorkspaceRuntime.value) return 'Hard reset in progress'
  if (isRetryingWorkspaceRuntime.value) return 'Retry in progress'
  if (isCreatingWorkspaceRuntime.value) return 'Preparing runtime'
  if (workspaceKernelStatus.value === 'starting' || workspaceKernelStatus.value === 'connecting') return 'Starting runtime'
  if (workspaceKernelStatus.value === 'error') return 'Runtime needs attention'
  return 'Runtime not started'
})
const runtimeStatusMessage = computed(() => {
  if (runtimeProgressError.value) return runtimeProgressError.value
  const latestEntry = runtimeProgressEntries.value[runtimeProgressEntries.value.length - 1]
  if (latestEntry?.message) return latestEntry.message
  const fallback = readinessKernelDetail(workspaceKernelStatus.value)
  return fallback === 'Runtime is connected' ? '' : fallback
})
const currentRuntimeProgressMessage = computed(() => {
  const latestEntry = runtimeProgressEntries.value[runtimeProgressEntries.value.length - 1]
  return String(latestEntry?.message || '').trim()
})
const workspaceReadinessItems = computed(() => {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const draft = resolveWorkspaceIdentityDraft()
  const registeredName = String(activeWorkspace.value?.name || draft?.name || '').trim()
  const context = String(resolveWorkspaceContext()).trim()
  const registered = Boolean(workspaceId && registeredName)
  const active = Boolean(workspaceId && String(appStore.activeWorkspaceId || '').trim() === workspaceId)
  const kernelStatus = String(workspaceKernelStatus.value || 'missing').trim()
  const kernelChecking = isCreatingWorkspaceRuntime.value || isCheckingWorkspaceReadiness.value || ['starting', 'connecting'].includes(kernelStatus)

  return [
    {
      id: 'workspace',
      label: 'Workspace saved',
      detail: registered ? registeredName : 'Waiting for workspace record',
      state: registered ? 'done' : 'pending',
    },
    {
      id: 'context',
      label: 'Context saved',
      detail: context ? 'Shared schema context is ready' : 'No shared context added',
      state: registered ? 'done' : 'pending',
    },
    {
      id: 'active',
      label: 'Workspace active',
      detail: active ? 'New datasets will attach here' : 'Waiting for active workspace',
      state: active ? 'done' : 'pending',
    },
    {
      id: 'kernel',
      label: 'Kernel ready',
      detail: readinessKernelDetail(kernelStatus),
      state: workspaceKernelReady.value ? 'done' : (kernelChecking ? 'checking' : 'pending'),
    },
  ]
})
const workspaceReadinessDoneCount = computed(() => workspaceReadinessItems.value.filter((item) => item.state === 'done').length)
const workspaceReadinessProgress = computed(() => Math.round((workspaceReadinessDoneCount.value / workspaceReadinessItems.value.length) * 100))
const workspaceReadinessComplete = computed(() => workspaceReadinessDoneCount.value === workspaceReadinessItems.value.length)
const workspaceReadinessTitle = computed(() => (
  workspaceReadinessComplete.value
    ? 'Ready for datasets'
    : `${workspaceReadinessDoneCount.value} of ${workspaceReadinessItems.value.length} checks ready`
))
const workspaceReadinessSummary = computed(() => (
  workspaceReadinessComplete.value
    ? 'Workspace setup is saved, active, and connected. Upload datasets when you are ready.'
    : 'Workspace setup is still settling. If the runtime stalls, retry it here before uploading data.'
))
const workspaceCreateTitle = computed(() => 'Creating workspace inside Settings...')
const workspaceDeleteDialogMessage = computed(() => {
  const targetId = String(pendingWorkspaceDeletionId.value || props.activeWorkspaceId || '').trim()
  const target = workspaceCards.value.find((workspace) => workspace.id === targetId)
  const name = String(target?.name || 'this workspace').trim()
  return `Are you sure you want to delete "${name}"? Cleanup will run in the background and cannot be undone.`
})
const datasetDeleteDialogMessage = computed(() => {
  const filename = String(pendingRemovalDataset.value?.filename || '').trim()
  return `Are you sure you want to delete "${filename || 'this dataset'}"? Dataset disappears immediately while storage cleanup continues in background.`
})
const schemaRegenerateDialogMessage = computed(() => {
  const filename = String(pendingSchemaRegenerateDataset.value?.filename || '').trim()
  return `Regenerated schema may differ from the current version because it is generated by the LLM. Continue regenerating "${filename || 'this dataset'}"?`
})
watch(
  () => props.panelMode,
  async (nextMode) => {
    if (nextMode === 'ws-list') {
      stopDatasetSchemaPolling()
      await hydrateWorkspaceCards()
    }
    if (nextMode === 'ws-detail') {
      await loadWorkspaceDetail()
      await loadWorkspaceDatasets()
      await loadActiveDatasetDeletionJobs()
      syncSetupIdentity()
    }
    if (nextMode === 'ws-create') {
      stopDatasetSchemaPolling()
      setupStep.value = 1
      setupWorkspaceName.value = ''
      setupWorkspaceContext.value = ''
    }
  },
  { immediate: true },
)

watch(
  () => props.workspaces,
  async () => {
    if (props.panelMode === 'ws-list') {
      await hydrateWorkspaceCards()
    }
  },
  { deep: true },
)

watch(
  () => setupWorkspaceName.value,
  (nextValue) => {
    const normalized = normalizeWorkspaceName(nextValue)
    if (normalized === nextValue) return
    setupWorkspaceName.value = normalized
  },
)

watch(
  () => props.activeWorkspaceId,
  async () => {
    if (props.panelMode !== 'ws-detail') return
    await loadWorkspaceDetail()
    await loadWorkspaceDatasets()
    await loadActiveDatasetDeletionJobs()
    syncSetupIdentity()
  },
)

watch(
  () => props.requestedSetupStep,
  (nextStep) => {
    if (props.panelMode !== 'ws-detail') return
    const normalized = Number(nextStep)
    if (![1, 2, 3].includes(normalized)) return
    setupStep.value = normalized
  },
  { immediate: true },
)

watch(
  () => props.workspaceIdentityDraft,
  () => {
    if (props.panelMode !== 'ws-detail') return
    syncSetupIdentity()
  },
  { deep: true },
)

watch(
  () => setupStep.value,
  (nextStep) => {
    if (props.panelMode !== 'ws-detail') return
    if (Number(nextStep) !== 1) return
    syncSetupIdentity()
  },
)

onMounted(async () => {
  unsubscribeProgress = settingsWebSocket.subscribeProgress(handleSettingsProgressUpdate)
  unsubscribeRuntimeError = settingsWebSocket.subscribeError(handleRuntimeSocketError)
  unsubscribeRuntimeComplete = settingsWebSocket.subscribeComplete(handleRuntimeSocketComplete)
  if (props.panelMode === 'ws-list') {
    await hydrateWorkspaceCards()
  }
  if (props.panelMode === 'ws-detail') {
    await loadActiveDatasetDeletionJobs()
    syncSetupIdentity()
  }
})

onUnmounted(() => {
  if (typeof unsubscribeProgress === 'function') {
    unsubscribeProgress()
    unsubscribeProgress = null
  }
  if (typeof unsubscribeRuntimeError === 'function') {
    unsubscribeRuntimeError()
    unsubscribeRuntimeError = null
  }
  if (typeof unsubscribeRuntimeComplete === 'function') {
    unsubscribeRuntimeComplete()
    unsubscribeRuntimeComplete = null
  }
  clearWorkspaceOperation()
  stopDatasetDeletionPollers()
  stopDatasetIngestionPollers()
  stopDatasetSchemaPolling()
})

async function hydrateWorkspaceCards() {
  const ids = workspaceCards.value.map((workspace) => workspace.id).filter(Boolean)
  if (!ids.length) {
    workspaceSummaries.value = {}
    return
  }
  const summaries = {}
  await Promise.all(
    ids.map(async (workspaceId) => {
      try {
        const summary = await apiService.v1GetWorkspaceSummary(workspaceId)
        summaries[workspaceId] = summary
      } catch {
        summaries[workspaceId] = {}
      }
    }),
  )
  workspaceSummaries.value = summaries
}

async function openWorkspaceDetail(workspaceId) {
  await emitSelectedWorkspace(workspaceId)
  emit('navigate', 'ws-detail', 'forward')
}

async function emitSelectedWorkspace(workspaceId) {
  const id = String(workspaceId || '').trim()
  if (!id) return
  emit('select-workspace', id)
}

async function activateSelectedWorkspace() {
  const id = String(props.activeWorkspaceId || '').trim()
  if (!id) return
  emit('activate-workspace', id)
}

async function loadWorkspaceDetail() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    workspaceDetail.value = null
    syncSetupIdentity()
    return
  }
  try {
    workspaceDetail.value = await apiService.v1GetWorkspaceSummary(workspaceId)
  } catch {
    workspaceDetail.value = null
  } finally {
    syncSetupIdentity()
  }
}

function resolveWorkspaceContext() {
  const draft = resolveWorkspaceIdentityDraft()
  return String(workspaceDetail.value?.schema_context ?? activeWorkspace.value?.schema_context ?? draft?.context ?? '').trim()
}

function resolveWorkspaceIdentityDraft() {
  const draft = props.workspaceIdentityDraft
  const draftWorkspaceId = String(draft?.workspaceId || '').trim()
  const activeId = String(props.activeWorkspaceId || '').trim()
  if (!draftWorkspaceId || draftWorkspaceId !== activeId) return null
  return {
    name: String(draft?.name || '').trim(),
    context: String(draft?.context || '').trim(),
  }
}

function syncSetupIdentity() {
  if (props.panelMode !== 'ws-detail') return
  const draft = resolveWorkspaceIdentityDraft()
  setupWorkspaceName.value = normalizeWorkspaceName(String(activeWorkspace.value?.name || draft?.name || '').trim())
  setupWorkspaceContext.value = resolveWorkspaceContext()
}

async function goToSetupStep(stepId) {
  if (notifyWorkspaceOperationBlocked()) return
  const normalized = Number(stepId)
  if (![1, 2, 3].includes(normalized)) return
  if (props.panelMode === 'ws-create' && normalized !== 1) {
    await createWorkspace({ setupStep: normalized })
    return
  }
  if (props.panelMode === 'ws-detail' && setupStep.value === 1 && normalized > 1) {
    const persisted = await ensureWorkspaceNamePersisted({ silent: true })
    if (!persisted) return
  }
  if (props.panelMode === 'ws-detail' && setupStep.value === 2 && normalized > 2 && setupWorkspaceContext.value.trim()) {
    const persisted = await ensureWorkspaceContextPersisted({ silent: true })
    if (!persisted) return
  }
  setupStep.value = normalized
}

async function continueFromWorkspaceName() {
  if (props.panelMode === 'ws-create') {
    await createWorkspace({ setupStep: 2 })
    return
  }
  await saveWorkspaceNameAndContinue()
}

async function saveWorkspaceNameAndContinue() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || '').trim()
  if (!workspaceId) return
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  const persisted = await ensureWorkspaceNamePersisted()
  if (!persisted) return
  setupStep.value = 2
}

async function skipWorkspaceContext() {
  setupStep.value = 3
}

async function saveWorkspaceContextAndContinue() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  if (!String(setupWorkspaceContext.value || '').trim()) return
  const persisted = await ensureWorkspaceContextPersisted()
  if (!persisted) return
  setupStep.value = 3
}

async function continueFromWorkspaceContext() {
  if (!String(setupWorkspaceContext.value || '').trim()) {
    await skipWorkspaceContext()
    return
  }
  await saveWorkspaceContextAndContinue()
}

async function ensureWorkspaceNamePersisted({ silent = false } = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || '').trim()
  if (!workspaceId || !name) {
    if (!silent) {
      toast.error('Workspace name required', 'Enter a workspace name to continue.')
    }
    return false
  }

  const currentContext = resolveWorkspaceContext()
  return ensureWorkspaceIdentityPersisted({
    name,
    context: currentContext,
    silent,
    successMessage: 'Workspace name updated.',
  })
}

async function ensureWorkspaceContextPersisted({ silent = false } = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(setupWorkspaceName.value || activeWorkspace.value?.name || '').trim()
  if (!workspaceId || !name) {
    if (!silent) {
      toast.error('Workspace name required', 'Enter a workspace name before saving context.')
    }
    return false
  }
  const context = String(setupWorkspaceContext.value || '').trim()
  return ensureWorkspaceIdentityPersisted({
    name,
    context,
    silent,
    successMessage: 'Workspace context updated.',
  })
}

async function ensureWorkspaceIdentityPersisted({
  name,
  context,
  silent = false,
  successMessage = 'Workspace updated.',
} = {}) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const normalizedName = String(name || '').trim()
  if (!workspaceId || !normalizedName) return false
  const currentName = String(activeWorkspace.value?.name || '').trim()
  const currentContext = resolveWorkspaceContext()
  const unchanged = normalizedName === currentName && context === currentContext
  if (unchanged) return true

  isSavingWorkspaceIdentity.value = true
  try {
    await appStore.renameWorkspace(workspaceId, normalizedName, context)
    await appStore.fetchWorkspaces()
    await loadWorkspaceDetail()
    if (!silent) {
      toast.success('Workspace saved', successMessage)
    }
    return true
  } catch (error) {
    if (!silent) {
      toast.error('Save failed', extractApiErrorMessage(error, 'Failed to save workspace.'))
    } else {
      toast.error('Save failed', extractApiErrorMessage(error, 'Failed to save workspace before continuing.'))
    }
    return false
  } finally {
    isSavingWorkspaceIdentity.value = false
  }
}

async function loadWorkspaceDatasets() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    datasetEntries.value = []
    return
  }
  try {
    const response = await apiService.v1ListDatasets(workspaceId)
    const datasets = Array.isArray(response?.datasets) ? response.datasets : []
    datasetEntries.value = datasets.map((item) => ({
      table_name: String(item?.table_name || '').trim(),
      source_path: String(item?.source_path || '').trim(),
      row_count: Number.isFinite(Number(item?.row_count)) ? Number(item.row_count) : null,
      file_type: String(item?.file_type || '').trim().toLowerCase(),
      schema_status: String(item?.schema_status || 'queued').trim().toLowerCase(),
      schema_error_message: String(item?.schema_error_message || '').trim(),
      schema_updated_at: String(item?.schema_updated_at || '').trim(),
      filename: formatFilename(item?.source_path || item?.table_name || ''),
    })).filter((item) => item.table_name)
    await enrichDatasetMetadata(workspaceId)
    notifyReadyDatasetSchemas(datasetEntries.value)
    syncDatasetSchemaPolling()
  } catch (error) {
    datasetEntries.value = []
    stopDatasetSchemaPolling()
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to load datasets.'))
  }
}

function startDatasetIngest(path) {
  const normalizedPath = String(path || '').trim()
  isDatasetIngesting.value = true
  datasetIngestFilename.value = formatFilename(normalizedPath)
  datasetIngestMessage.value = 'Preparing dataset ingestion...'
  datasetIngestPercent.value = null
  datasetIngestError.value = ''
}

function appendRuntimeProgress(stage, message) {
  const normalizedMessage = String(message || '').trim()
  if (!normalizedMessage) return
  const previous = runtimeProgressEntries.value[runtimeProgressEntries.value.length - 1]
  if (previous?.message === normalizedMessage) return
  runtimeProgressEntries.value = [
    ...runtimeProgressEntries.value.slice(-7),
    {
      stage: String(stage || '').trim(),
      message: normalizedMessage,
    },
  ]
}

function clearRuntimeProgress({ preserveError = false } = {}) {
  runtimeProgressEntries.value = []
  if (!preserveError) {
    runtimeProgressError.value = ''
  }
}

function resetRuntimeActionFlags() {
  isCreatingWorkspaceRuntime.value = false
  isRetryingWorkspaceRuntime.value = false
  isHardResettingWorkspaceRuntime.value = false
  runtimeActionMode.value = ''
}

function applyDatasetSelectionFromUpload(uploadResult, fallbackPath = '') {
  const resolvedPath = String(uploadResult?.file_path || fallbackPath || '').trim()
  const resolvedTableName = String(uploadResult?.table_name || '').trim()
  const resolvedColumns = Array.isArray(uploadResult?.columns) ? uploadResult.columns : []
  if (!resolvedPath && !resolvedTableName) return

  appStore.setDataFilePath(resolvedPath)
  appStore.setIngestedTableName(resolvedTableName)
  appStore.setIngestedColumns(resolvedColumns)
  appStore.setSchemaFileId(resolvedPath || resolvedTableName)

  window.dispatchEvent(new CustomEvent('dataset-switched', {
    detail: {
      tableName: resolvedTableName || null,
      dataPath: resolvedPath || null,
    },
  }))
}

function dispatchDatasetSchemaReady(dataset) {
  const tableName = String(dataset?.table_name || '').trim()
  if (!tableName) return
  window.dispatchEvent(new CustomEvent('dataset-schema-ready', {
    detail: {
      workspaceId: String(props.activeWorkspaceId || '').trim() || null,
      tableName,
      dataPath: String(dataset?.source_path || '').trim() || null,
    },
  }))
}

function trackSchemaReadyNotificationsFromIngestionJob(job) {
  const items = Array.isArray(job?.items) ? job.items : []
  items.forEach((item) => {
    if (String(item?.status || '').toLowerCase() !== 'completed') return
    const tableName = String(item?.table_name || '').trim()
    if (tableName) {
      pendingSchemaReadyNotifications.add(tableName)
    }
  })
}

function notifyReadyDatasetSchemas(datasets) {
  if (pendingSchemaReadyNotifications.size === 0) return
  const entries = Array.isArray(datasets) ? datasets : []
  entries.forEach((dataset) => {
    const tableName = String(dataset?.table_name || '').trim()
    if (!tableName || !pendingSchemaReadyNotifications.has(tableName)) return
    const status = datasetSchemaStatusState(dataset)
    if (status === 'ready') {
      pendingSchemaReadyNotifications.delete(tableName)
      toast.success('Schema ready', `Schema is ready for ${formatFilename(tableName)}.`)
      dispatchDatasetSchemaReady(dataset)
    } else if (status === 'failed') {
      pendingSchemaReadyNotifications.delete(tableName)
      toast.error('Schema generation failed', dataset?.schema_error_message || `Schema generation failed for ${formatFilename(tableName)}.`)
      dispatchDatasetSchemaReady(dataset)
    }
  })
}

function finishDatasetIngest() {
  isDatasetIngesting.value = false
  datasetIngestFilename.value = ''
  datasetIngestMessage.value = ''
  datasetIngestPercent.value = null
  datasetIngestError.value = ''
  lastSelectedDatasetPaths.value = []
}

function markDatasetIngestFailed(message) {
  isDatasetIngesting.value = true
  datasetIngestError.value = String(message || 'Failed to import dataset.').trim() || 'Failed to import dataset.'
  datasetIngestMessage.value = datasetIngestError.value
  datasetIngestPercent.value = 100
}

function handleSettingsProgressUpdate(data) {
  if (!data || data.type !== 'progress') return
  const stage = String(data?.stage || '').trim().toLowerCase()
  if (stage.startsWith('workspace_runtime')) {
    runtimeProgressError.value = ''
    appendRuntimeProgress(stage, data?.message || '')
    if (isCreatingWorkspace.value && props.panelMode === 'ws-create') {
      isCreatingWorkspaceRuntime.value = true
      workspaceCreateMessage.value = String(data?.message || '').trim() || 'Preparing workspace runtime...'
    }
    return
  }
  if (!isDatasetIngesting.value) return
  const nextMessage = String(data?.message || '').trim()
  if (nextMessage) {
    datasetIngestMessage.value = nextMessage
  }
  const percent = Number(data?.progress)
  if (Number.isFinite(percent) && percent >= 0 && percent <= 100) {
    datasetIngestPercent.value = Math.round(percent)
  }
}

function handleRuntimeSocketError(message) {
  if (!isRuntimeActionInProgress.value && !isCreatingWorkspace.value) return
  runtimeProgressError.value = String(message || 'Workspace runtime failed.').trim() || 'Workspace runtime failed.'
  appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
  resetRuntimeActionFlags()
}

function handleRuntimeSocketComplete(result) {
  const workspaceId = String(result?.workspace_id || '').trim()
  if (!workspaceId || workspaceId !== String(props.activeWorkspaceId || '').trim()) return
  if (!isRuntimeActionInProgress.value && !isCreatingWorkspace.value) return
  clearRuntimeProgress()
  resetRuntimeActionFlags()
}

function setWorkspaceOperation(operation, message) {
  const normalizedOperation = String(operation || '').trim()
  const normalizedMessage = String(message || 'Workspace setup is still running.').trim()
  activeWorkspaceOperation.value = normalizedOperation
  activeWorkspaceOperationMessage.value = normalizedMessage
  emit('workspace-operation-change', {
    locked: Boolean(normalizedOperation),
    operation: normalizedOperation,
    message: normalizedMessage,
  })
}

function clearWorkspaceOperation() {
  activeWorkspaceOperation.value = ''
  activeWorkspaceOperationMessage.value = ''
  emit('workspace-operation-change', { locked: false, operation: '', message: '' })
}

function notifyWorkspaceOperationBlocked() {
  if (!activeWorkspaceOperation.value) return false
  toast.info(
    'Workspace setup in progress',
    activeWorkspaceOperationMessage.value || 'Wait for the current workspace setup step to finish.',
  )
  return true
}

function readinessKernelDetail(status) {
  const normalized = String(status || '').trim()
  if (normalized === 'ready') return 'Runtime is connected'
  if (normalized === 'busy') return 'Runtime is busy but available'
  if (normalized === 'starting' || normalized === 'connecting') return 'Runtime is starting'
  if (normalized === 'error') return 'Runtime needs attention'
  return 'Runtime not prepared yet'
}

function readinessItemClass(item) {
  const state = String(item?.state || '').trim()
  if (state === 'done') return 'workspace-readiness-item-done'
  if (state === 'checking') return 'workspace-readiness-item-checking'
  return 'workspace-readiness-item-pending'
}

function readinessDotClass(item) {
  const state = String(item?.state || '').trim()
  if (state === 'done') return 'workspace-readiness-dot-done'
  if (state === 'checking') return 'workspace-readiness-dot-checking'
  return 'workspace-readiness-dot-pending'
}

async function refreshWorkspaceReadiness() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || isCheckingWorkspaceReadiness.value) return
  isCheckingWorkspaceReadiness.value = true
  clearRuntimeProgress()
  try {
    const ready = await appStore.ensureWorkspaceKernelConnected(workspaceId)
    if (ready) {
      toast.success('Workspace ready', 'Runtime is ready for dataset uploads.')
    } else {
      toast.error('Runtime not ready', String(appStore.runtimeError || 'Workspace runtime is still starting.'))
    }
  } catch (error) {
    toast.error('Runtime check failed', extractApiErrorMessage(error, 'Failed to prepare workspace runtime.'))
  } finally {
    isCheckingWorkspaceReadiness.value = false
  }
}

async function retryWorkspaceRuntime() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || isRetryingWorkspaceRuntime.value || isHardResettingWorkspaceRuntime.value) return
  clearRuntimeProgress()
  runtimeActionMode.value = 'retry'
  isRetryingWorkspaceRuntime.value = true
  setWorkspaceOperation('runtime', 'Retrying the workspace runtime.')
  appStore.clearWorkspaceKernelStatus(workspaceId)
  try {
    const response = await apiService.v1RetryWorkspaceRuntime(workspaceId)
    await appStore.fetchWorkspaces()
    if (!response?.reset) {
      throw new Error('Workspace runtime retry did not finish successfully.')
    }
    appStore.setWorkspaceKernelStatus(workspaceId, 'ready')
    clearRuntimeProgress()
    toast.success('Runtime ready', 'Workspace runtime restarted successfully.')
  } catch (error) {
    runtimeProgressError.value = extractApiErrorMessage(error, 'Failed to retry workspace runtime.')
    appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
    appStore.setWorkspaceKernelStatus(workspaceId, 'error')
    toast.error('Runtime retry failed', runtimeProgressError.value)
  } finally {
    isRetryingWorkspaceRuntime.value = false
    runtimeActionMode.value = ''
    clearWorkspaceOperation()
  }
}

async function hardResetWorkspaceRuntime() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId || isRetryingWorkspaceRuntime.value || isHardResettingWorkspaceRuntime.value) return
  clearRuntimeProgress()
  runtimeActionMode.value = 'hard-reset'
  isHardResettingWorkspaceRuntime.value = true
  setWorkspaceOperation('runtime', 'Rebuilding the workspace runtime from scratch.')
  appStore.clearWorkspaceKernelStatus(workspaceId)
  try {
    const response = await apiService.v1HardResetWorkspaceRuntime(workspaceId)
    await appStore.fetchWorkspaces()
    if (!response?.reset) {
      throw new Error('Workspace hard reset did not finish successfully.')
    }
    appStore.setWorkspaceKernelStatus(workspaceId, 'ready')
    clearRuntimeProgress()
    toast.success('Runtime rebuilt', 'Workspace runtime was rebuilt from scratch.')
  } catch (error) {
    runtimeProgressError.value = extractApiErrorMessage(error, 'Failed to rebuild workspace runtime.')
    appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
    appStore.setWorkspaceKernelStatus(workspaceId, 'error')
    toast.error('Hard reset failed', runtimeProgressError.value)
  } finally {
    isHardResettingWorkspaceRuntime.value = false
    runtimeActionMode.value = ''
    clearWorkspaceOperation()
  }
}

function stopDatasetDeletionPollers() {
  datasetDeletionPollers.forEach((timerId) => clearTimeout(timerId))
  datasetDeletionPollers.clear()
}

function stopDatasetIngestionPollers() {
  datasetIngestionPollers.forEach((timerId) => clearTimeout(timerId))
  datasetIngestionPollers.clear()
}

function trackDatasetDeletionJob(workspaceId, jobId, datasetLabel, timeoutMs = 300000) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const normalizedJobId = String(jobId || '').trim()
  if (!normalizedWorkspaceId || !normalizedJobId) return
  if (datasetDeletionPollers.has(normalizedJobId)) return
  const startedAt = Date.now()
  const displayName = String(datasetLabel || '').trim() || 'dataset'

  const poll = async () => {
    try {
      const job = await apiService.v1GetDatasetDeletionJob(normalizedWorkspaceId, normalizedJobId)
      const status = String(job?.status || '').trim().toLowerCase()
      if (status === 'completed') {
        datasetDeletionPollers.delete(normalizedJobId)
        toast.success('Dataset deletion completed', `"${displayName}" cleanup finished.`)
        return
      }
      if (status === 'failed') {
        datasetDeletionPollers.delete(normalizedJobId)
        const detail = String(job?.error_message || '').trim()
        toast.error('Dataset deletion failed', detail || `Background cleanup failed for "${displayName}".`)
        return
      }
      if (Date.now() - startedAt > timeoutMs) {
        datasetDeletionPollers.delete(normalizedJobId)
        toast.info('Dataset cleanup still running', `Background cleanup for "${displayName}" is still in progress.`)
        return
      }
      const timer = setTimeout(poll, 2000)
      datasetDeletionPollers.set(normalizedJobId, timer)
    } catch (_error) {
      datasetDeletionPollers.delete(normalizedJobId)
    }
  }

  poll()
}

function applyDatasetSelectionFromIngestionJob(job) {
  const items = Array.isArray(job?.items) ? job.items : []
  const firstCompleted = items.find((item) => String(item?.status || '').toLowerCase() === 'completed')
  if (!firstCompleted) return
  applyDatasetSelectionFromUpload({
    file_path: firstCompleted.source_path || '',
    table_name: firstCompleted.table_name || '',
    columns: [],
  }, firstCompleted.source_path || '')
}

function trackDatasetIngestionJob(workspaceId, jobId, timeoutMs = Infinity) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const normalizedJobId = String(jobId || '').trim()
  if (!normalizedWorkspaceId || !normalizedJobId) return
  if (datasetIngestionPollers.has(normalizedJobId)) return
  const startedAt = Date.now()

  const poll = async () => {
    try {
      const job = await apiService.v1GetDatasetIngestionJob(normalizedWorkspaceId, normalizedJobId)
      const status = String(job?.status || '').trim().toLowerCase()
      const completed = Number(job?.completed_count || 0)
      const failed = Number(job?.failed_count || 0)
      const total = Number(job?.total_count || 0)
      if (total > 0) {
        datasetIngestPercent.value = Math.round(((completed + failed) / total) * 100)
      }
      datasetIngestMessage.value = `Processed ${completed + failed} of ${total || '?'} datasets`

      if (['completed', 'completed_with_errors', 'failed'].includes(status)) {
        datasetIngestionPollers.delete(normalizedJobId)
        applyDatasetSelectionFromIngestionJob(job)
        trackSchemaReadyNotificationsFromIngestionJob(job)
        await loadWorkspaceDatasets()
        const failedCount = Number(job?.failed_count || 0)
        datasetIngestPercent.value = 100
        datasetIngestMessage.value = failedCount > 0
          ? `Completed with ${failedCount} failed import${failedCount === 1 ? '' : 's'}.`
          : 'Import complete.'
        await new Promise((resolve) => setTimeout(resolve, 700))
        finishDatasetIngest()
        clearWorkspaceOperation()
        if (status === 'failed' || failedCount > 0) {
          toast.error('Dataset ingestion completed with errors', `${failedCount || 'Some'} file${failedCount === 1 ? '' : 's'} failed to import.`)
        }
        return
      }

      if (Date.now() - startedAt > timeoutMs) {
        datasetIngestionPollers.delete(normalizedJobId)
        finishDatasetIngest()
        clearWorkspaceOperation()
        toast.info('Dataset ingestion still running', 'Dataset import is still running in the background.')
        return
      }
      const timer = setTimeout(poll, 1500)
      datasetIngestionPollers.set(normalizedJobId, timer)
    } catch (error) {
      datasetIngestionPollers.delete(normalizedJobId)
      finishDatasetIngest()
      clearWorkspaceOperation()
      toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to poll dataset ingestion.'))
    }
  }

  poll()
}

async function startBatchDatasetIngestion(paths) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const sourcePaths = Array.isArray(paths)
    ? paths.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (!workspaceId || sourcePaths.length === 0) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before importing datasets.')
    return
  }
  const identityReady = await ensureWorkspaceNamePersisted({ silent: true })
  if (!identityReady) return

  startDatasetIngest(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths.length} selected files`)
  lastSelectedDatasetPaths.value = [...sourcePaths]
  setWorkspaceOperation('ingest', 'Importing selected datasets into the workspace.')
  datasetIngestMessage.value = 'Preparing workspace...'
  try {
    datasetIngestMessage.value = 'Queueing dataset ingestion...'
    const job = await apiService.v1AddDatasetsBatch(workspaceId, sourcePaths)
    const jobId = String(job?.job_id || '').trim()
    if (!jobId) {
      finishDatasetIngest()
      clearWorkspaceOperation()
      toast.error('Dataset Error', 'Backend did not return an ingestion job.')
      return
    }
    trackDatasetIngestionJob(workspaceId, jobId)
  } catch (error) {
    markDatasetIngestFailed(extractApiErrorMessage(error, 'Failed to queue dataset import.'))
    clearWorkspaceOperation()
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to add datasets.'))
  }
}

async function retryLastDatasetIngestion() {
  const paths = Array.isArray(lastSelectedDatasetPaths.value)
    ? lastSelectedDatasetPaths.value.map((item) => String(item || '').trim()).filter(Boolean)
    : []
  if (!paths.length) {
    toast.info('Retry unavailable', 'Select files again to retry import.')
    finishDatasetIngest()
    return
  }
  await startBatchDatasetIngestion(paths)
}

async function loadActiveDatasetDeletionJobs() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  try {
    const response = await apiService.v1ListDatasetDeletionJobs(workspaceId)
    const jobs = Array.isArray(response?.jobs) ? response.jobs : []
    jobs.forEach((job) => {
      const jobId = String(job?.job_id || '').trim()
      const label = formatFilename(job?.table_name || '')
      trackDatasetDeletionJob(workspaceId, jobId, label)
    })
  } catch (_error) {
    // Ignore hydration errors; explicit delete actions still start polling.
  }
}

async function enrichDatasetMetadata(workspaceId) {
  const columnCounts = {}
  const fileSizes = {}

  await Promise.all(
    datasetEntries.value.map(async (dataset) => {
      try {
        const schema = await apiService.v1GetDatasetSchema(workspaceId, dataset.table_name)
        const columns = Array.isArray(schema?.columns) ? schema.columns : []
        columnCounts[dataset.table_name] = columns.length
      } catch {
        columnCounts[dataset.table_name] = null
      }

      try {
        fileSizes[dataset.table_name] = await resolveDatasetFileSize(dataset.source_path)
      } catch {
        fileSizes[dataset.table_name] = null
      }
    }),
  )

  datasetColumnCounts.value = columnCounts
  datasetFileSizes.value = fileSizes
}

async function resolveDatasetFileSize(path) {
  const normalized = String(path || '').trim()
  if (!normalized || normalized.startsWith('browser://')) return null
  if (typeof window === 'undefined' || !window.__TAURI_INTERNALS__) return null
  const { stat } = await import('@tauri-apps/plugin-fs')
  const info = await stat(normalized)
  const bytes = Number(info?.size || 0)
  return Number.isFinite(bytes) && bytes > 0 ? bytes : null
}

function datasetRowCount(dataset) {
  const value = Number(dataset?.row_count || 0)
  return Number.isFinite(value) && value > 0 ? value.toLocaleString() : '?'
}

function datasetColumnCount(dataset) {
  const value = Number(datasetColumnCounts.value?.[dataset?.table_name] || 0)
  return Number.isFinite(value) && value > 0 ? value : '?'
}

function datasetFileSize(dataset) {
  const bytes = Number(datasetFileSizes.value?.[dataset?.table_name] || 0)
  if (!Number.isFinite(bytes) || bytes <= 0) return null
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}

function datasetMetadata(dataset) {
  const segments = [
    `${datasetRowCount(dataset)} rows`,
    `${datasetColumnCount(dataset)} cols`,
  ]
  const sizeLabel = datasetFileSize(dataset)
  if (sizeLabel) {
    segments.push(sizeLabel)
  }
  return segments.join(' · ')
}

function requestRemoveDataset(dataset) {
  if (!dataset || isDeletingDataset.value) return
  pendingRemovalDataset.value = dataset
  isDatasetDeleteDialogOpen.value = true
}

function closeDatasetDeleteDialog({ force = false } = {}) {
  if (isDeletingDataset.value && !force) return
  isDatasetDeleteDialogOpen.value = false
  pendingRemovalDataset.value = null
}

async function confirmRemoveDataset() {
  if (isDeletingDataset.value) return
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const dataset = pendingRemovalDataset.value
  const tableName = String(dataset?.table_name || '').trim()
  const datasetLabel = String(dataset?.filename || formatFilename(tableName)).trim()
  if (!workspaceId || !tableName) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before deleting datasets.')
    return
  }
  isDeletingDataset.value = true
  try {
    const job = await apiService.v1DeleteDataset(workspaceId, tableName)
    const deletedActiveDataset = appStore.handleDatasetRemoved(tableName)
    previewService.clearSchemaCache()
    window.dispatchEvent(new CustomEvent('dataset-switched', { detail: null }))
    await loadWorkspaceDatasets()
    closeDatasetDeleteDialog({ force: true })
    const jobId = String(job?.job_id || '').trim()
    if (jobId) {
      toast.info(
        'Dataset deletion started',
        deletedActiveDataset
          ? 'Dataset removed. Active selection cleared. Background cleanup started.'
          : 'Dataset removed from workspace. Background cleanup started.',
      )
      trackDatasetDeletionJob(workspaceId, jobId, datasetLabel)
    } else {
      toast.success(
        'Dataset removed',
        deletedActiveDataset ? 'Dataset removed. Active selection cleared.' : 'Dataset removed from workspace.',
      )
    }
  } catch (error) {
    toast.error('Remove failed', extractApiErrorMessage(error, 'Failed to remove dataset.'))
  } finally {
    isDeletingDataset.value = false
    if (!isDatasetDeleteDialogOpen.value) {
      pendingRemovalDataset.value = null
    }
  }
}

function requestRegenerateDatasetSchema(dataset) {
  if (!dataset || isSchemaRegenerateSubmitting.value) return
  pendingSchemaRegenerateDataset.value = dataset
  isSchemaRegenerateDialogOpen.value = true
}

function closeSchemaRegenerateDialog() {
  if (isSchemaRegenerateSubmitting.value) return
  isSchemaRegenerateDialogOpen.value = false
  pendingSchemaRegenerateDataset.value = null
}

async function confirmRegenerateDatasetSchema() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const dataset = pendingSchemaRegenerateDataset.value
  const tableName = String(dataset?.table_name || '').trim()
  if (!workspaceId || !tableName) return
  if (requiresWorkspaceActivation.value) {
    toast.info('Activate workspace first', 'Activate this workspace before generating schemas.')
    return
  }
  try {
    isSchemaRegenerateSubmitting.value = true
    await apiService.v1EnqueueDatasetSchemaRegeneration(workspaceId, tableName)
    await loadWorkspaceDatasets()
    toast.success('Schema regeneration queued', 'Schema generation will continue in the background.')
  } catch (error) {
    toast.error('Schema regeneration failed', extractApiErrorMessage(error, 'Failed to queue schema regeneration.'))
  } finally {
    isSchemaRegenerateSubmitting.value = false
    closeSchemaRegenerateDialog()
  }
}

async function openDatasetPicker() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: true,
      filters: [{ name: 'Data files', extensions: ['csv', 'parquet', 'xlsx', 'xls', 'json', 'tsv'] }],
    })
    const selectedPaths = Array.isArray(selected)
      ? selected.map((item) => String(item || '').trim()).filter(Boolean)
      : [String(selected || '').trim()].filter(Boolean)
    await startBatchDatasetIngestion(selectedPaths)
  } catch (error) {
    toast.error('Dataset Error', extractApiErrorMessage(error, 'Failed to add dataset.'))
  }
}

async function startRename() {
  renameValue.value = String(activeWorkspace.value?.name || '').trim()
  isRenamingInline.value = true
  await nextTick()
  renameInputRef.value?.focus?.()
  renameInputRef.value?.select?.()
}

function cancelRename() {
  isRenamingInline.value = false
  renameValue.value = ''
}

async function saveRename() {
  if (!isRenamingInline.value) return
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const name = String(renameValue.value || '').trim()
  const currentName = String(activeWorkspace.value?.name || '').trim()
  if (!workspaceId) {
    cancelRename()
    return
  }
  if (!name) {
    cancelRename()
    return
  }
  if (name === currentName) {
    cancelRename()
    return
  }
  try {
    await appStore.renameWorkspace(workspaceId, name, resolveWorkspaceContext())
    await appStore.fetchWorkspaces()
    isRenamingInline.value = false
    renameValue.value = ''
    toast.success('Workspace renamed', 'Workspace name updated.')
  } catch (error) {
    isRenamingInline.value = false
    renameValue.value = ''
    toast.error('Rename failed', extractApiErrorMessage(error, 'Failed to rename workspace.'))
  }
}


function requestDeleteWorkspace(workspaceId) {
  if (notifyWorkspaceOperationBlocked()) return
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  pendingWorkspaceDeletionId.value = normalizedWorkspaceId
  isWorkspaceDeleteDialogOpen.value = true
}

function closeWorkspaceDeleteDialog({ force = false } = {}) {
  if (activeWorkspaceOperation.value === 'delete' && !force) return
  isWorkspaceDeleteDialogOpen.value = false
  pendingWorkspaceDeletionId.value = ''
}

async function deleteWorkspace() {
  const workspaceId = String(pendingWorkspaceDeletionId.value || props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  setWorkspaceOperation('delete', 'Deleting workspace and starting background cleanup.')
  try {
    await appStore.deleteWorkspaceAsync(workspaceId)
    closeWorkspaceDeleteDialog({ force: true })
    await appStore.fetchWorkspaces()
    const fallbackId = String(appStore.activeWorkspaceId || workspaceCards.value[0]?.id || '').trim()
    if (fallbackId) {
      emit('select-workspace', fallbackId)
    }
    emit('navigate', 'ws-list', 'backward')
    toast.success('Workspace deletion started', 'Workspace deletion is running in background.')
  } catch (error) {
    toast.error('Delete failed', extractApiErrorMessage(error, 'Failed to delete workspace.'))
  } finally {
    clearWorkspaceOperation()
  }
}

async function createWorkspace({ setupStep: targetSetupStep = 2 } = {}) {
  const name = String(setupWorkspaceName.value || '').trim()
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  let workspaceId = ''
  isCreatingWorkspace.value = true
  isCreatingWorkspaceRuntime.value = false
  clearRuntimeProgress()
  runtimeActionMode.value = 'create'
  workspaceCreateMessage.value = 'Saving the workspace name. You will add context next.'
  setWorkspaceOperation('create', 'Creating workspace.')
  try {
    const context = ''
    const workspace = await appStore.createWorkspace(name, context)
    workspaceId = String(workspace?.id || appStore.activeWorkspaceId || '').trim()
    if (!workspaceId) {
      throw new Error('Backend did not return a workspace id.')
    }
    await appStore.fetchWorkspaces()
    emit('workspace-created', {
      workspaceId,
      name,
      context,
      setupStep: targetSetupStep,
    })
    isCreatingWorkspace.value = false
    clearWorkspaceOperation()
    setTimeout(() => {
      void warmWorkspaceRuntimeInBackground(workspaceId)
    }, 0)
  } catch (error) {
    toast.error('Create failed', extractApiErrorMessage(error, 'Failed to create workspace.'))
  } finally {
    isCreatingWorkspace.value = false
    if (!workspaceId) {
      isCreatingWorkspaceRuntime.value = false
      runtimeActionMode.value = ''
    }
    workspaceCreateMessage.value = 'Saving the workspace name. You will add context next.'
    clearWorkspaceOperation()
  }
}

async function warmWorkspaceRuntimeInBackground(workspaceId) {
  const targetWorkspaceId = String(workspaceId || '').trim()
  if (!targetWorkspaceId) return
  clearRuntimeProgress()
  try {
    const ready = await appStore.ensureWorkspaceKernelConnected(targetWorkspaceId)
    if (!ready) {
      runtimeProgressError.value = String(appStore.runtimeError || 'Workspace runtime bootstrap failed.')
      appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
      return
    }
    clearRuntimeProgress()
  } catch (error) {
    runtimeProgressError.value = extractApiErrorMessage(error, 'Workspace runtime bootstrap failed.')
    appendRuntimeProgress('workspace_runtime_error', runtimeProgressError.value)
    appStore.setWorkspaceKernelStatus(targetWorkspaceId, 'error')
  } finally {
    if (runtimeActionMode.value === 'create') {
      runtimeActionMode.value = ''
    }
  }
}

function datasetSchemaStatusState(dataset) {
  const persistedStatus = String(dataset?.schema_status || 'queued').trim().toLowerCase()
  if (['queued', 'generating', 'ready', 'failed'].includes(persistedStatus)) {
    return persistedStatus
  }
  return 'queued'
}

function datasetSchemaStatusLabel(dataset) {
  const status = datasetSchemaStatusState(dataset)
  if (status === 'generating') return 'Generating schema'
  if (status === 'ready') return 'Schema ready'
  if (status === 'failed') return 'Schema failed'
  return 'Schema queued'
}

function datasetSchemaStatusBadgeClass(dataset) {
  const status = datasetSchemaStatusState(dataset)
  if (status === 'generating') return 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
  if (status === 'ready') return 'bg-[var(--color-success-bg)] text-[var(--color-success)]'
  if (status === 'failed') return 'bg-[var(--color-danger-bg)] text-[var(--color-danger)]'
  return 'bg-[var(--color-base-muted)] text-[var(--color-text-muted)]'
}

function stopDatasetSchemaPolling() {
  if (datasetSchemaPoller !== null) {
    clearInterval(datasetSchemaPoller)
    datasetSchemaPoller = null
  }
}

function syncDatasetSchemaPolling() {
  const shouldPoll = datasetEntries.value.some((dataset) => {
    const status = datasetSchemaStatusState(dataset)
    return status === 'queued' || status === 'generating'
  })
  if (!shouldPoll) {
    stopDatasetSchemaPolling()
    return
  }
  if (datasetSchemaPoller !== null) return
  datasetSchemaPoller = setInterval(async () => {
    if (props.panelMode !== 'ws-detail' || setupStep.value !== 3) return
    await loadWorkspaceDatasets()
  }, 1500)
}

function stepDotClass(stepId) {
  if (setupStep.value === stepId) return 'border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-on-accent)] shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-accent)_20%,transparent)]'
  if (setupStep.value > stepId) return 'border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
  return 'border-[var(--color-border)] bg-[var(--color-base)] text-[var(--color-text-muted)]'
}

function stepLabelClass(stepId) {
  if (setupStep.value === stepId) return 'text-[var(--color-accent)] font-semibold'
  if (setupStep.value > stepId) return 'text-[var(--color-text-main)]'
  return 'text-[var(--color-text-muted)]'
}

function formatFilename(raw) {
  const value = String(raw || '').trim()
  if (!value) return 'dataset'
  const last = value.split('/').pop() || value
  return last
}

function formatCreatedDate(raw) {
  const value = String(raw || '').trim()
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatRelativeTime(raw) {
  const value = String(raw || '').trim()
  if (!value) return 'unknown'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 'unknown'
  const deltaMs = Date.now() - parsed.getTime()
  const minutes = Math.max(1, Math.round(deltaMs / 60000))
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 48) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}
</script>

<style scoped>
.workspace-readiness-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 1rem;
  padding: 1rem;
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--color-accent) 14%, transparent), transparent 34%),
    linear-gradient(135deg, color-mix(in srgb, var(--color-base-soft) 92%, var(--color-accent) 8%), var(--color-base));
  box-shadow: 0 14px 34px color-mix(in srgb, var(--color-text-main) 8%, transparent);
  transition:
    border-color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    box-shadow var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-readiness-card::before {
  content: '';
  position: absolute;
  inset: -35% auto auto 54%;
  height: 9rem;
  width: 9rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-accent) 10%, transparent);
  filter: blur(22px);
  pointer-events: none;
}

.workspace-readiness-card-ready {
  border-color: color-mix(in srgb, var(--color-success) 36%, var(--color-border));
}

.workspace-readiness-card-pending {
  border-color: color-mix(in srgb, var(--color-accent) 24%, var(--color-border));
}

.workspace-readiness-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.625rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  padding: 0.625rem;
  background: color-mix(in srgb, var(--color-base) 72%, transparent);
  transition:
    border-color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-readiness-item:hover {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--color-base) 88%, transparent);
}

.workspace-readiness-item-done {
  border-color: color-mix(in srgb, var(--color-success) 28%, var(--color-border));
}

.workspace-readiness-item-checking {
  border-color: color-mix(in srgb, var(--color-accent) 34%, var(--color-border));
}

.workspace-readiness-item-pending {
  opacity: 0.82;
}

.workspace-readiness-dot {
  display: inline-flex;
  height: 1.5rem;
  width: 1.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  transition:
    background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    transform var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-readiness-dot-done {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.workspace-readiness-dot-checking {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

.workspace-readiness-dot-pending {
  background: var(--color-base-muted);
  color: var(--color-text-muted);
}

.workspace-stepper {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0;
}

.workspace-stepper-item {
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  color: var(--color-text-muted);
  cursor: pointer;
}

.workspace-stepper-item:focus-visible {
  outline: none;
}

.workspace-stepper-line {
  position: absolute;
  right: 0;
  left: -50%;
  top: 1.25rem;
  height: 1.5px;
  background: var(--color-border);
  transition: background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.workspace-stepper-dot {
  position: relative;
  z-index: 1;
  display: inline-flex;
  height: 2.25rem;
  width: 2.25rem;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-border);
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  transition:
    background var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    border-color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    color var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease),
    box-shadow var(--motion-duration-standard, 200ms) var(--motion-ease-standard, ease);
}

.node-success {
  border-color: color-mix(in srgb, var(--color-success) 30%, transparent);
  background-color: color-mix(in srgb, var(--color-success) 5%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-success) 15%, transparent);
}
.node-danger {
  border-color: color-mix(in srgb, var(--color-danger) 30%, transparent);
  background-color: color-mix(in srgb, var(--color-danger) 5%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-danger) 15%, transparent);
}
.node-accent {
  border-color: color-mix(in srgb, var(--color-accent) 30%, transparent);
  background-color: color-mix(in srgb, var(--color-accent) 5%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-accent) 15%, transparent);
}
</style>
