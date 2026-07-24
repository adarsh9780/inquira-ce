<template>
  <section class="scrollbar-hidden h-full overflow-y-auto">
    <div class="grid h-full min-h-0 grid-cols-[210px_1fr] gap-4">
      <WorkspaceListPanel>
        <header class="mb-3 flex items-center justify-between">
          <h3 class="section-label">Workspaces</h3>
          <button type="button" class="text-xs font-semibold text-[var(--color-accent)] hover:underline" @click="beginInlineCreate">
            + New
          </button>
        </header>

        <div class="flex-1 space-y-1.5 overflow-y-auto pr-1 scrollbar-thin">
          <div
            v-if="isInlineCreating"
            class="rounded-lg bg-[var(--color-accent-soft)] px-3 py-2.5 ring-1 ring-[var(--color-accent-border)]"
          >
            <input
              ref="newWorkspaceInputRef"
              v-model="setupWorkspaceName"
              type="text"
              class="w-full bg-transparent text-xs font-medium text-[var(--color-text-main)] outline-none placeholder:text-[var(--color-text-muted)]"
              placeholder="New workspace name"
              :disabled="isCreatingWorkspace"
              @keydown.enter.prevent="createWorkspace"
              @keydown.escape.prevent="cancelInlineCreate"
            />
            <p class="mt-1 text-[10px] text-[var(--color-text-muted)]">Press Enter to create</p>
          </div>

          <div
            v-for="workspace in workspaceCards"
            :key="workspace.id"
            class="group relative flex w-full cursor-pointer flex-col rounded-lg px-2.5 py-2 text-left transition-all"
            :class="workspace.id === activeWorkspaceId
              ? 'bg-[var(--color-accent-soft)] ring-1 ring-[var(--color-accent-border)]'
              : 'bg-[var(--color-base-soft)] hover:bg-[var(--color-base-muted)]'"
            @click="selectWorkspaceSummary(workspace.id)"
          >
            <div class="flex items-start justify-between gap-2">
              <p class="min-w-0 flex-1 truncate text-xs font-medium text-[var(--color-text-main)]">{{ workspace.name || 'Untitled workspace' }}</p>
              <div class="flex shrink-0 items-center gap-1.5">
                <span v-if="workspace.id === activeWorkspaceId" class="rounded-full bg-[var(--color-accent-soft)] px-1.5 py-0.5 text-[9px] text-[var(--color-accent)]">Selected</span>
                <span v-if="workspace.id === workspaceStore.activeWorkspaceId" class="rounded-full bg-[var(--color-success-bg)] px-1.5 py-0.5 text-[9px] text-[var(--color-success)]">Active</span>
                <button
                  type="button"
                  class="rounded p-1 text-[var(--color-text-muted)] opacity-40 transition-all hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger)] focus-visible:opacity-100 group-hover:opacity-100"
                  title="Delete workspace"
                  aria-label="Delete workspace"
                  @click.stop="requestDeleteWorkspace(workspace.id)"
                >
                  <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M5 7h14" /><path d="M9 7V5h6v2" /><path d="M8 7l1 12h6l1-12" />
                  </svg>
                </button>
              </div>
            </div>
            <p class="mt-1 text-[10px] text-[var(--color-text-muted)]">{{ workspace.conversationCount }} convs · {{ workspace.lastActiveLabel }}</p>
          </div>

          <p v-if="!workspaceCards.length && !isInlineCreating" class="py-4 text-center text-xs text-[var(--color-text-muted)]">No workspaces yet</p>
        </div>
      </WorkspaceListPanel>

      <div
        class="flex h-full min-w-0 flex-col space-y-3"
      >
        <header class="flex min-w-0 items-center justify-between gap-3 border-b border-[var(--color-border)] pb-2">
          <input
            v-if="isRenamingInline"
            ref="renameInputRef"
            v-model="renameValue"
            class="input-base input-outlined min-w-0 flex-1 py-1 text-sm"
            aria-label="Workspace name"
            @keydown.enter.prevent="saveRename"
            @keydown.escape.prevent="cancelRename"
          />
          <div v-else class="min-w-0">
            <p class="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Workspace settings</p>
            <h2 class="truncate text-sm font-bold text-[var(--color-text-main)]">{{ activeWorkspace?.name || 'Select a workspace' }}</h2>
          </div>
          <div v-if="activeWorkspace" class="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <template v-if="isRenamingInline">
              <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="cancelRename">Cancel</button>
              <button type="button" class="btn-primary px-3 py-1.5 text-xs" @click="saveRename">Save</button>
            </template>
            <template v-else>
              <span v-if="isWorkspaceActive" class="inline-flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
                <span class="h-1.5 w-1.5 rounded-full" :class="runtimeStatusTone === 'danger' ? 'bg-[var(--color-danger)]' : runtimeStatusTone === 'success' ? 'bg-[var(--color-success)]' : 'bg-[var(--color-warning)]'"></span>
                {{ runtimeStatusLabel }}
              </span>
              <button v-if="!isWorkspaceActive" type="button" class="btn-primary px-3 py-1.5 text-xs" @click="activateSelectedWorkspace">Activate</button>
              <div ref="workspaceActionsRef" class="relative">
                <button type="button" class="btn-icon h-8 w-8" aria-label="Workspace actions" title="Workspace actions" :aria-expanded="workspaceActionsOpen" @click.stop="workspaceActionsOpen = !workspaceActionsOpen">•••</button>
                <Transition name="motion-popover">
                  <div v-if="workspaceActionsOpen" class="motion-popover-surface absolute right-0 top-full z-20 mt-1 w-44 rounded-lg border border-[var(--color-border)] bg-[var(--color-base)] p-1 shadow-lg">
                    <button v-if="isWorkspaceActive" type="button" class="nav-tab w-full text-left" @click="runWorkspaceAction(startRename)">Rename workspace</button>
                    <button type="button" class="nav-tab w-full text-left text-[var(--color-danger)]" @click="runWorkspaceAction(requestDeleteWorkspace, activeWorkspace.id)">Delete workspace</button>
                  </div>
                </Transition>
              </div>
            </template>
          </div>
        </header>

        <nav v-if="activeWorkspace" class="flex shrink-0 gap-4 border-b border-[var(--color-border)]" aria-label="Workspace settings sections" role="tablist">
          <button
            v-for="section in workspaceSections"
            :key="section.id"
            type="button"
            class="relative -mb-px border-b-2 px-0.5 pb-1.5 text-xs font-medium transition-colors"
            :class="activeWorkspaceSection === section.id ? 'border-[var(--color-accent)] text-[var(--color-text-main)]' : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
            :aria-selected="activeWorkspaceSection === section.id"
            :tabindex="activeWorkspaceSection === section.id ? 0 : -1"
            role="tab"
            @click="activeWorkspaceSection = section.id"
            @keydown.left.prevent="moveWorkspaceSection(-1, $event)"
            @keydown.right.prevent="moveWorkspaceSection(1, $event)"
          >
            {{ section.label }}
          </button>
        </nav>

        <div v-if="activeWorkspace" class="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
          <div v-show="activeWorkspaceSection === 'general'" class="space-y-3" role="tabpanel" aria-label="General workspace settings">
          <WorkspaceContextSection>
            <div class="flex items-center justify-between gap-3">
              <h4 class="section-label">Workspace Context</h4>
              <button v-if="isWorkspaceActive && !isEditingContext" type="button" class="text-xs font-semibold text-[var(--color-accent)] hover:underline" @click="startContextEdit">Edit</button>
            </div>
            <div v-if="isEditingContext" class="space-y-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] p-3">
              <textarea v-model="setupWorkspaceContext" rows="4" class="input-base input-outlined resize-none py-1.5 text-xs" placeholder="Describe the business purpose, terms, and schema context for this workspace..." :disabled="isSavingWorkspaceIdentity"></textarea>
              <div class="flex items-center justify-between gap-3">
                <span class="text-[10px]" :class="isWorkspaceContextDirty ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'">{{ isWorkspaceContextDirty ? 'Unsaved changes' : 'Saved' }}</span>
                <div class="flex items-center gap-2">
                  <button type="button" class="btn-secondary px-3 py-1.5 text-xs" :disabled="isSavingWorkspaceIdentity" @click="cancelContextEdit">Cancel</button>
                  <button type="button" class="btn-primary px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60" :disabled="isSavingWorkspaceIdentity || !isWorkspaceContextDirty" @click="saveWorkspaceContext">{{ isSavingWorkspaceIdentity ? 'Saving...' : 'Save' }}</button>
                </div>
              </div>
            </div>
            <div v-else class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] p-3">
              <p v-if="selectedWorkspaceContext" class="whitespace-pre-wrap text-xs leading-relaxed text-[var(--color-text-main)]">{{ selectedWorkspaceContext }}</p>
              <p v-else class="text-xs text-[var(--color-text-muted)]">No workspace context added yet.</p>
            </div>
          </WorkspaceContextSection>
          </div>

          <div v-show="activeWorkspaceSection === 'connections'" class="space-y-3" role="tabpanel" aria-label="Workspace data sources">
            <section class="rounded-lg border p-4" :class="nativeRuntimeStatus.ready ? 'border-[var(--color-border)] bg-[var(--color-base-soft)]' : 'border-[var(--color-warning-border)] bg-[var(--color-warning-bg)]'">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h4 class="section-label">Data runtime</h4>
                  <p class="mt-1 text-xs leading-5" :class="nativeRuntimeStatus.ready ? 'text-[var(--color-text-muted)]' : 'text-[var(--color-warning-text)]'">
                    {{ nativeRuntimeStatus.ready ? runtimeConfigurationSummary : 'Set up the local Python runtime before adding a data source.' }}
                  </p>
                </div>
                <button v-if="nativeRuntimeStatus.ready && !runtimeConfigurationOpen" type="button" class="btn-secondary shrink-0 px-3 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="startRuntimeReconfiguration">Runtime settings</button>
              </div>
              <p v-if="runtimeProvisionError" class="mt-3 rounded-lg bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger-text)]" role="alert">{{ runtimeProvisionError }}</p>

              <div v-if="!nativeRuntimeStatus.ready && !runtimeConfigurationOpen" class="mt-3 flex flex-wrap items-center justify-between gap-3">
                <p class="max-w-sm text-[10px] leading-4 text-[var(--color-warning-text)]">
                  Managed setup installs the supported Python version and data packages for you.
                </p>
                <div class="flex flex-wrap items-center justify-end gap-2">
                  <button type="button" class="btn-secondary px-3 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="startRuntimeReconfiguration">
                    Company-managed setup
                  </button>
                  <button type="button" class="btn-primary px-4 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="setupManagedRuntime">
                    {{ runtimeProvisioning ? 'Setting up managed runtime…' : 'Set up managed runtime' }}
                  </button>
                </div>
              </div>

              <div v-if="runtimeConfigurationOpen" class="mt-4 border-t border-[var(--color-border)] pt-4">
                <div class="mb-3">
                  <h5 class="text-xs font-semibold text-[var(--color-text-main)]">{{ nativeRuntimeStatus.ready ? 'Runtime settings' : 'Company-managed setup' }}</h5>
                  <p class="mt-1 text-[10px] leading-4 text-[var(--color-text-muted)]">
                    Use a company Python installation, internal package mirror, proxy, or certificate bundle.
                  </p>
                </div>
                <div class="grid gap-3 sm:grid-cols-2">
                <label class="block sm:col-span-2">
                  <span class="input-label">Runtime source</span>
                  <select v-model="runtimeConfig.mode" class="input-base input-outlined" :disabled="runtimeProvisioning">
                    <option value="managed">Managed Python</option>
                    <option value="external-python">Company Python</option>
                    <option value="internal-mirror">Internal mirror</option>
                  </select>
                </label>
                <label v-if="runtimeConfig.mode !== 'external-python'" class="block">
                  <span class="input-label">Python version</span>
                  <input v-model="runtimeConfig.pythonVersion" class="input-base input-outlined" placeholder="3.12" :disabled="runtimeProvisioning" />
                </label>
                <label v-if="runtimeConfig.mode === 'external-python'" class="block sm:col-span-2">
                  <span class="input-label">Python executable path</span>
                  <div class="flex gap-2">
                    <input v-model="runtimeConfig.pythonExecutable" class="input-base input-outlined min-w-0 flex-1 font-mono text-xs" placeholder="/company/tools/python3.12" :disabled="runtimeProvisioning" />
                    <button type="button" class="btn-secondary px-3 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="choosePythonExecutable">Browse</button>
                  </div>
                </label>
                <label v-if="runtimeConfig.mode === 'internal-mirror'" class="block sm:col-span-2">
                  <span class="input-label">Python download mirror</span>
                  <input type="password" v-model="runtimeConfig.pythonInstallMirror" class="input-base input-outlined" placeholder="https://packages.company/python" autocomplete="off" spellcheck="false" :disabled="runtimeProvisioning" />
                </label>
                <label class="block sm:col-span-2">
                  <span class="input-label">Package index</span>
                  <input type="password" v-model="runtimeConfig.defaultIndex" class="input-base input-outlined" placeholder="https://packages.company/simple (optional for managed Python)" autocomplete="off" spellcheck="false" :disabled="runtimeProvisioning" />
                </label>
                <label class="block">
                  <span class="input-label">HTTP proxy</span>
                  <input type="password" v-model="runtimeConfig.httpProxy" class="input-base input-outlined" placeholder="http://proxy.company:8080" autocomplete="off" spellcheck="false" :disabled="runtimeProvisioning" />
                </label>
                <label class="block">
                  <span class="input-label">HTTPS proxy</span>
                  <input type="password" v-model="runtimeConfig.httpsProxy" class="input-base input-outlined" placeholder="https://proxy.company:8443" autocomplete="off" spellcheck="false" :disabled="runtimeProvisioning" />
                </label>
                <label class="block sm:col-span-2">
                  <span class="input-label">Proxy bypass list</span>
                  <input v-model="runtimeConfig.noProxy" class="input-base input-outlined" placeholder="localhost,.company.internal" :disabled="runtimeProvisioning" />
                </label>
                <label class="flex items-center gap-2 text-xs text-[var(--color-text-main)] sm:col-span-2">
                  <input v-model="runtimeConfig.useSystemCertificates" type="checkbox" :disabled="runtimeProvisioning" />
                  Use operating-system certificates
                </label>
                <label class="block sm:col-span-2">
                  <span class="input-label">Custom CA bundle</span>
                  <div class="flex gap-2">
                    <input v-model="runtimeConfig.certificateBundle" class="input-base input-outlined min-w-0 flex-1 font-mono text-xs" placeholder="/company/certificates/ca-bundle.pem (optional)" :disabled="runtimeProvisioning" />
                    <button type="button" class="btn-secondary px-3 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="chooseCertificateBundle">Browse</button>
                  </div>
                </label>
              </div>
              <div class="mt-4 flex items-center justify-between gap-3">
                <p class="text-[10px] text-[var(--color-text-muted)]">Proxy, mirror, and index values are cleared after every setup attempt and are never saved by Inquira. {{ runtimePlanSummary }}</p>
                <div class="flex shrink-0 items-center gap-2">
                  <button type="button" class="btn-secondary px-3 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="cancelRuntimeReconfiguration">Cancel</button>
                  <button type="button" class="btn-primary px-4 py-1.5 text-xs" :disabled="runtimeProvisioning" @click="provisionDataRuntime()">{{ runtimeProvisioning ? 'Validating and setting up…' : 'Apply runtime setup' }}</button>
                </div>
              </div>
              </div>
            </section>

            <section class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] p-4">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <h4 class="section-label">Data sources</h4>
                  <p class="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">Create refreshable local snapshots from CSV, Parquet, and Excel files.</p>
                </div>
                <button type="button" class="btn-primary px-3 py-1.5 text-xs" :disabled="connectionActionLoading || !isWorkspaceActive || !nativeRuntimeStatus.ready" @click="chooseConnectionFile">
                  Add data source
                </button>
              </div>

              <p v-if="connectionError" class="mt-3 rounded-lg bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger-text)]" role="alert">{{ connectionError }}</p>

              <div v-if="pendingConnection" class="mt-4 space-y-3 rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-base)] p-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-xs font-semibold text-[var(--color-text-main)]">{{ pendingConnection.source_path }}</p>
                    <p class="mt-1 text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">{{ adapterKindLabel(pendingConnection.adapter_kind) }} · {{ pendingConnection.objects.length }} {{ pendingConnection.adapter_kind === 'excel' ? 'sheets' : 'table' }}</p>
                  </div>
                  <button type="button" class="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]" :disabled="connectionActionLoading" @click="cancelPendingConnection">Cancel</button>
                </div>
                <label class="block">
                  <span class="input-label">Connection name</span>
                  <input v-model="pendingConnection.name" class="input-base input-outlined" maxlength="120" :disabled="connectionActionLoading" />
                </label>
                <div v-if="pendingConnection.adapter_kind === 'excel'" class="space-y-2">
                  <div class="flex items-center justify-between gap-3">
                    <span class="input-label">
                      Select sheets · {{ pendingConnection.selected_object_ids.length }} selected
                    </span>
                    <label class="flex items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
                      Formula values
                      <select v-model="pendingConnection.formula_mode" class="rounded border border-[var(--color-border)] bg-[var(--color-base)] px-2 py-1" :disabled="connectionActionLoading" @change="previewPendingSheet(pendingConnection.active_object_id)">
                        <option value="cached">Last saved values</option>
                        <option value="formula">Formula text</option>
                      </select>
                    </label>
                  </div>
                  <div v-if="pendingConnection.objects.length > 6" class="flex items-center gap-2">
                    <input
                      v-model="sheetSearch"
                      type="search"
                      class="input-base input-outlined h-8 min-w-0 flex-1 text-xs"
                      placeholder="Search sheets"
                      aria-label="Search Excel sheets"
                    />
                    <button type="button" class="btn-ghost shrink-0 px-2 py-1 text-xs" :disabled="connectionActionLoading" @click="selectAllPendingSheets">
                      Select all
                    </button>
                    <button
                      v-if="pendingConnection.selected_object_ids.length"
                      type="button"
                      class="btn-ghost shrink-0 px-2 py-1 text-xs"
                      :disabled="connectionActionLoading"
                      @click="clearPendingSheetSelection"
                    >
                      Clear
                    </button>
                  </div>
                  <div class="grid max-h-56 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
                    <label v-for="object in filteredPendingSheets" :key="object.id" class="flex items-start gap-2 rounded-lg border p-2" :class="object.id === pendingConnection.active_object_id ? 'border-[var(--color-accent)]' : 'border-[var(--color-border)]'">
                      <input v-model="pendingConnection.selected_object_ids" type="checkbox" :value="object.id" :disabled="connectionActionLoading || object.metadata?.selectable === false" />
                      <span class="min-w-0 flex-1">
                        <span class="block truncate text-xs font-medium text-[var(--color-text-main)]">{{ object.name }}</span>
                        <span class="block text-[10px] text-[var(--color-text-muted)]">{{ object.metadata?.visibility || 'visible' }} · {{ Number(object.metadata?.row_count || 0).toLocaleString() }} rows · {{ Number(object.metadata?.column_count || 0) }} columns</span>
                      </span>
                      <button v-if="object.metadata?.selectable !== false" type="button" class="text-[10px] font-medium text-[var(--color-accent)] hover:underline" :disabled="connectionActionLoading" @click.prevent="previewPendingSheet(object.id)">Preview</button>
                    </label>
                  </div>
                  <p v-if="filteredPendingSheets.length === 0" class="py-4 text-center text-xs text-[var(--color-text-muted)]">
                    No sheets match “{{ sheetSearch }}”.
                  </p>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="column in visiblePendingColumns" :key="column.name" class="rounded-full bg-[var(--color-base-soft)] px-2 py-1 text-[10px] text-[var(--color-text-muted)]">
                    {{ column.name }} · {{ column.data_type }}
                  </span>
                  <span v-if="pendingConnection.columns.length > visiblePendingColumns.length" class="rounded-full bg-[var(--color-base-soft)] px-2 py-1 text-[10px] font-medium text-[var(--color-text-main)]">
                    +{{ pendingConnection.columns.length - visiblePendingColumns.length }} more
                  </span>
                </div>
                <div v-if="pendingConnection.preview_rows.length" class="overflow-hidden rounded-lg border border-[var(--color-border)]">
                  <div class="overflow-x-auto">
                    <table class="min-w-full text-left text-[10px]">
                      <thead class="bg-[var(--color-base-soft)] text-[var(--color-text-muted)]"><tr><th v-for="column in pendingConnection.columns" :key="column.name" class="px-2 py-1.5 font-medium">{{ column.name }}</th></tr></thead>
                      <tbody><tr v-for="(row, index) in pendingConnection.preview_rows.slice(0, 5)" :key="index" class="border-t border-[var(--color-border)]"><td v-for="column in pendingConnection.columns" :key="column.name" class="max-w-48 truncate px-2 py-1.5 text-[var(--color-text-main)]">{{ row[column.name] ?? '—' }}</td></tr></tbody>
                    </table>
                  </div>
                </div>
                <div class="flex justify-end">
                  <button type="button" class="btn-primary px-4 py-1.5 text-xs" :disabled="connectionActionLoading || !pendingConnection.name.trim() || !pendingConnection.selected_object_ids.length" @click="createPendingConnection">
                    {{ connectionActionLoading ? 'Creating snapshot…' : 'Create connection' }}
                  </button>
                </div>
              </div>
            </section>

            <section v-if="nativeConnections.length" class="space-y-2">
              <article v-for="item in nativeConnections" :key="item.id" class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <p class="truncate text-xs font-semibold text-[var(--color-text-main)]">{{ item.name }}</p>
                      <span class="rounded-full px-2 py-0.5 text-[9px]" :class="['error', 'needs_attention'].includes(item.status) ? 'bg-[var(--color-danger-bg)] text-[var(--color-danger-text)]' : 'bg-[var(--color-success-bg)] text-[var(--color-success)]'">{{ item.status === 'needs_attention' ? 'needs attention' : item.status }}</span>
                    </div>
                    <p class="mt-1 truncate text-[10px] text-[var(--color-text-muted)]">{{ item.source_path }}</p>
                    <p class="mt-1 text-[10px] text-[var(--color-text-muted)]">{{ connectionOutputSummary(item) }}</p>
                    <p v-if="item.error_message" class="mt-1 text-[10px] text-[var(--color-danger-text)]">{{ item.error_message }}</p>
                  </div>
                  <div class="flex shrink-0 items-center gap-2">
                    <button type="button" class="text-xs font-medium text-[var(--color-accent)] hover:underline" :disabled="refreshingConnectionIds.has(item.id)" @click="refreshNativeConnection(item.id)">{{ refreshingConnectionIds.has(item.id) ? 'Refreshing…' : 'Refresh' }}</button>
                    <button type="button" class="text-xs font-medium text-[var(--color-danger)] hover:underline" :disabled="connectionActionLoading" @click="deleteNativeConnection(item.id)">Delete</button>
                  </div>
                </div>
              </article>
            </section>
            <div v-else-if="!pendingConnection && !connectionActionLoading" class="rounded-lg border border-dashed border-[var(--color-border)] py-8 text-center">
              <p class="text-xs font-medium text-[var(--color-text-main)]">No data sources yet</p>
              <p class="mt-1 text-[10px] text-[var(--color-text-muted)]">Start with a local CSV, Parquet, or Excel file.</p>
            </div>
          </div>

          <div v-show="activeWorkspaceSection === 'ai'" role="tabpanel" aria-label="Workspace AI settings">
            <WorkspaceAIConfigSection v-if="activeWorkspace?.id" :workspace-id="activeWorkspace.id" />
          </div>

        </div>

        <div v-else class="flex flex-1 flex-col items-center justify-center rounded-lg bg-[var(--color-base-soft)] px-5 py-8 text-center">
          <p class="mb-4 text-sm text-[var(--color-text-sub)]">Create a workspace to add context and data sources.</p>
          <button type="button" class="btn-primary px-4 py-2 text-sm" @click="beginInlineCreate">Create your first workspace</button>
        </div>
      </div>
    </div>

    <ConfirmationModal
      :is-open="isWorkspaceDeleteDialogOpen"
      title="Delete Workspace"
      :message="workspaceDeleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeWorkspaceDeleteDialog"
      @confirm="deleteWorkspace"
    />

  </section>
