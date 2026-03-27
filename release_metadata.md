# Release v0.5.7a23

This release introduces a comprehensive **Frontend UI/UX Redesign**, moving toward a "minimal elegant" aesthetic. We’ve overhauled the sidebar, modals, and notification systems to improve visual consistency and layout fluidity while resolving several regressions from the `v0.5.7a22` cycle.

## 🗒️ Changelog

### ✨ Features & UI Redesign

* **UnifiedSidebar:** Complete overhaul featuring a new search/filter bar, collapsible sections (Workspace, Datasets, Conversations), item count badges, and a new delete confirmation flow. (`58a8034`)
* **Settings & Modals:** Applied a modern aesthetic to the Settings Modal including backdrop blur, softer corners, and a new active-tab accent bar. (`56963e6`)
* **Toast Notifications:**
  * Relocated to bottom-center for better visibility. (`07ce371`)
  * Redesigned with CSS variables for semantic coloring and smoother stacking animations. (`3ca1678`)
* **Layout Enhancements:**
  * **StatusBar:** Refined minimal design using CSS variables. (`a55ec93`)
  * **Startup & Overlays:** Redesigned Workspace and Startup screens with centered layouts, staggered animations, and subtle fade-ins. (`a108aac`, `71968db`)
* **Interactive Search:** The search icon has been moved to the footer and now triggers a reveal animation for the search bar. (`ffb9ca4`)

### 🐛 Bug Fixes

* **Sidebar:** Restored the "Add Dataset" button and fixed the missing right border. (`dda284c`, `1e975d7`)
* **Data Handling:** Resolved `appStore.datasets` errors by transitioning to local state management via `apiService.v1ListDatasets()`. (`0640a91`)
* **Assets & Icons:**
  * Restored logo visibility by removing a breaking gradient overlay. (`856043d`)
  * Fixed broken icon references (replaced `DatabaseIcon` with `CircleStackIcon`). (`69a4d92`)
* **UX Polish:**
  * Adjusted sidebar chevron positioning within the StatusBar. (`abbbc90`)
  * Restored circular spinner animations in the workspace overlay. (`0b382d7`)
  * Switched to `v-show` for key UI elements to prevent DOM flicker during state changes. (`98d8237`)

### 🔄 Refactoring

* **Sidebar Footer:** Simplified the footer to an icons-only layout with descriptive hover tooltips. (`83d0800`)

-----

## 🛠️ Internal & Dependency Changes

* **CSS Architecture:** Migration toward CSS variables for layout components (`StatusBar`, `Toast`, `Sidebar`) to support easier theme maintenance.
* **Performance:** Optimization of DOM rendering in `App.vue` to reduce layout shifts.

-----

## ⚠️ Breaking Changes
* **None.** This release is fully backward compatible with `v0.5.7` configurations.

**Full Changelog**: [v0.5.7a22...v0.5.8](https://www.google.com/search?q=https://github.com/your-repo/compare/v0.5.7a22...v0.5.8)