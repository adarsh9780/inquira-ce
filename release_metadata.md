Release

## Added
Implemented guest sessions and removed the mandatory login wall for immediate access.
Revamped the documentation site home page and landing pages with a premium Zinc aesthetic and 'Local-First' narrative.
Integrated an offline-first local search engine for the documentation site.
Added a comprehensive Editions overview page and expanded the site footer with legal links.

## Changed
Deferred session verification until the desktop backend startup is ready, making Tauri startup authoritative.
Modernized and pivoted the public roadmap from proxy infrastructure to pure OAuth BYOK, focusing on local-first capabilities.
Removed arbitrary workspace limits and "Free Edition" nomenclature to clarify Community Edition positioning.
Streamlined documentation site navigation by removing redundant pages, consolidating sidebar categories, and promoting downloads.

## Fixed
Resolved uv path resolution issues outside of standard terminal environments during startup.
Fixed guest fallbacks and restored App shell startup build.
Fixed documentation site styling issues including oversized icons, missing imports, form styling, and duplicate formatting.
Restored authentication guards and aligned stale UI assertions in the test suite.