</template>

<script>
const handledConnectionFlowRequestIds = new WeakMap()
</script>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { workspaceApi } from '../../../api/workspaces'
import { connectionService } from '../../../services/connectionService'
import { runtimeProvisionService } from '../../../services/runtimeProvisionService'
import { useUiStore } from '../../../stores/uiStore'
import { usePreferencesStore } from '../../../stores/preferencesStore'
import { useArtifactStore } from '../../../stores/artifactStore'
import { useExecutionStore } from '../../../stores/executionStore'
import { useWorkspaceStore } from '../../../stores/workspaceStore'
import { useConversationStore } from '../../../stores/conversationStore'
import { useWorkspaceActivation } from '../../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../../composables/useArtifactPresentation'
import { toast } from '../../../composables/useToast'
import WorkspaceAIConfigSection from './WorkspaceAIConfigSection.vue'
import { extractApiErrorMessage } from '../../../utils/apiError'
import { filenameFromPath } from '../../../utils/pathUtils'
import ConfirmationModal from '../ConfirmationModal.vue'
import WorkspaceContextSection from './workspace/WorkspaceContextSection.vue'
import WorkspaceListPanel from './workspace/WorkspaceListPanel.vue'

const props = defineProps({
  activeWorkspaceId: {
    type: String,
    default: '',
  },
  workspaces: {
    type: Array,
    default: () => [],
  },
  initialSection: {
    type: String,
    default: 'general',
  },
})

