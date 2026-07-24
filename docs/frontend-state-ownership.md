# Frontend State Ownership

The frontend state is divided by product domain. Components should import the
smallest store that owns the state they need.

| Store | Ownership |
| --- | --- |
| `workspaceStore.ts` | Workspaces, datasets, schema/context, workspace readiness, and ingestion/deletion state |
| `conversationStore.ts` | Conversations, messages, turns, branches, stream traces, interventions, and usage |
| `executionStore.ts` | Generated/edited code, runtime state, operations, and terminal state |
| `artifactStore.ts` | Tables, figures, scalars, selections, paging, and viewport state |
| `preferencesStore.ts` | Providers, models, credentials metadata, themes, fonts, and preference state |
| `uiStore.ts` | Panes, dialogs, navigation, resizers, editor focus, and transient UI state |

`appCoordinatorStore.js` is not a state owner. It composes the six stores for
cross-domain workflows such as startup hydration, workspace activation,
conversation switching, and local snapshot persistence. Its public surface is
the application orchestration contract; new state and isolated domain
mutations must be added to a domain store, never to the coordinator.

The former `appStore.js` compatibility boundary has been removed.
