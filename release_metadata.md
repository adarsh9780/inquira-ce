# Release v0.5.7a21

## Added

- Live desktop startup status updates in the app UI by subscribing to native `backend-status` events.
- Regression coverage for startup progress dedupe/layout stability and desktop startup event wiring.

## Changed

- Startup overlays now use a stable two-column layout with a large animated Inquira brand panel and a fixed-height progress panel.
- Desktop runtime state (`.venv`, startup logs, bootstrap markers) now resolves beside the updater-managed `_up_` directory for bundled builds.

## Fixed

- Windows post-startup API `Network error` regressions by unifying runtime config resolution between startup and `get_backend_url`.
- Consistent backend host defaults on Windows (`127.0.0.1`) for backend spawn, health checks, and frontend base URL.
- Duplicate startup progress entries and layout jumpiness when new progress cards are appended.
- Debug Windows build workflow now runs manual-only (no all-branch push trigger) to prevent accidental GitHub Actions minute usage.