const emit = defineEmits(['select-workspace', 'activate-workspace', 'workspace-created'])

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const isNativeWorkspaceMetadata = workspaceApi.isAvailable()
const workspaceSections = [
  { id: 'general', label: 'General' },
  { id: 'connections', label: 'Data sources' },
  { id: 'ai', label: 'AI' },
]
const activeWorkspaceSection = ref('general')
const nativeConnections = ref([])
const pendingConnection = ref(null)
const connectionActionLoading = ref(false)
const connectionError = ref('')
const sheetSearch = ref('')
const refreshingConnectionIds = ref(new Set())
const nativeRuntimeStatus = ref({ ready: false })
const runtimeProvisioning = ref(false)
const runtimeProvisionError = ref('')
const runtimeConfigurationOpen = ref(false)
const runtimePlanSummary = ref('')
const isWorkspaceTabMounted = ref(false)
const runtimeConfig = ref({
  mode: 'managed',
  pythonVersion: '3.12',
  pythonExecutable: '',
  pythonInstallMirror: '',
  defaultIndex: '',
  useSystemCertificates: false,
  certificateBundle: '',
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
})
const pendingSelectableSheets = computed(() => (
  Array.isArray(pendingConnection.value?.objects)
    ? pendingConnection.value.objects.filter((object) => object?.metadata?.selectable !== false)
    : []
))
const filteredPendingSheets = computed(() => {
  const query = String(sheetSearch.value || '').trim().toLowerCase()
  if (!query) return Array.isArray(pendingConnection.value?.objects) ? pendingConnection.value.objects : []
  return (Array.isArray(pendingConnection.value?.objects) ? pendingConnection.value.objects : [])
    .filter((object) => String(object?.name || object?.id || '').toLowerCase().includes(query))
})
const visiblePendingColumns = computed(() => (
  Array.isArray(pendingConnection.value?.columns) ? pendingConnection.value.columns.slice(0, 12) : []
))

