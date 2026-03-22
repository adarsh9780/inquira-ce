Release

### New features

- Added Supabase-based desktop sign-in with browser-managed authentication and session persistence across app restarts.
- Moved agent-generated Python execution onto the workspace kernel so analysis runs in the same runtime as the active workspace.
- Added model refresh and grouped model selection UI so provider models are easier to browse and update.
- Launched the new docs site with branded pages, direct desktop download buttons, and the `docs.inquiraai.com` domain.

### Fixes and improvements

- Made desktop login more reliable by hardening OAuth callback handling, deduplicating startup auth work, and ordering workspace bootstrap correctly after sign-in.
- Improved agent reliability with structured tool execution, short streamed tool explanations, better schema search batching, and safer retry/recursion behavior.
- Fixed several frontend workflow issues, including schema context text being overwritten while typing, manual schema regeneration flow, table/chart delete confirmation UX, and stable external link handling.
- Kept release download links aligned with actual Tauri asset names so docs and download buttons point at the right installers.

### Docs and product polish

- Refreshed auth, privacy, and terms documentation to match current product behavior.
- Updated site branding with the animated Inquira logo and app assets in the browser tab and social preview images.