function selectAllPendingSheets() {
  if (!pendingConnection.value) return
  pendingConnection.value.selected_object_ids = pendingSelectableSheets.value.map((object) => String(object.id))
}

function clearPendingSheetSelection() {
  if (!pendingConnection.value) return
  pendingConnection.value.selected_object_ids = []
}
const workspaceActionsOpen = ref(false)
const workspaceActionsRef = ref(null)

function runWorkspaceAction(action, ...args) {
  workspaceActionsOpen.value = false
  return action?.(...args)
}

function handleWorkspaceActionsPointerDown(event) {
  if (!workspaceActionsOpen.value) return
  if (workspaceActionsRef.value?.contains(event.target)) return
  workspaceActionsOpen.value = false
}

function moveWorkspaceSection(direction, event) {
  const currentIndex = workspaceSections.findIndex((section) => section.id === activeWorkspaceSection.value)
  const nextIndex = (currentIndex + direction + workspaceSections.length) % workspaceSections.length
  activeWorkspaceSection.value = workspaceSections[nextIndex].id
  nextTick(() => {
    const tabs = event?.currentTarget?.parentElement?.querySelectorAll?.('[role="tab"]') || []
    tabs[nextIndex]?.focus?.()
  })
}

const workspaceSummaries = ref({})
const workspaceDetail = ref(null)
const isRenamingInline = ref(false)
const renameValue = ref('')
const renameInputRef = ref(null)
const isWorkspaceDeleteDialogOpen = ref(false)
const pendingWorkspaceDeletionId = ref('')

const isCreatingWorkspace = ref(false)
const setupWorkspaceName = ref('')
const setupWorkspaceContext = ref('')
const savedWorkspaceContext = ref('')
const isSavingWorkspaceIdentity = ref(false)
const isInlineCreating = ref(false)
const isEditingContext = ref(false)
const newWorkspaceInputRef = ref(null)

function normalizeWorkspaceName(value) {
  return String(value || '').toUpperCase()
}

const workspaceCards = computed(() => {
  const items = Array.isArray(props.workspaces) ? props.workspaces : []
  return items.map((workspace) => {
    const id = String(workspace?.id || '').trim()
    const name = String(workspace?.name || '').trim()
    const summary = workspaceSummaries.value?.[id] || {}
    const conversationCount = Number(summary?.conversation_count || 0)
    const lastActive = String(workspace?.updated_at || '').trim()
    return {
      ...workspace,
      id,
      name,
      conversationCount,
      lastActiveLabel: formatRelativeTime(lastActive),
    }
  })
})

const activeWorkspace = computed(() => workspaceCards.value.find((workspace) => workspace.id === String(props.activeWorkspaceId || '').trim()) || null)
const isWorkspaceActive = computed(() => !!activeWorkspace.value && activeWorkspace.value.id === String(workspaceStore.activeWorkspaceId || '').trim())
const selectedWorkspaceContext = computed(() => String(workspaceDetail.value?.schema_context ?? activeWorkspace.value?.schema_context ?? '').trim())
const normalizedSetupWorkspaceContext = computed(() => String(setupWorkspaceContext.value || '').trim())
const isWorkspaceContextDirty = computed(() => normalizedSetupWorkspaceContext.value !== String(savedWorkspaceContext.value || '').trim())
const workspaceRuntimeStatus = computed(() => executionStore.getWorkspaceRuntimeStatus(props.activeWorkspaceId))
const workspaceRuntimeReady = computed(() => ['ready', 'busy'].includes(workspaceRuntimeStatus.value))
const runtimeStatusTone = computed(() => {
  if (workspaceRuntimeStatus.value === 'error') return 'danger'
  if (workspaceRuntimeReady.value) return 'success'
  if (['starting', 'connecting'].includes(String(workspaceRuntimeStatus.value || ''))) {
    return 'accent'
  }
  return 'muted'
})
const runtimeStatusLabel = computed(() => {
  if (workspaceRuntimeStatus.value === 'busy') return 'Runtime working'
  if (workspaceRuntimeStatus.value === 'ready') return 'Runtime ready'
  if (workspaceRuntimeStatus.value === 'starting' || workspaceRuntimeStatus.value === 'connecting') return 'Starting runtime'
  if (workspaceRuntimeStatus.value === 'error') return 'Runtime needs attention'
  return 'Runtime not started'
})
const workspaceDeleteDialogMessage = computed(() => {
  const targetId = String(pendingWorkspaceDeletionId.value || props.activeWorkspaceId || '').trim()
  const target = workspaceCards.value.find((workspace) => workspace.id === targetId)
  const name = String(target?.name || 'this workspace').trim()
  return `Are you sure you want to delete "${name}"? This cannot be undone.`
})
watch(
  () => props.initialSection,
  (section) => {
    const normalized = String(section || '').trim().toLowerCase()
    const requested = normalized === 'data' ? 'connections' : normalized
    activeWorkspaceSection.value = workspaceSections.some((item) => item.id === requested) ? requested : 'general'
  },
  { immediate: true },
)
watch(
  () => props.workspaces,
  async () => { await hydrateWorkspaceCards() },
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
    await loadWorkspaceDetail()
    syncSetupIdentity()
    await loadNativeConnections()
  },
  { immediate: true },
)

watch(
  [
    () => Number(uiStore.connectionFlowRequestId || 0),
    () => isWorkspaceActive.value,
    () => Boolean(nativeRuntimeStatus.value?.ready),
    () => runtimeProvisioning.value,
    () => connectionActionLoading.value,
    () => isWorkspaceTabMounted.value,
  ],
  () => {
    void handlePendingConnectionFlowRequest()
  },
  { flush: 'post' },
)

onMounted(async () => {
  isWorkspaceTabMounted.value = true
  document.addEventListener('pointerdown', handleWorkspaceActionsPointerDown)
  await hydrateWorkspaceCards()
  await loadNativeConnections()
  await loadNativeRuntimeStatus()
  syncSetupIdentity()
  await handlePendingConnectionFlowRequest()
})

async function loadNativeRuntimeStatus() {
  if (!isNativeWorkspaceMetadata) return
  try {
    nativeRuntimeStatus.value = await runtimeProvisionService.status()
    applySavedRuntimeConfiguration(nativeRuntimeStatus.value?.configuration)
  } catch (error) {
    runtimeProvisionError.value = extractApiErrorMessage(error, 'Could not read data runtime status.')
  }
}

const runtimeConfigurationSummary = computed(() => {
  const configuration = nativeRuntimeStatus.value?.configuration
  if (!configuration) return `Runtime ready at ${nativeRuntimeStatus.value?.pythonExecutable || 'the managed environment'}.`
  if (configuration.mode === 'external-python') return `Runtime ready using company Python at ${configuration.pythonExecutable}.`
  if (configuration.mode === 'internal-mirror') return `Runtime ready using Python ${configuration.pythonVersion} from an internal mirror.`
  return `Runtime ready using managed Python ${configuration.pythonVersion || '3.12'}.`
})

function applySavedRuntimeConfiguration(configuration) {
  if (!configuration || typeof configuration !== 'object') return
  runtimeConfig.value.mode = configuration.mode || 'managed'
  runtimeConfig.value.pythonVersion = configuration.pythonVersion || '3.12'
  runtimeConfig.value.pythonExecutable = configuration.pythonExecutable || ''
  runtimeConfig.value.useSystemCertificates = Boolean(configuration.useSystemCertificates)
  runtimeConfig.value.certificateBundle = configuration.certificateBundle || ''
}

function clearTransientRuntimeConfig() {
  runtimeConfig.value.pythonInstallMirror = ''
  runtimeConfig.value.defaultIndex = ''
  runtimeConfig.value.httpProxy = ''
  runtimeConfig.value.httpsProxy = ''
  runtimeConfig.value.noProxy = ''
}

function startRuntimeReconfiguration() {
  runtimePlanSummary.value = ''
  runtimeProvisionError.value = ''
  runtimeConfigurationOpen.value = true
}

async function setupManagedRuntime() {
  runtimeConfig.value = {
    mode: 'managed',
    pythonVersion: '3.12',
    pythonExecutable: '',
    pythonInstallMirror: '',
    defaultIndex: '',
    useSystemCertificates: false,
    certificateBundle: '',
    httpProxy: '',
    httpsProxy: '',
    noProxy: '',
  }
  runtimeConfigurationOpen.value = false
  await provisionDataRuntime()
}

function cancelRuntimeReconfiguration() {
  clearTransientRuntimeConfig()
  applySavedRuntimeConfiguration(nativeRuntimeStatus.value?.configuration)
  runtimePlanSummary.value = ''
  runtimeProvisionError.value = ''
  runtimeConfigurationOpen.value = false
}

async function choosePythonExecutable() {
  try {
    const selected = await runtimeProvisionService.choosePythonExecutable()
    if (selected) runtimeConfig.value.pythonExecutable = String(selected)
  } catch (error) {
    runtimeProvisionError.value = extractApiErrorMessage(error, 'Could not choose a Python executable.')
  }
}

async function chooseCertificateBundle() {
  try {
    const selected = await runtimeProvisionService.chooseCertificateBundle()
    if (selected) runtimeConfig.value.certificateBundle = String(selected)
  } catch (error) {
    runtimeProvisionError.value = extractApiErrorMessage(error, 'Could not choose a certificate bundle.')
  }
}

async function provisionDataRuntime() {
  runtimeProvisioning.value = true
  runtimeProvisionError.value = ''
  try {
    const plan = await runtimeProvisionService.plan({ ...runtimeConfig.value })
    runtimePlanSummary.value = `${Number(plan?.steps?.length || 0)} setup steps validated.`
    await runtimeProvisionService.provision({ ...runtimeConfig.value })
    await loadNativeRuntimeStatus()
    if (!nativeRuntimeStatus.value?.ready) throw new Error('The data runtime did not become ready.')
    runtimeConfigurationOpen.value = false
    toast.success('Data runtime ready', 'CSV, Parquet, and Excel connections can now be created.')
  } catch (error) {
    runtimeProvisionError.value = extractApiErrorMessage(error, 'Could not set up the data runtime.')
  } finally {
    clearTransientRuntimeConfig()
    runtimeProvisioning.value = false
  }
}

async function loadNativeConnections() {
  if (!isNativeWorkspaceMetadata) return
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    nativeConnections.value = []
    return
  }
  try {
    const response = await connectionService.list(workspaceId)
    nativeConnections.value = Array.isArray(response?.connections) ? response.connections : []
  } catch (error) {
    connectionError.value = extractApiErrorMessage(error, 'Could not load connections.')
  }
}

async function refreshNativeConnectionState(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const refreshes = [loadNativeConnections()]
  if (normalizedWorkspaceId && normalizedWorkspaceId === String(workspaceStore.activeWorkspaceId || '').trim()) {
    refreshes.push(
      workspaceStore.fetchActiveWorkspaceSummary(normalizedWorkspaceId),
      workspaceStore.fetchColumnCatalog({ force: true }),
    )
  }
  await Promise.all(refreshes)
}

async function handlePendingConnectionFlowRequest() {
  const requestId = Math.max(0, Math.floor(Number(uiStore.connectionFlowRequestId || 0)))
  const lastHandledRequestId = Number(handledConnectionFlowRequestIds.get(workspaceStore) || 0)
  if (!requestId || requestId <= lastHandledRequestId) return
  if (!isWorkspaceTabMounted.value || !isNativeWorkspaceMetadata || !isWorkspaceActive.value) return

  activeWorkspaceSection.value = 'connections'
  if (!nativeRuntimeStatus.value?.ready || runtimeProvisioning.value || connectionActionLoading.value) return

  handledConnectionFlowRequestIds.set(workspaceStore, requestId)
  await chooseConnectionFile()
}

async function chooseConnectionFile() {
  connectionError.value = ''
  connectionActionLoading.value = true
  try {
    const selection = await connectionService.chooseFile()
    const sourcePath = String(selection?.source_path || '').trim()
    const adapterKind = String(selection?.adapter_kind || '').trim().toLowerCase()
    if (!sourcePath || !adapterKind) return
    const discovery = await connectionService.discover(adapterKind, sourcePath)
    const objects = Array.isArray(discovery?.objects) ? discovery.objects : []
    const selectableObjects = objects.filter((object) => object?.metadata?.selectable !== false)
    const sourceObject = selectableObjects[0] || objects[0] || {}
    const sourceObjectId = adapterKind === 'excel' ? String(sourceObject?.id || '') : ''
    const options = adapterKind === 'excel' ? { formula_mode: 'cached' } : {}
    const preview = sourceObjectId || adapterKind !== 'excel'
      ? await connectionService.preview(adapterKind, sourcePath, sourceObjectId, 25, options)
      : { columns: [], rows: [] }
    sheetSearch.value = ''
    pendingConnection.value = {
      source_path: sourcePath,
      adapter_kind: adapterKind,
      name: String(sourceObject?.name || formatFilename(sourcePath) || 'Local connection').trim(),
      objects,
      selected_object_ids: sourceObject?.metadata?.selectable === false ? [] : [String(sourceObject?.id || 'file')],
      active_object_id: String(sourceObject?.id || ''),
      formula_mode: 'cached',
      columns: Array.isArray(preview?.columns) ? preview.columns : (sourceObject?.columns || []),
      preview_rows: Array.isArray(preview?.rows) ? preview.rows : [],
    }
  } catch (error) {
    connectionError.value = extractApiErrorMessage(error, 'Could not inspect the selected file.')
  } finally {
    connectionActionLoading.value = false
  }
}

async function previewPendingSheet(source_object_id) {
  const pending = pendingConnection.value
  if (!pending || !source_object_id || connectionActionLoading.value) return
  connectionError.value = ''
  connectionActionLoading.value = true
  try {
    const options = pending.adapter_kind === 'excel' ? { formula_mode: pending.formula_mode } : {}
    const preview = await connectionService.preview(
      pending.adapter_kind,
      pending.source_path,
      source_object_id,
      25,
      options,
    )
    pending.active_object_id = source_object_id
    pending.columns = Array.isArray(preview?.columns) ? preview.columns : []
    pending.preview_rows = Array.isArray(preview?.rows) ? preview.rows : []
  } catch (error) {
    connectionError.value = extractApiErrorMessage(error, 'Could not preview the selected sheet.')
  } finally {
    connectionActionLoading.value = false
  }
}

function cancelPendingConnection() {
  if (connectionActionLoading.value) return
  pendingConnection.value = null
  sheetSearch.value = ''
  connectionError.value = ''
}

async function createPendingConnection() {
  const pending = pendingConnection.value
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!pending || !workspaceId) return
  connectionError.value = ''
  connectionActionLoading.value = true
  try {
    await connectionService.create({
      workspace_id: workspaceId,
      name: String(pending.name || '').trim(),
      adapter_kind: pending.adapter_kind,
      source_path: pending.source_path,
      selected_object_ids: pending.selected_object_ids,
      options: pending.adapter_kind === 'excel' ? { formula_mode: pending.formula_mode } : {},
    })
    pendingConnection.value = null
    sheetSearch.value = ''
    await refreshNativeConnectionState(workspaceId)
    toast.success('Connection created', 'The local snapshot is ready for analysis.')
  } catch (error) {
    connectionError.value = extractApiErrorMessage(error, 'Could not create the connection.')
  } finally {
    connectionActionLoading.value = false
  }
}

async function refreshNativeConnection(connectionId) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  const next = new Set(refreshingConnectionIds.value)
  next.add(connectionId)
  refreshingConnectionIds.value = next
  connectionError.value = ''
  try {
    await connectionService.refresh(connectionId)
    await refreshNativeConnectionState(workspaceId)
    toast.success('Connection refreshed', 'The local snapshot is up to date.')
  } catch (error) {
    connectionError.value = extractApiErrorMessage(error, 'Could not refresh the connection.')
    await refreshNativeConnectionState(workspaceId)
  } finally {
    const remaining = new Set(refreshingConnectionIds.value)
    remaining.delete(connectionId)
    refreshingConnectionIds.value = remaining
  }
}

async function deleteNativeConnection(connectionId) {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  connectionError.value = ''
  connectionActionLoading.value = true
  try {
    await connectionService.remove(connectionId)
    await refreshNativeConnectionState(workspaceId)
    toast.success('Connection deleted', 'The connection and its local snapshots were removed.')
  } catch (error) {
    connectionError.value = extractApiErrorMessage(error, 'Could not delete the connection.')
  } finally {
    connectionActionLoading.value = false
  }
}

function connectionOutputSummary(connection) {
  const outputs = Array.isArray(connection?.outputs) ? connection.outputs : []
  const rows = outputs.reduce((total, output) => total + Number(output?.row_count || 0), 0)
  return `${adapterKindLabel(connection?.adapter_kind)} · ${outputs.length} table${outputs.length === 1 ? '' : 's'} · ${rows.toLocaleString()} rows`
}

function adapterKindLabel(kind) {
  if (kind === 'csv') return 'CSV'
  if (kind === 'excel') return 'Excel'
  return 'Parquet'
}

onUnmounted(() => {
  isWorkspaceTabMounted.value = false
  document.removeEventListener('pointerdown', handleWorkspaceActionsPointerDown)
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
        const summary = await workspaceApi.summary(workspaceId)
        summaries[workspaceId] = summary
      } catch {
        summaries[workspaceId] = {}
      }
    }),
  )
  workspaceSummaries.value = summaries
}

async function selectWorkspaceSummary(workspaceId) {
  isEditingContext.value = false
  isInlineCreating.value = false
  await emitSelectedWorkspace(workspaceId)
}

async function beginInlineCreate() {
  isEditingContext.value = false
  isInlineCreating.value = true
  setupWorkspaceName.value = ''
  await nextTick()
  newWorkspaceInputRef.value?.focus?.()
}

function cancelInlineCreate() {
  if (isCreatingWorkspace.value) return
  isInlineCreating.value = false
  setupWorkspaceName.value = ''
}

function startContextEdit() {
  if (!isWorkspaceActive.value) return
  syncSetupIdentity()
  isEditingContext.value = true
}

function cancelContextEdit() {
  syncSetupIdentity()
  isEditingContext.value = false
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
  workspaceDetail.value = null
  if (!workspaceId) {
    syncSetupIdentity()
    return
  }
  try {
    workspaceDetail.value = await workspaceApi.summary(workspaceId)
  } catch {
    workspaceDetail.value = null
  } finally {
    syncSetupIdentity()
  }
}

function resolveWorkspaceContext() {
  return String(workspaceDetail.value?.schema_context ?? activeWorkspace.value?.schema_context ?? '').trim()
}

function syncSetupIdentity() {
  setupWorkspaceName.value = normalizeWorkspaceName(String(activeWorkspace.value?.name || '').trim())
  const context = resolveWorkspaceContext()
  setupWorkspaceContext.value = context
  savedWorkspaceContext.value = context
}

async function saveWorkspaceContext() {
  const workspaceId = String(props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  const persisted = await ensureWorkspaceContextPersisted()
  if (persisted) {
    savedWorkspaceContext.value = normalizedSetupWorkspaceContext.value
    isEditingContext.value = false
  }
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
    await workspaceStore.renameWorkspace(workspaceId, normalizedName, context)
    await workspaceStore.fetchWorkspaces()
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
    await workspaceStore.renameWorkspace(workspaceId, name, resolveWorkspaceContext())
    await workspaceStore.fetchWorkspaces()
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
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  pendingWorkspaceDeletionId.value = normalizedWorkspaceId
  isWorkspaceDeleteDialogOpen.value = true
}

function closeWorkspaceDeleteDialog() {
  isWorkspaceDeleteDialogOpen.value = false
  pendingWorkspaceDeletionId.value = ''
}

async function deleteWorkspace() {
  const workspaceId = String(pendingWorkspaceDeletionId.value || props.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  try {
    await workspaceActivation.deleteWorkspace(workspaceId)
    closeWorkspaceDeleteDialog()
    await workspaceStore.fetchWorkspaces()
    const fallbackId = String(workspaceStore.activeWorkspaceId || workspaceCards.value[0]?.id || '').trim()
    if (fallbackId) {
      emit('select-workspace', fallbackId)
    }
    toast.success('Workspace deleted', 'Workspace metadata and local data were deleted.')
  } catch (error) {
    toast.error('Delete failed', extractApiErrorMessage(error, 'Failed to delete workspace.'))
  }
}

async function createWorkspace() {
  const name = String(setupWorkspaceName.value || '').trim()
  if (!name) {
    toast.error('Workspace name required', 'Enter a workspace name to continue.')
    return
  }
  isCreatingWorkspace.value = true
  try {
    const context = ''
    const workspace = await workspaceActivation.createWorkspace(name, context)
    const workspaceId = String(workspace?.id || workspaceStore.activeWorkspaceId || '').trim()
    if (!workspaceId) {
      throw new Error('Backend did not return a workspace id.')
    }
    await workspaceStore.fetchWorkspaces()
    emit('workspace-created', {
      workspaceId,
      name,
      context,
    })
    isInlineCreating.value = false
    isEditingContext.value = true
  } catch (error) {
    toast.error('Create failed', extractApiErrorMessage(error, 'Failed to create workspace.'))
  } finally {
    isCreatingWorkspace.value = false
  }
}

function formatFilename(raw) {
  const value = String(raw || '').trim()
  if (!value) return 'dataset'
  return filenameFromPath(value, value)
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
